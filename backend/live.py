# -*- coding: utf-8 -*-
"""Persisted, opt-in process demonstration. Not a calibrated physical model."""
import json,random,threading,traceback
from datetime import datetime,timedelta
from .db import connect,one,rows,now,audit
from .telemetry import device_freshness

LABEL='动态演示产线（模拟）'
INTERVAL=3
PROFILES={
 1:dict(name='精密外壳成型',temperature=72.,pressure=5.2,vibration=.72,cycle=6.8,usage=.04,risk=.018),
 2:dict(name='厚壁壳体成型',temperature=76.,pressure=5.8,vibration=.90,cycle=9.2,usage=.055,risk=.028),
 3:dict(name='轻量支架成型',temperature=69.,pressure=4.8,vibration=.62,cycle=8.1,usage=.03,risk=.022),
}
PHASES={'warming':'预热稳态','producing':'稳定生产','short_stop':'短暂停机','changeover':'换料确认',
 'fault':'温控故障','cooling':'降温观察','awaiting_resume':'等待复产确认','paused':'工单暂停','shortage':'缺料等待','stopped':'演示已停止'}

def initial_state(run,stamp):
    return dict(phase='warming',phase_elapsed=0.,cycle_elapsed=0.,cycle_target=PROFILES[run['factory_id']]['cycle'],
      stable=0.,resume_required=False,last_step=stamp,batch=1,batch_shift=0.,batch_n=0,batch_bad=0,
      pending_n=0,pending_bad=0,produced=0,next_stop=14+run['factory_id']*2,stops=0,settling=0,load=0.,temperature_drift=0.)

def state_of(run):
    s=initial_state(run,run['updated_at']);s.update(json.loads(run.get('state') or '{}'));return s

def describe(record):
    if not record:return None
    result={k:v for k,v in record.items() if k not in ('user_id','state')};s=state_of(record)
    result.update(phase=s['phase'],phase_label=PHASES[s['phase']],profile=PROFILES[record['factory_id']],
       phase_seconds=round(s['phase_elapsed']),cycle_seconds=round(s['cycle_target'],1),
       batch=s['batch'],pending_samples=s['pending_n'],resume_required=s['resume_required'],
       batch_samples=s['batch_n'],batch_defects=s['batch_bad'],
       batch_rate=1-s['batch_bad']/s['batch_n'] if s['batch_n'] else None)
    return result

def annotate(c,entity,records):
    if entity in ('devices','orders','materials','quality'):
        sources={r['record_id']:r for r in rows(c,'SELECT record_id,label FROM source_records WHERE entity=?',(entity,))}
        for record in records:
            src=sources.get(record['id'])
            record['archived']=bool(src);record['source']=src['label'] if src else '平台业务数据'
    column={'devices':'device_id','orders':'order_id','materials':'material_id'}.get(entity)
    demo={r[column] for r in rows(c,'SELECT '+column+' FROM demo_runs')} if column else set()
    demo_orders={r['order_id'] for r in rows(c,'SELECT order_id FROM demo_runs')} if entity=='quality' else set()
    for r in records:
        if r['id'] in demo or (entity=='quality' and r['order_id'] in demo_orders):r['source']=LABEL;r['simulated']=True
    return device_freshness(records) if entity=='devices' else records

