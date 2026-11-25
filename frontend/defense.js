
import {esc, fmt} from './ui.js';

function measured(value, unit) {
  return value == null ? '—' : fmt(value) + ' ' + unit;
}

function dateTime(value) {
  if (!value) return '—';
  return '<time datetime="' + esc(value) + '">' + esc(String(value).replace('T', ' ')) + '</time>';
}

function facts(entries) {
  return '<dl class="defense-facts">' + entries.map(([label, content]) =>
    '<div><dt>' + label + '</dt><dd>' + content + '</dd></div>'
  ).join('') + '</dl>';
}

const warehouseStages = {
  ready: '待模拟缺料',
  shortage: '缺料停产',
  refilled: '已补料，等待报工',
  resumed: '已恢复生产',
};

export function renderWarehouseSummary(warehouse) {
  const {stage, material_name: name, unit, location, line_location: lineLocation, line_quantity: line, available_quantity: available} = warehouse;
  return '<p class="warehouse-state" data-stage="' + esc(stage) + '">' + esc(name) + ' · ' + esc(warehouseStages[stage] || '—') + '</p>' +
    '<dl class="warehouse-balances"><div><dt>' + esc(lineLocation) + '</dt><dd>' + measured(line, esc(unit)) + '</dd></div>' +
    '<div><dt>' + esc(location) + '</dt><dd>' + measured(available, esc(unit)) + '</dd></div></dl>';
}

function warehouseRecord(warehouse) {
  const {stage, location, available_quantity: available, line_location: lineLocation, line_quantity: line,
    transfers = [], hold, recovery} = warehouse;
  const unit = esc(warehouse.unit);
  const balances = [
    ['补料进度', esc(warehouseStages[stage] || '—')],
    [esc(location), measured(available, unit)],
    [esc(lineLocation), measured(line, unit)],
    ['补料后累计报工', stage === 'refilled' || stage === 'resumed' ? measured(recovery?.output_count, '件') : '—'],
  ];
  return '<section class="defense-warehouse"><h3>库位补料</h3>' + facts(balances) +
    (hold ? '<p>缺料期间报工 ' + measured(hold.output_count, '件') + ' · 耗料 ' + measured(hold.consumed_quantity, unit) + '</p>' : '') +
    (transfers.length ? '<ol>' + transfers.map(move =>
      '<li><div><strong>' + (move.kind === 'return' ? '退回库位' : '库位补料') + '</strong> · ' +
      esc(move.from_location) + ' → ' + esc(move.to_location) + '</div><span>' + measured(move.quantity, unit) + '</span>' +
      '<span>出库 #' + esc(move.out_move_id) + ' · 入库 #' + esc(move.in_move_id) + '</span><span>批次 ' + esc(move.batch) + '</span>' +
      dateTime(move.at) + '</li>'
    ).join('') + '</ol>' : '') +
    (recovery?.first_report_id ? '<p>首条报工 #' + esc(recovery.first_report_id) + ' · ' + dateTime(recovery.first_report_at) + '</p>' : '') +
    '</section>';
}

function qualityResults(records, resumed) {
  if (!resumed) return '<p>待确认复产后采集。</p>';
  if (!records.length) return '<p>暂无复产后批次抽检记录。</p>';
  return '<ul class="defense-quality-list">' + records.map(record =>
    '<li><span>批次 <strong>' + esc(record.batch) + '</strong> · 质检 #' + esc(record.id) + '</span>' +
    '<span>抽检 <strong>' + measured(record.sample_size, '件') + '</strong> · 不合格 <strong>' +
    measured(record.defects, '件') + '</strong></span>' + dateTime(record.created_at) + '</li>'
  ).join('') + '</ul>';
}

function interlockRecord(interlock, unit) {
  const {fault_at: faultAt, resume_at: resumeAt, anomaly, task, inspection, shutdown, restart} = interlock;
  const status = {passed: '通过', failed: '未通过', pending: '待点检'}[inspection?.status] || '待点检';
  const inspectionText = task?.id ? '工单 #' + esc(task.id) + ' · ' + esc(task.status || '待处理') : '待派单';
  const details = [
    ['故障触发', dateTime(faultAt)],
    ['复产确认', resumeAt ? dateTime(resumeAt) : '待确认复产'],
    ['停产前累计报工', measured(shutdown?.completed_before, '件')],
    [resumeAt ? '复产确认时累计报工' : '停产期间累计报工', measured(shutdown?.completed_after, '件')],
    ['停产段报工 / 耗料', measured(shutdown?.output_count, '件') + ' / ' + measured(shutdown?.consumed_quantity, unit)],
    ['复产后报工 / 耗料', resumeAt ? measured(restart?.output_count, '件') + ' / ' + measured(restart?.consumed_quantity, unit) : '待复产'],
    ['处置人员', esc(task?.assignee_name || '待派单')],
  ];
  return '<article class="defense-interlock">' +
    '<div class="defense-interlock-head"><h3>' + esc(anomaly?.title || '温控故障') + '</h3>' +
    (anomaly?.id ? '<button type="button" class="btn small" data-action="open-analysis" data-id="' + esc(anomaly.id) + '">查看异常 #' + esc(anomaly.id) + '</button>' : '') +
    '</div>' + facts(details) +
    '<div class="defense-review"><section><h4>设备点检</h4>' +
    '<p><strong>' + status + '</strong> · ' + inspectionText + '</p>' +
    (inspection?.reviewed_at ? '<p>' + esc(inspection.reviewer || '—') + ' · ' + dateTime(inspection.reviewed_at) + '</p>' : '') +
    (inspection?.note ? '<p class="defense-note">' + esc(inspection.note) + '</p>' : '') +
    '</section><section><h4>复产后批次抽检</h4>' +
    qualityResults(restart?.quality_records || [], Boolean(resumeAt)) + '</section></div></article>';
}

export function renderDefenseRecord(record) {
  const {device, order, material, staffing, source, interlocks = [], warehouse, events = []} = record;
  const identifiers = [
    ['模拟设备', esc(device?.code || '—') + (device?.name ? ' · ' + esc(device.name) : '')],
    ['生产工单', esc(order?.code || '—')],
    ['当前批次', esc(order?.batch || '—')],
    ['原料', esc(material?.name || '—')],
  ];
  if (staffing?.operator_name) {
    identifiers.push(['演示班表', esc(staffing.operator_name) + ' · ' + dateTime(staffing.start_at) + ' 至 ' + dateTime(staffing.end_at)]);
  }
  return '<p class="defense-context">' + esc(source || '本机模拟数据') +
    (record.run_id ? ' · 演示 #' + esc(record.run_id) : '') + '</p>' + facts(identifiers) +
    (interlocks.length ? interlocks.map(fault => interlockRecord(fault, esc(material?.unit || ''))).join('') :
      '<p class="defense-empty">当前演示暂无温控故障记录。</p>') +
    (warehouse ? warehouseRecord(warehouse) : '') +
    (events.length ? '<section class="defense-event-log"><h3>演示与处置时间线</h3><ol>' + events.map(event =>
      '<li>' + dateTime(event.at) + '<strong>' + esc(event.label) + '</strong><span>' + esc(event.actor || '—') + '</span></li>'
    ).join('') + '</ol></section>' : '');
}
