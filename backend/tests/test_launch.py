import unittest
from unittest.mock import patch

import run


class LaunchTests(unittest.TestCase):
    url = 'http://127.0.0.1:8765'

    def test_launch_waits_for_the_platform_before_opening_unity(self):
        health = {'ok': True, 'name': '质因云联', 'version': '1.5.0', 'webgl_ready': True}
        with patch.object(run, 'server_health', side_effect=[None, health]) as probe, \
             patch.object(run.time, 'sleep'), patch.object(run.webbrowser, 'open', return_value=True) as browser:
            run.open_when_ready(self.url, workshop=True)
        self.assertEqual(probe.call_count, 2)
        browser.assert_called_once_with(self.url + '/?view=unity#workshop')

    def test_unavailable_build_opens_the_existing_workshop_view(self):
        health = {'ok': True, 'name': '质因云联', 'version': '1.5.0', 'webgl_ready': False}
        with patch.object(run.webbrowser, 'open', return_value=True) as browser:
            run.open_client(self.url, workshop=True, health=health)
        browser.assert_called_once_with(self.url + '/#workshop')

    def test_plain_client_keeps_its_original_entry(self):
        with patch.object(run.webbrowser, 'open', return_value=True) as browser:
            run.open_client(self.url, workshop=False, health={'webgl_ready': True})
        browser.assert_called_once_with(self.url)

    def test_readiness_timeout_does_not_open_a_page(self):
        with patch.object(run.time, 'monotonic', side_effect=[0, 0, 9]), \
             patch.object(run.time, 'sleep'), patch.object(run, 'server_health', return_value=None), \
             patch.object(run.webbrowser, 'open') as browser:
            run.open_when_ready(self.url, workshop=True)
        browser.assert_not_called()
