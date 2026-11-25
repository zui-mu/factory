"""Freshness is independent of the last reported machine state."""
from datetime import datetime

def device_freshness(records,current=None):
    current=current or datetime.now()
    for d in records:
        limit=15 if d.get('simulated') else 120
        try:age=(current-datetime.fromisoformat(d.get('updated_at') or '')).total_seconds()
        except (ValueError,TypeError):age=None
        collected=all(d.get(k) is not None for k in ('temperature','pressure','vibration'))
        valid=collected and age is not None and 0<=age<=limit and not d.get('archived')
        d.update(fresh=valid,age_seconds=round(age,1) if age is not None else None,freshness_limit=limit,
            display_status='历史档案' if d.get('archived') else d['status'] if valid else '通信未知' if collected else '未采集')
    return records
