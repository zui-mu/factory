
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
