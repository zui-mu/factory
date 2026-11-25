
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {test} from 'node:test';

const component = await import('../../frontend/defense.js').catch(error => {
  if (error.code === 'ERR_MODULE_NOT_FOUND') return {};
  throw error;
});

test('public pages present the competition project title', async () => {
  const entry = await readFile(new URL('../../frontend/index.html', import.meta.url), 'utf8');
  assert.match(entry, /<title>全景可视化数字工厂<\/title>/);
  for (const name of ['app.js', 'pages.js', 'controlroom.js']) {
    const page = await readFile(new URL('../../frontend/' + name, import.meta.url), 'utf8');
    assert.doesNotMatch(page, /质因云联|ZHIYIN YUNLIAN/);
  }
});

test('displays linked simulation identifiers, interlock evidence and separate review and quality records', () => {
  assert.equal(typeof component.renderDefenseRecord, 'function', 'render the defense record');
  const result = component.renderDefenseRecord({
    run_id: 18,
    source: '答辩模拟',
    device: {id: 3, code: 'EQ-03', name: '成型单元'},
    order: {id: 42, code: 'SIM-01-0042', batch: 'SIM-01-0042-B01'},
    material: {id: 7, name: '演示 PA66 原料', unit: 'kg'},
    interlocks: [{
      fault_at: '2026-11-25T10:11:12',
      resume_at: '2026-11-25T10:12:13',
      anomaly: {id: 72, title: '温控故障'},
      task: {id: 21, assignee_name: '<script>作业员</script>', status: '已关闭'},
      shutdown: {completed_before: 4, completed_after: 4, output_count: 0, consumed_quantity: 0},
      restart: {
        output_count: 10, consumed_quantity: 1.2,
        quality_records: [{id: 88, batch: 'SIM-01-0042-B01', sample_size: 10, defects: 1, created_at: '2026-11-25T10:13:41'}]
      },
      inspection: {status: 'passed', reviewer: '质量工程师', reviewed_at: '2026-11-25T10:13:40', note: '温控回路检查完成'}
    }],
    events: [{id: 34, at: '2026-11-25T10:12:13', label: '确认复产', actor: '管理员'}]
  });
  assert.match(result, /EQ-03/);
  assert.match(result, /SIM-01-0042-B01/);
  assert.match(result, /10:11:12/);
  assert.match(result, /10:12:13/);
  assert.match(result, /4 件[\s\S]*4 件/);
  assert.match(result, /0 kg/);
  assert.match(result, /&lt;script&gt;作业员&lt;\/script&gt;/);
  assert.doesNotMatch(result, /<script>/);
  assert.match(result, /设备点检[\s\S]*通过[\s\S]*温控回路检查完成/);
  assert.match(result, /复产后批次抽检[\s\S]*10 件[\s\S]*1 件/);
});

test('keeps not yet collected evidence distinct from a recorded zero', () => {
  assert.equal(typeof component.renderDefenseRecord, 'function', 'render the defense record');
  const result = component.renderDefenseRecord({
    device: {code: 'EQ-03'}, order: {code: 'SIM-01-0042'}, material: {unit: 'kg'},
    interlocks: [{fault_at: '2026-11-25T10:11:12', shutdown: null, restart: {output_count: 0, consumed_quantity: 0}, inspection: {status: 'pending'}}],
    events: []
  });
  assert.match(result, /待点检/);
  assert.match(result, /待确认复产/);
  assert.doesNotMatch(result, /0 件|0 kg/);
});

test('shows paired warehouse movements and the same batch production report', () => {
  const result = component.renderDefenseRecord({
    order: {batch: 'SIM-01-0042-B01'},
    warehouse: {
      stage: 'resumed', location: '模拟库位 A-01', line_location: '演示线料仓',
      material_name: '演示 PA66 原料', unit: 'kg', available_quantity: 5.32, line_quantity: 0.56,
      transfers: [
        {kind: 'return', quantity: 5.92, batch: 'SIM-01-0042-B01', from_location: '演示线料仓',
          to_location: '模拟库位 A-01', out_move_id: 40, in_move_id: 41, at: '2026-11-25T10:11:12'},
        {kind: 'replenish', quantity: 0.6, batch: 'SIM-01-0042-B01', from_location: '模拟库位 A-01',
          to_location: '演示线料仓', out_move_id: 42, in_move_id: 43, at: '2026-11-25T10:12:13'},
      ],
      hold: {report_count: 0, output_count: 0, consumed_quantity: 0, completed_before: 2, completed_after: 2},
      recovery: {report_count: 1, output_count: 1, first_report_id: 81, first_report_at: '2026-11-25T10:13:41'},
    },
  });
  assert.match(result, /库位补料[\s\S]*5\.32 kg[\s\S]*0\.56 kg/);
  assert.match(result, /缺料期间报工 0 件 · 耗料 0 kg/);
  assert.match(result, /演示线料仓 → 模拟库位 A-01[\s\S]*5\.92 kg[\s\S]*出库 #40 · 入库 #41/);
  assert.match(result, /模拟库位 A-01 → 演示线料仓[\s\S]*0\.6 kg[\s\S]*出库 #42 · 入库 #43/);
  assert.match(result, /SIM-01-0042-B01[\s\S]*首条报工 #81[\s\S]*10:13:41/);
});

test('shows real zero inventory and waits for evidence after a refill', () => {
  const warehouse = {
    stage: 'shortage', location: '模拟库位 A-01', line_location: '演示线料仓',
    material_name: '演示 PA66 原料', unit: 'kg', line_quantity: 0, available_quantity: 5.92,
    recovery: {output_count: 0},
  };
  const summary = component.renderWarehouseSummary(warehouse);
  assert.match(summary, /缺料停产[\s\S]*演示线料仓[\s\S]*0 kg/);
  assert.doesNotMatch(component.renderDefenseRecord({warehouse}), /补料后累计报工<\/dt><dd>0 件/);
  const result = component.renderDefenseRecord({warehouse: {...warehouse, stage: 'refilled', line_quantity: 0.6}});
  assert.match(result, /已补料，等待报工/);
  assert.match(result, /补料后累计报工<\/dt><dd>0 件/);
  assert.doesNotMatch(result, /首条报工 #|已恢复生产/);
});