def snapshot(c,f,device_id=None):
    run=one(c,'SELECT * FROM demo_runs WHERE factory_id=? ORDER BY id DESC LIMIT 1',(f,))
    device=one(c,'SELECT * FROM devices WHERE factory_id=? AND id=?',(f,device_id or (run or {}).get('device_id',0)))
    if not device:device=one(c,"SELECT * FROM devices WHERE factory_id=? AND temperature IS NOT NULL ORDER BY id LIMIT 1",(f,))
    current=datetime.now();start=(current-timedelta(minutes=15)).isoformat(timespec='seconds')
    recent=rows(c,'SELECT * FROM readings WHERE device_id=? AND created_at>=? ORDER BY id DESC LIMIT 320',(device['id'],start))[::-1] if device else []
    history=rows(c,'SELECT * FROM readings WHERE device_id=? ORDER BY id DESC LIMIT 40',(device['id'],))[::-1] if device else []
    if device:annotate(c,'devices',[device])
    hours=[(current.replace(minute=0,second=0,microsecond=0)-timedelta(hours=i)).isoformat(timespec='hours') for i in range(7,-1,-1)]
    reports=rows(c,"SELECT substr(p.created_at,1,13) `hour`,sum(p.quantity) quantity FROM production_reports p JOIN orders o ON o.id=p.order_id WHERE o.factory_id=? AND p.created_at>=? GROUP BY `hour`",(f,hours[0]))
    lookup={r['hour']:r['quantity'] for r in reports}
    minutes=[(current.replace(second=0,microsecond=0)-timedelta(minutes=i)).isoformat(timespec='minutes') for i in range(14,-1,-1)]
    production=rows(c,"SELECT substr(p.created_at,1,16) `minute`,sum(p.quantity) quantity FROM production_reports p JOIN orders o ON o.id=p.order_id WHERE o.factory_id=? AND p.created_at>=? GROUP BY `minute`",(f,minutes[0]))
    minute_lookup={r['minute']:r['quantity'] for r in production}
    inspection=rows(c,'SELECT batch,sample_size,defects,created_at FROM quality WHERE order_id=? AND inspector=? ORDER BY id DESC LIMIT 8',(run['order_id'],'演示在线检测'))[::-1] if run else []
    return {'server_time':current.isoformat(timespec='seconds'),'demo':describe(run),'device':device,'readings':history,'recent_readings':recent,
      'window_start':start,'minute_output':[{'time':m,'quantity':minute_lookup.get(m,0),'partial':i==14} for i,m in enumerate(minutes)],
      'inspections':inspection,'hourly':[{'hour':h[11:]+':00','quantity':lookup.get(h,0)} for h in hours],
      'events':rows(c,"SELECT id,action,entity,user_name,created_at FROM audit WHERE factory_id=? AND action NOT IN ('登录','退出登录','修改密码') ORDER BY id DESC LIMIT 12",(f,)),
      'source':LABEL if device and device.get('simulated') else '最近采集记录',
      'stale_after_seconds':device['freshness_limit'] if device else 120}

def actor(run):return {'username':'演示采集器','factory_id':run['factory_id']}

def transition(c,run,s,phase):
    if s['phase']!=phase:
        audit(c,actor(run),'演示工况 · '+PHASES[phase],str(run['id']),PHASES[s['phase']]+' → '+PHASES[phase])
        s['phase']=phase;s['phase_elapsed']=0.;s['cycle_elapsed']=0.;s['stable']=0.

def save(c,run,s,stamp,**values):
    values.update(state=json.dumps(s,ensure_ascii=False),updated_at=stamp)
    c.execute('UPDATE demo_runs SET '+','.join(k+'=?' for k in values)+' WHERE id=?',tuple(values.values())+(run['id'],))

def flush_quality(c,run,s,o,stamp):
    n=s['pending_n'];bad=s['pending_bad']
    if not n:return
    batch=o['code']+'-B%02d'%s['batch']
    c.execute('INSERT INTO quality(factory_id,order_id,batch,sample_size,defects,defect_type,inspector,created_at) VALUES(?,?,?,?,?,?,?,?)',
      (run['factory_id'],o['id'],batch,n,bad,'模拟外观检测','演示在线检测',stamp))
    s['batch_n']+=n;s['batch_bad']+=bad;s['pending_n']=s['pending_bad']=0
    audit(c,actor(run),'演示检测完成',batch,'%s 件中 %s 件不合格'%(n,bad))
    if bad/n>.05 and not one(c,"SELECT id FROM anomalies WHERE order_id=? AND status!='已关闭'",(o['id'],)):
        c.execute('INSERT INTO anomalies(factory_id,device_id,order_id,title,severity,description,source,created_at) VALUES(?,?,?,?,?,?,?,?)',
          (run['factory_id'],run['device_id'],o['id'],'演示批次外观缺陷率超限','高','%s：检测 %s 件，%s 件不合格；模拟结果需人工处置。'%(batch,n,bad),LABEL,stamp))

def fault_alarm(c,run,stamp):
    if not one(c,"SELECT id FROM anomalies WHERE device_id=? AND order_id IS NULL AND source=? AND status!='已关闭'",(run['device_id'],LABEL)):
        c.execute('INSERT INTO anomalies(factory_id,device_id,title,severity,description,source,created_at) VALUES(?,?,?,?,?,?,?)',
          (run['factory_id'],run['device_id'],'演示线温控故障 · 已阻断自动报工','高','模拟温控故障已联锁停产。观察模具温控回路逐渐升温；恢复后须降温稳定并人工确认复产，异常另行点检闭环。',LABEL,stamp))

