# -*- coding: utf-8 -*-
"""Process invariants exercised with an injected clock, without touching user data."""
import unittest
from datetime import datetime,timedelta
from backend.db import SCHEMA,one,rows,connect
from mysql_support import TestDatabases
from backend.live import control,advance,describe,annotate,PROFILES
from backend.telemetry import device_freshness
from backend.api import ApiError

class LiveLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mysql=TestDatabases()
        cls.addClassCleanup(cls.mysql.close)
        with connect(config=cls.mysql.config) as c:c.executescript(SCHEMA)

    def setUp(self):
        self.c=connect(config=self.mysql.config);self.c.begin_write()
        for f in (1,2,3):self.c.execute('INSERT INTO factories VALUES(?,?,?)',(f,'测试工厂'+str(f),'匿名园区'))
        self.c.execute("INSERT INTO users(id,username,password,name,role,factory_id) VALUES(1,'tester','test-placeholder','测试员','admin',1)")
        self.user={'id':1,'username':'tester','factory_id':1};self.clock=datetime.now().replace(microsecond=0)
        self.run=control(self.c,self.user,1,'start',self.clock)
    def tearDown(self):self.c.close()
    def record(self):return one(self.c,'SELECT * FROM demo_runs WHERE id=?',(self.run['id'],))
    def state(self):return describe(self.record())
    def tick(self,n=1,seconds=3):
        for _ in range(n):
            self.clock+=timedelta(seconds=seconds);advance(self.c,self.record(),self.clock)
    def until(self,check,limit=450):
        for _ in range(limit):
            if check():return
            self.tick()
        self.fail('Process did not reach expected condition: '+str(self.state()))
    def action(self,name):return control(self.c,self.user,self.run['factory_id'],name,self.clock)
    def order(self):return one(self.c,'SELECT * FROM orders WHERE id=?',(self.run['order_id'],))
    def device(self):return one(self.c,'SELECT * FROM devices WHERE id=?',(self.run['device_id'],))
    def stock(self):return one(self.c,'SELECT * FROM materials WHERE id=?',(self.run['material_id'],))['stock']
    def total(self,table,column):return self.c.execute('SELECT coalesce(sum('+column+'),0) FROM '+table).fetchone()[0]
    def test_warmup_consumption_and_sampling(self):
        self.tick(2);self.assertEqual(self.order()['completed'],0);self.assertEqual(self.state()['phase'],'warming')
        self.until(lambda:self.order()['completed']>=23)
        done=self.order()['completed'];self.assertEqual(self.total('production_reports','quantity'),done)
        self.assertAlmostEqual(self.stock(),6-done*.04);self.assertAlmostEqual(self.total('stock_moves','quantity'),done*.04)
        self.assertEqual(self.total('quality','sample_size')+self.state()['pending_samples'],done)
        for q in rows(self.c,'SELECT * FROM quality'):
            self.assertLessEqual(q['defects'],q['sample_size']);self.assertTrue(annotate(self.c,'quality',[q])[0]['simulated'])
        self.action('stop');self.assertEqual(self.total('quality','sample_size'),done)
    def test_fault_gradual_cooling_requires_human_resume(self):
        self.until(lambda:self.order()['completed']>=3);qty=self.order()['completed'];stock=self.stock();temp=self.device()['temperature']
        self.action('fault');self.tick();self.assertLess(abs(self.device()['temperature']-temp),2.4)
        self.tick(12);self.assertGreater(self.device()['temperature'],90)
        self.assertEqual(self.order()['completed'],qty);self.assertEqual(self.stock(),stock)
        self.action('fault');self.assertEqual(len(rows(self.c,'SELECT * FROM anomalies WHERE order_id IS NULL')),1)
        self.action('recover')
        with self.assertRaises(ApiError):self.action('resume')
        self.tick();self.assertGreater(self.device()['temperature'],90)
        self.until(lambda:self.state()['phase']=='awaiting_resume');self.tick(8)
        self.assertEqual(self.order()['completed'],qty);self.assertEqual(self.stock(),stock)
        self.action('resume');self.until(lambda:self.order()['completed']>qty)
        self.assertEqual(one(self.c,'SELECT * FROM anomalies WHERE order_id IS NULL')['status'],'待分析')
    def test_stop_start_keeps_fault_latch(self):
        self.action('fault');self.tick(10);self.action('stop');self.action('start')
        self.assertTrue(self.state()['resume_required']);self.until(lambda:self.state()['phase']=='awaiting_resume')
        self.tick(20);self.assertEqual(self.order()['completed'],0)
    def test_short_stop_and_changeover_batches(self):
        self.until(lambda:self.order()['completed']>=4);qty=self.order()['completed']
        self.action('short-stop');self.tick(3);self.assertEqual(self.order()['completed'],qty)
        self.until(lambda:self.state()['phase']=='producing');self.action('changeover');self.tick(6)
        self.assertEqual(self.order()['completed'],qty);self.until(lambda:self.state()['batch']==2)
        self.assertEqual(self.total('quality','sample_size'),qty);self.assertEqual(self.state()['batch_samples'],0)
        self.assertIsNone(self.state()['batch_rate']);self.assertTrue(self.order()['batch'].endswith('B02'))
        self.until(lambda:self.order()['completed']>=qty+10)
        batches={q['batch'] for q in rows(self.c,'SELECT * FROM quality')};self.assertEqual(len(batches),2)
    def test_pause_and_shortage_do_not_consume(self):
        self.c.execute("UPDATE orders SET status='已暂停'");self.tick(10)
        self.assertEqual(self.order()['completed'],0);self.assertEqual(self.stock(),6)
        self.c.execute("UPDATE orders SET status='生产中'");self.c.execute('UPDATE materials SET stock=.01');self.tick(10)
        self.assertEqual(self.state()['phase'],'shortage');self.assertEqual(self.stock(),.01)
        self.c.execute('UPDATE materials SET stock=.04');self.until(lambda:self.order()['completed']==1);self.tick(10)
        self.assertEqual(self.order()['completed'],1);self.assertEqual(self.stock(),0)
    def test_no_overproduction_and_separate_new_order(self):
        self.c.execute('UPDATE orders SET quantity=1');self.until(lambda:not self.state()['running']);self.tick(10)
        self.assertEqual(self.order()['completed'],1);self.assertEqual(self.total('quality','sample_size'),1)
        another=self.action('start');self.assertNotEqual(another['order_id'],self.run['order_id'])
    def test_delayed_sampling_does_not_invent_output(self):
        self.until(lambda:self.order()['completed']>=2);qty=self.order()['completed']
        self.tick(seconds=90);self.assertEqual(self.order()['completed'],qty)
        self.assertEqual(self.state()['phase'],'warming');self.tick();self.assertEqual(self.order()['completed'],qty)
    def test_run_limit_flushes_actual_pending_samples(self):
        self.until(lambda:self.order()['completed']>=3);qty=self.order()['completed']
        self.tick(seconds=1200);self.assertFalse(self.state()['running']);self.assertEqual(self.order()['completed'],qty)
        self.assertEqual(self.total('quality','sample_size'),qty)
    def test_factory_profiles_and_bounded_sensor_variation(self):
        observed=[]
        for f in (1,2,3):
            self.run=control(self.c,self.user,f,'start',self.clock);self.until(lambda:self.order()['completed']>=10)
            rs=rows(self.c,'SELECT * FROM readings WHERE device_id=? ORDER BY id',(self.run['device_id'],))
            self.assertTrue(all(abs(a['temperature']-b['temperature'])<2.45 for a,b in zip(rs,rs[1:])))
            self.assertGreater(len({r['pressure'] for r in rs}),5)
            self.assertAlmostEqual(self.stock(),PROFILES[f]['usage']*(150-self.order()['completed']))
            observed.append(self.device()['temperature']);self.action('stop')
        self.assertGreater(observed[1],observed[0]);self.assertLess(observed[2],observed[0])
    def test_freshness_is_independent_of_last_reported_state(self):
        d=dict(self.device(),status='运行',simulated=True)
        self.assertTrue(device_freshness([dict(d)],self.clock)[0]['fresh'])
        stale=device_freshness([dict(d)],self.clock+timedelta(seconds=16))[0]
        self.assertFalse(stale['fresh']);self.assertEqual(stale['display_status'],'通信未知')
        self.assertFalse(device_freshness([dict(d)],self.clock-timedelta(seconds=1))[0]['fresh'])
        self.assertEqual(device_freshness([dict(d,temperature=None)],self.clock)[0]['display_status'],'未采集')
        self.assertEqual(device_freshness([dict(d,archived=True)],self.clock)[0]['display_status'],'历史档案')

if __name__=='__main__':unittest.main()
