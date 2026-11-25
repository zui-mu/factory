import assert from 'node:assert/strict';
import {test} from 'node:test';

import * as workshop from '../../frontend/workshop-3d.js';

function snapshot() {
  return {
    demo: {
      id: 4, factory_id: 1, device_id: 3, order_id: 64, mode: 'defense', running: 1,
      phase: 'producing', phase_label: '稳定生产', resume_required: false,
      order: {id: 64, factory_id: 1, device_id: 3, code: 'SIM-DEF-01-0004', batch: 'SIM-DEF-01-0004-B01',
        completed: 2, quantity: 120, status: '生产中'},
    },
    device: {id: 3, factory_id: 1, code: 'EQ-03', status: '运行', simulated: true, fresh: true,
      age_seconds: 1.5, freshness_limit: 15, temperature: 71.8, pressure: 5.07, vibration: 0.71},
    readings: [{id: 831, device_id: 3}],
  };
}

test('sends the exact active defense device, order and batch to Unity', () => {
  assert.equal(typeof workshop.projectWorkshopView, 'function');
  const {view, expiresIn} = workshop.projectWorkshopView(snapshot(), 1, 500);
  assert.deepEqual(view, {
    valid: true, runId: 4, deviceId: 3, orderId: 64, deviceCode: 'EQ-03', orderCode: 'SIM-DEF-01-0004',
    batch: 'SIM-DEF-01-0004-B01', completed: 2, quantity: 120, phase: 'producing', running: true,
    temperature: 71.8, pressure: 5.07, vibration: 0.71, status: '运行',
  });
  assert.equal(expiresIn, 13000);
});

test('denies motion when the selected device, run, order or telemetry is unverified', () => {
  for (const change of [
    x => { x.demo.device_id = 99; },
    x => { x.device.code = 'EQ-04'; },
    x => { x.demo.order.id = 63; },
    x => { x.demo.order.device_id = 99; },
    x => { x.demo.order.factory_id = 2; },
    x => { x.demo.order = null; },
    x => { x.demo.order.completed = null; },
    x => { x.readings = []; },
    x => { x.device.fresh = false; },
    x => { x.device.age_seconds = 15; },
    x => { x.device.temperature = null; },
  ]) {
    const input = snapshot();
    change(input);
    assert.deepEqual(workshop.projectWorkshopView(input, 1).view, {valid: false, running: false});
  }
  assert.equal(workshop.projectWorkshopView(snapshot(), 2).view.valid, false);
});

test('keeps the batch visible during thermal interlock without playing the animation', () => {
  let input = snapshot();
  for (const phase of ['fault', 'cooling', 'awaiting_resume', 'warming', 'shortage']) {
    input.demo.phase = phase;
    input.demo.resume_required = true;
    const {view} = workshop.projectWorkshopView(input, 1);
    assert.equal(view.valid, true);
    assert.equal(view.running, false);
    assert.equal(view.phase, phase);
    assert.equal(view.batch, 'SIM-DEF-01-0004-B01');
  }
  input = snapshot();
  input.demo.order.status = '已暂停';
  assert.equal(workshop.projectWorkshopView(input, 1).view.running, false);
});

test('offers only phase-appropriate controls to authorized roles', () => {
  const input = snapshot();
  const controls = () => workshop.workshopControls(input, workshop.projectWorkshopView(input, 1).view, 'engineer');
  assert.deepEqual(controls(), {prepare: false, fault: true, recover: false, resume: false, stop: true});
  input.demo.phase = 'awaiting_resume';
  assert.deepEqual(controls(), {prepare: false, fault: false, recover: false, resume: true, stop: true});
  input.demo.device_id = 6;
  assert.deepEqual(controls(), {prepare: false, fault: false, recover: false, resume: false, stop: true});
  assert.deepEqual(workshop.workshopControls(input, {valid: true}, 'operator'),
    {prepare: false, fault: false, recover: false, resume: false, stop: false});
});