def control(c,user,f,action,moment=None):
    from .api import ApiError
    stamp=(moment or datetime.now()).isoformat(timespec='seconds')
    run=one(c,'SELECT * FROM demo_runs WHERE factory_id=? ORDER BY id DESC LIMIT 1',(f,))
    if action=='start':
        order=one(c,'SELECT * FROM orders WHERE id=?',(run['order_id'],)) if run else None
        if not run or order['status'] in ('已完成','已取消'):
            seq=c.execute('SELECT coalesce(max(id),0)+1 FROM demo_runs').fetchone()[0];code='SIM-%02d-%04d'%(f,seq);p=PROFILES[f]
            did=c.execute('INSERT INTO devices(factory_id,code,name,line,status,temperature,pressure,vibration,runtime,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
              (f,code,'演示成型单元','模具温控回路 · '+p['name'],'待机',p['temperature']-8,.4,.18,0,stamp)).lastrowid
            oid=c.execute('INSERT INTO orders(factory_id,code,product,batch,quantity,status,priority,due_date,device_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
              (f,code,'演示连接器外壳',code+'-B01',120,'生产中','普通',stamp[:10],did,stamp)).lastrowid
            mid=c.execute('INSERT INTO materials(factory_id,code,name,spec,unit,stock,min_stock,location) VALUES(?,?,?,?,?,?,?,?)',
              (f,code,'演示 PA66 原料','%.3f kg / 件'%p['usage'],'kg',round(p['usage']*150,3),round(p['usage']*50,3),'演示线料仓')).lastrowid
            rid=c.execute('INSERT INTO demo_runs(factory_id,device_id,order_id,material_id,user_id,running,started_at,updated_at) VALUES(?,?,?,?,?,1,?,?)',(f,did,oid,mid,user['id'],stamp,stamp)).lastrowid
            run=one(c,'SELECT * FROM demo_runs WHERE id=?',(rid,));s=initial_state(run,stamp);save(c,run,s,stamp,reason='预热至稳定窗口后开始生产')
        elif not run['running']:
            s=state_of(run);transition(c,run,s,'cooling' if s['resume_required'] else 'warming');s['last_step']=stamp
            save(c,run,s,stamp,running=1,started_at=stamp,user_id=user['id'],reason='恢复采集，检查工况后继续')
    elif run and action=='stop':
        s=state_of(run);o=one(c,'SELECT * FROM orders WHERE id=?',(run['order_id'],));flush_quality(c,run,s,o,stamp)
        transition(c,run,s,'stopped');save(c,run,s,stamp,running=0,reason='人工停止演示')
        c.execute("UPDATE devices SET status='待机' WHERE id=?",(run['device_id'],))
    elif run and run['running']:
        s=state_of(run);phase=s['phase']
        if action=='fault':
            transition(c,run,s,'fault');s['resume_required']=True;fault_alarm(c,run,stamp)
        elif action=='recover' and phase=='fault':transition(c,run,s,'cooling')
        elif action=='resume' and phase=='awaiting_resume':
            d=one(c,'SELECT * FROM devices WHERE id=?',(run['device_id'],));p=PROFILES[f]
            if not device_freshness([dict(d,simulated=True)],moment)[0]['fresh'] or abs(d['temperature']-p['temperature'])>1.5:
                raise ApiError('采集已过期或温度不在稳定窗口，请继续观察',409)
            s['resume_required']=False;s['settling']=5;transition(c,run,s,'warming')
        elif action in ('short-stop','changeover') and phase=='producing':
            transition(c,run,s,'short_stop' if action=='short-stop' else 'changeover');s['hold_seconds']=12 if action=='short-stop' else 21
        else:raise ApiError('当前工况不允许此操作；降温稳定后才能确认复产',409)
        s['last_step']=stamp
        save(c,run,s,stamp,scenario='overheat' if s['phase']=='fault' else 'normal',reason=PHASES[s['phase']])
        if s['phase']!='producing':c.execute('UPDATE devices SET status=? WHERE id=?',('预警' if s['resume_required'] else '待机',run['device_id']))
    else:raise ApiError('请先启动演示产线')
    titles={'start':'启动动态演示','stop':'停止动态演示','fault':'模拟温控故障','recover':'开始降温观察','resume':'确认演示复产','short-stop':'模拟短暂停机','changeover':'模拟换料'}
    audit(c,user,titles[action],str(run['id']),LABEL,f)
    return describe(one(c,'SELECT * FROM demo_runs WHERE id=?',(run['id'],)))

def approach(previous,target,speed,dt):return previous+max(-speed*dt,min(speed*dt,target-previous))

def advance(c,run,moment=None):
    if not run['running']:return
    current=moment or datetime.now();stamp=current.isoformat(timespec='seconds');s=state_of(run);p=PROFILES[run['factory_id']]
    elapsed=(current-datetime.fromisoformat(s['last_step'])).total_seconds()
    if elapsed<=0:return
    dt=min(elapsed,INTERVAL*2);s['last_step']=stamp;tick=run['tick']+1
    r=random.Random(run['id']*1000003+run['factory_id']*10007+tick*97)
    o=one(c,'SELECT * FROM orders WHERE id=?',(run['order_id'],));m=one(c,'SELECT * FROM materials WHERE id=?',(run['material_id'],));d=one(c,'SELECT * FROM devices WHERE id=?',(run['device_id'],))
    if (current-datetime.fromisoformat(run['started_at'])).total_seconds()>=1200 or o['status'] in ('已完成','已取消'):
        flush_quality(c,run,s,o,stamp);transition(c,run,s,'stopped');save(c,run,s,stamp,running=0,reason='工单结束或演示达到20分钟上限')
        c.execute("UPDATE devices SET status='待机' WHERE id=?",(run['device_id'],));return
    if elapsed>INTERVAL*3:
        s['cycle_elapsed']=0;s['stable']=0;dt=INTERVAL
        if s['phase']=='producing':transition(c,run,s,'warming')
        audit(c,actor(run),'采集间隔中断',str(run['id']),'不补算失联期间产量；重新检查稳定状态')
    if s['phase'] not in ('fault','cooling','awaiting_resume'):
        if o['status']!='生产中':transition(c,run,s,'paused')
        elif m['stock']+1e-8<p['usage']:transition(c,run,s,'shortage')
        elif s['phase'] in ('paused','shortage','stopped'):transition(c,run,s,'cooling' if s['resume_required'] else 'warming')
    phase=s['phase'];s['phase_elapsed']+=dt
    s['load']=max(-.16,min(.16,.72*s['load']+r.uniform(-.065,.065)))
    s['temperature_drift']=max(-.5,min(.5,.96*s['temperature_drift']+r.uniform(-.08,.08)))
    target=p['temperature']+s['temperature_drift']+s['batch_shift']
    if phase=='fault':target=97.5+s['load']*3
    elif phase in ('paused','shortage','short_stop','changeover'):target=p['temperature']-4
    temperature=round(approach(d['temperature'],target,.75,dt)+r.uniform(-.09,.09),2)
    busy=phase=='producing'
    pressure_target=p['pressure']*(1+s['load']) if busy else .35 if phase in ('fault','cooling','awaiting_resume') else 1.2
    pressure=round(max(0,approach(d['pressure'],pressure_target,.9,dt)+r.uniform(-.035,.035)),3)
    vibration_target=p['vibration']*(1+s['load']*2) if busy else .18
    vibration=round(max(0,approach(d['vibration'],vibration_target,.3,dt)+r.uniform(-.025,.025)),3)
    if temperature>90 and not s['resume_required']:
        s['resume_required']=True;transition(c,run,s,'fault');fault_alarm(c,run,stamp);busy=False
        phase=s['phase']
    if phase in ('warming','cooling'):
        s['stable']=s['stable']+dt if abs(temperature-p['temperature'])<=1.2 else 0
        if s['stable']>=6:
            transition(c,run,s,'awaiting_resume' if s['resume_required'] else 'producing')
            s['cycle_target']=p['cycle']*r.uniform(.88,1.15)
    elif phase in ('short_stop','changeover') and s['phase_elapsed']>=s.get('hold_seconds',12):
        if phase=='changeover':
            flush_quality(c,run,s,o,stamp);s['batch']+=1;s['batch_n']=s['batch_bad']=0;s['batch_shift']=r.uniform(-.65,.65);s['settling']=5
            c.execute('UPDATE orders SET batch=? WHERE id=?',(o['code']+'-B%02d'%s['batch'],o['id']))
        transition(c,run,s,'warming')
    elif phase=='producing' and s['phase']=='producing':
        s['cycle_elapsed']+=dt
        if s['cycle_elapsed']>=s['cycle_target']:
            s['cycle_elapsed']-=s['cycle_target'];s['cycle_target']=p['cycle']*(1+s['load']*.3)*r.uniform(.86,1.18)
            completed=o['completed']+1;s['produced']+=1
            c.execute('UPDATE orders SET completed=?,status=? WHERE id=?',(completed,'已完成' if completed>=o['quantity'] else '生产中',o['id']))
            c.execute('INSERT INTO production_reports(order_id,quantity,user_id,created_at) VALUES(?,?,?,?)',(o['id'],1,run['user_id'],stamp))
            c.execute('UPDATE materials SET stock=round(stock-?,6) WHERE id=?',(p['usage'],m['id']))
            c.execute('INSERT INTO stock_moves(material_id,direction,quantity,note,user_name,created_at) VALUES(?,?,?,?,?,?)',(m['id'],'出库',p['usage'],'模拟耗料 · '+o['code'],'演示采集器',stamp))
            risk=min(.35,p['risk']+abs(temperature-p['temperature'])*.016+abs(s['load'])*.10+(.07 if s['settling'] else 0)+abs(s['batch_shift'])*.02)
            s['pending_n']+=1;s['pending_bad']+=int(r.random()<risk);s['settling']=max(0,s['settling']-1)
            audit(c,actor(run),'演示报工 +1 件',o['code'],'计划模拟节拍 %.1fs；耗料 %.3fkg'%(s['cycle_target'],p['usage']))
            if s['pending_n']>=10 or completed>=o['quantity']:flush_quality(c,run,s,o,stamp)
            if completed>=o['quantity']:transition(c,run,s,'stopped')
            elif s['produced']>=s['next_stop']:
                s['stops']+=1;next_phase='changeover' if s['stops']%2==0 else 'short_stop'
                transition(c,run,s,next_phase);s['hold_seconds']=r.randint(15,24) if next_phase=='changeover' else r.randint(6,12)
                s['next_stop']=s['produced']+r.randint(13,21)
    status='预警' if s['resume_required'] else '运行' if s['phase']=='producing' else '待机'
    c.execute('UPDATE devices SET temperature=?,pressure=?,vibration=?,status=?,runtime=runtime+?,updated_at=? WHERE id=?',(temperature,pressure,vibration,status,dt if busy else 0,stamp,run['device_id']))
    c.execute('INSERT INTO readings(device_id,temperature,pressure,vibration,created_at) VALUES(?,?,?,?,?)',(run['device_id'],temperature,pressure,vibration,stamp))
    c.execute('DELETE FROM readings WHERE device_id=? AND id NOT IN (SELECT id FROM (SELECT id FROM readings WHERE device_id=? ORDER BY id DESC LIMIT 2400) AS retained)',(run['device_id'],run['device_id']))
    details={'warming':'温度连续稳定6秒后开始生产','producing':'节拍约 %.1fs · %.3fkg/件 · 每10件检测'%(s['cycle_target'],p['usage']),
      'fault':'温控故障联锁，报工与耗料已阻断','cooling':'温度渐变回落，稳定后等待人工确认','awaiting_resume':'已进入稳定窗口，请确认复产；异常需另行复检',
      'short_stop':'现场短停，暂停产出，参数回落','changeover':'换料期间停止产出，结束后新建生产批次','paused':'工单暂停，等待生产管理恢复','shortage':'库存不足，等待补料','stopped':'本次演示结束'}
    save(c,run,s,stamp,tick=tick,running=int(s['phase']!='stopped'),reason=details[s['phase']])

class LiveRuntime:
    def __init__(self):
        self.stop_event=threading.Event()
        with connect() as c:
            for run in rows(c,'SELECT * FROM demo_runs WHERE running=1'):
                s=state_of(run);s['phase']='stopped';s['cycle_elapsed']=0
                save(c,run,s,now(),running=0,reason='服务重启，请手动继续演示')
                c.execute("UPDATE devices SET status='待机' WHERE id=?",(run['device_id'],))
        self.thread=threading.Thread(target=self.run,daemon=True,name='demo-telemetry');self.thread.start()
    def run(self):
        while not self.stop_event.wait(INTERVAL):
            try:
                with connect() as c:
                    c.begin_write()
                    for run in rows(c,'SELECT * FROM demo_runs WHERE running=1'):advance(c,run)
            except Exception:traceback.print_exc()
    def close(self):self.stop_event.set();self.thread.join(timeout=5)
