"""Application services. Authorization is enforced here for every object."""
import json,math,secrets,csv,io,base64
from datetime import datetime
from .db import connect,rows,one,now,audit,DATA,password_hash,check_password
from .analytics import analyze
from .assistant import answer as assistant_answer,provider_status,PRESETS
from .live import (annotate,snapshot,control,timeline,demo_owns_device,defense_owns_device,
                   defense_owns_material,record_equipment_review,WAREHOUSE_ACTIONS)

class ApiError(Exception):
    def __init__(self,message,status=400):self.message=message;self.status=status
def required(b,key,limit=300):
    value=b.get(key)
    if not isinstance(value,str) or not value.strip() or len(value.strip())>limit:raise ApiError("请填写有效的"+key)
    return value.strip()
def number(b,key,minimum=0,maximum=1000000,integer=False):
    v=b.get(key)
    if isinstance(v,bool):raise ApiError(key+"数值不合法")
    try:v=float(v)
    except (TypeError,ValueError):raise ApiError(key+"必须为数值")
    if not math.isfinite(v) or v<minimum or v>maximum or (integer and not v.is_integer()):raise ApiError(key+"超出允许范围")
    return int(v) if integer else v
def role(user,*allowed):
    if user["role"] not in ("admin",)+allowed:raise ApiError("当前角色没有此操作权限",403)
def scope(user,requested=None):
    if user["role"]!="admin":
        if requested not in (None,"",str(user["factory_id"]),user["factory_id"]):raise ApiError("无权访问其他工厂",403)
        return user["factory_id"]
    if requested not in (None,""):
        try:f=int(requested)
        except (ValueError,TypeError):raise ApiError("工厂编号无效")
        if f not in (1,2,3):raise ApiError("工厂不存在",404)
        return f
    return None
def get_entity(c,user,table,id):
    if table not in ("devices","orders","anomalies","analyses","tasks","materials"):raise ApiError("不支持的资源")
    record=one(c,"SELECT * FROM "+table+" WHERE id=?",(id,))
    if not record:raise ApiError("记录不存在",404)
    scope(user,record["factory_id"])
    return record
def list_scoped(c,user,table,params,extra="",limit=500):
    f=scope(user,params.get("factory_id"));where=" WHERE factory_id=?" if f else "";args=(f,) if f else ()
    records=rows(c,"SELECT * FROM "+table+where+extra+" ORDER BY id DESC LIMIT "+str(limit),args)
    if table in ("devices","orders","quality","materials"):
        sources={r["record_id"]:r for r in rows(c,"SELECT * FROM source_records WHERE entity=?",(table,))}
        for record in records:
            src=sources.get(record["id"])
            record["source"]=src["label"] if src else "平台业务数据"
            record["archived"]=bool(src)
    return annotate(c,table,records)
def decode_job(j,user):
    if not j:return None
    for k in ("config","history","result"):j[k]=json.loads(j[k])
    if user["role"]!="admin":
        j["result"]["factories"]=[f for f in j["result"].get("factories",[]) if f["factory_id"]==user["factory_id"]]
        for h in j["history"]:
            if "nodes" in h:h["nodes"]=[n for n in h["nodes"] if n["factory_id"]==user["factory_id"]]
    return j

def dispatch(method,path,p,b,user,federation):
    with connect() as c:
        if method!="GET":c.begin_write()
        if path=="/api/workforce" or path.startswith("/api/workforce/"):
            from .workforce import dispatch as workforce_dispatch
            return workforce_dispatch(c,method,path,p,b,user)
        if method=="GET":
            if path in ('/api/live','/api/live/timeline'):
                if path.endswith('/timeline'):role(user,'engineer','manager')
                f=scope(user,p.get('factory_id')) or 1
                c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                c.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY')
                if path.endswith('/timeline'):
                    return timeline(c,f,number(p,'run_id',1,2147483647,True))
                did=p.get('device_id')
                if did:get_entity(c,user,'devices',int(did))
                return snapshot(c,f,int(did) if did else None)
            if path=="/api/meta":
                return {"user":{k:v for k,v in user.items() if k!="token"},"factories":rows(c,"SELECT * FROM factories"+(" WHERE id=?" if user["role"]!="admin" else ""),(user["factory_id"],) if user["role"]!="admin" else ()),
                 "users":rows(c,"SELECT id,username,name,role,factory_id,active FROM users WHERE factory_id=? OR (role='admin' AND ?='admin')",(scope(user,p.get("factory_id")) or 1,user["role"])),
                 "source":"内置样例为模拟工厂数据；导入记录按来源单独标识","version":"1.5.0"}
            if path=="/api/overview":
                f=scope(user,p.get("factory_id"));w=" WHERE factory_id=?" if f else "";args=(f,) if f else ()
                dev=list_scoped(c,user,'devices',p);orders=rows(c,"SELECT * FROM orders"+w+(" AND " if f else " WHERE ")+"status NOT IN ('历史归档','已取消')",args)
                qs=rows(c,"SELECT * FROM quality"+w+" ORDER BY created_at DESC LIMIT 500",args)
                today=datetime.now().date().isoformat();daily=[q for q in qs if q["created_at"].startswith(today)]
                n=sum(q["sample_size"] for q in daily);bad=sum(q["defects"] for q in daily)
                anomalies=rows(c,"SELECT * FROM anomalies"+w+(" AND " if f else " WHERE ")+"status!='已关闭' ORDER BY id DESC LIMIT 8",args)
                tasks=rows(c,"SELECT status,count(*) n FROM tasks"+w+" GROUP BY status",args)
                grouped={}
                for q in qs:
                    day=q["created_at"][:10];item=grouped.setdefault(day,{"date":day,"samples":0,"defects":0})
                    item["samples"]+=q["sample_size"];item["defects"]+=q["defects"]
                return {"devices":dev,"orders":orders,"alerts":anomalies,"tasks":tasks,"trend":sorted(grouped.values(),key=lambda x:x["date"])[-14:],
                 "kpi":{"production":sum(o["completed"] for o in orders),"planned":sum(o["quantity"] for o in orders),"quality_rate":1-bad/n if n else None,"sample_count":n,
                   "running":sum(d["fresh"] and d["status"]=="运行" for d in dev),"device_total":sum(not d['archived'] for d in dev),
                   "communication_unknown":sum(not d['fresh'] and not d['archived'] for d in dev),"archive_devices":sum(d['archived'] for d in dev),
                   "active_anomalies":c.execute("SELECT count(*) FROM anomalies"+w+(" AND " if f else " WHERE ")+"status!='已关闭'",args).fetchone()[0]},
                 "updated_at":now()}
            if path in ("/api/orders","/api/devices","/api/quality","/api/anomalies","/api/materials","/api/tasks"):
                result=list_scoped(c,user,path.split("/")[-1],p)
                if path=="/api/tasks":
                    for t in result:t["assignee_name"]=(one(c,"SELECT name FROM users WHERE id=?",(t["assignee"],)) or {}).get("name","未分配")
                    if user["role"]=="operator":result=[t for t in result if t["assignee"]==user["id"]]
                return result
            if path.startswith("/api/devices/"):
                item=get_entity(c,user,"devices",int(path.rsplit("/",1)[1]))
                item["readings"]=rows(c,"SELECT * FROM readings WHERE device_id=? ORDER BY id DESC LIMIT 40",(item["id"],))[::-1]
                return annotate(c,'devices',[item])[0]
            if path.startswith("/api/tasks/"):
                item=get_entity(c,user,"tasks",int(path.rsplit("/",1)[1]))
                if user["role"]=="operator" and item["assignee"]!=user["id"]:raise ApiError("仅能查看自己的任务",403)
                item["events"]=rows(c,"SELECT * FROM task_events WHERE task_id=? ORDER BY id",(item["id"],))
                item["attachments"]=rows(c,"SELECT id,original_name,mime,created_at FROM attachments WHERE task_id=?",(item["id"],))
                event=one(c,"SELECT order_id FROM anomalies WHERE id=?",(item["anomaly_id"],))
                item["review_type"]="quality" if event["order_id"] else "equipment"
                return item
            if path=="/api/analyses":
                data=list_scoped(c,user,"analyses",p,limit=30)
                for a in data:a["result"]=json.loads(a["result"])
                return data
            if path=="/api/samples":
                f=scope(user,p.get("factory_id")) or 1
                return {"count":c.execute("SELECT count(*) FROM samples WHERE factory_id=?",(f,)).fetchone()[0],
                 "sources":rows(c,"SELECT source,count(*) n FROM samples WHERE factory_id=? GROUP BY source",(f,)),
                 "preview":rows(c,"SELECT * FROM samples WHERE factory_id=? ORDER BY id DESC LIMIT 15",(f,))}
            if path=="/api/stock-moves":
                f=scope(user,p.get("factory_id"))
                return rows(c,"SELECT s.*,m.name,m.unit,m.factory_id FROM stock_moves s JOIN materials m ON m.id=s.material_id"+(" WHERE m.factory_id=?" if f else "")+" ORDER BY s.id DESC LIMIT 200",(f,) if f else ())
            if path=="/api/sources":
                f=scope(user,p.get("factory_id"))
                return rows(c,"SELECT source_key,label,entity,count(*) n,sha256,min(imported_at) imported_at FROM source_records"+(" WHERE factory_id=?" if f else "")+" GROUP BY source_key,label,entity,sha256",(f,) if f else ())
            if path=="/api/audit":
                role(user,"manager","engineer");return list_scoped(c,user,"audit",p,limit=200)
            if path=="/api/federation":
                jobs=[decode_job(j,user) for j in rows(c,"SELECT * FROM training_jobs ORDER BY created_at DESC LIMIT 8")]
                events=rows(c,"SELECT * FROM training_events WHERE job_id=? ORDER BY id DESC LIMIT 200",(jobs[0]["id"],)) if jobs else []
                if user["role"]!="admin":events=[e for e in events if e["factory_id"] in (None,user["factory_id"])]
                return {"nodes":federation.status(),"jobs":jobs,"events":events,"pause_requested":federation.pause_event.is_set(),"description":"本机三个独立 HTTP 节点，独立数据库，真实本地训练与参数聚合","privacy":"模型参数与汇总指标跨节点传输；本版本没有差分隐私、安全聚合或跨网络 TLS。"}
            if path=="/api/assistant":
                f=scope(user,p.get("factory_id")) or 1
                messages=rows(c,"SELECT id,question,response,created_at FROM assistant_messages WHERE user_id=? AND factory_id=? ORDER BY id DESC LIMIT 20",(user["id"],f))
                for m in messages:m["response"]=json.loads(m["response"])
                return {"messages":messages[::-1],"provider":provider_status(),"presets":PRESETS}
            if path=="/api/users":
                role(user,"manager")
                f=scope(user,p.get("factory_id"))
                return rows(c,"SELECT id,username,name,role,factory_id,active FROM users"+(" WHERE factory_id=?" if f else ""),(f,) if f else ())
            raise ApiError("接口不存在",404)

        if path=="/api/live/demo":
            action=b.get('action')
            if action=='prepare-defense' or action in WAREHOUSE_ACTIONS:role(user,'engineer')
            else:role(user,'engineer','manager')
            f=scope(user,b.get('factory_id')) or 1
            if action not in ('prepare-defense','start','stop','fault','recover','resume','short-stop','changeover')+WAREHOUSE_ACTIONS:raise ApiError('不支持的演示操作')
            if action in WAREHOUSE_ACTIONS:
                return control(c,user,f,action,intended_run_id=number(b,'run_id',1,2147483647,True))
            return control(c,user,f,action)
        if path=="/api/password":
            old=required(b,"old_password");new=required(b,"new_password")
            u=one(c,"SELECT * FROM users WHERE id=?",(user["id"],))
            if not check_password(old,u["password"]):raise ApiError("原密码不正确")
            if len(new)<10 or not any(x.isdigit() for x in new) or not any(x.isalpha() for x in new):raise ApiError("新密码至少10位，包含字母和数字")
            c.execute("UPDATE users SET password=? WHERE id=?",(password_hash(new),user["id"]))
            audit(c,user,"修改密码","用户");return {"message":"密码已更新"}
        if path=="/api/orders":
            role(user,"manager","engineer")
            f=scope(user,b.get("factory_id")) or 1;device=get_entity(c,user,"devices",number(b,"device_id",1,100000,True))
            if device["factory_id"]!=f:raise ApiError("设备与工厂不一致")
            due=required(b,"due_date")
            try:datetime.strptime(due,"%Y-%m-%d")
            except ValueError:raise ApiError("交期格式应为 YYYY-MM-DD")
            code="MO-"+datetime.now().strftime("%m%d")+"-"+secrets.token_hex(2).upper()
            id=c.execute("INSERT INTO orders(factory_id,code,product,batch,quantity,status,priority,due_date,device_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
             (f,code,required(b,"product"),required(b,"batch"),number(b,"quantity",1,1000000,True),"待排产","紧急" if b.get("priority")=="紧急" else "普通",due,device["id"],now())).lastrowid
            audit(c,user,"创建生产工单",str(id),code,f);return {"id":id,"code":code}
        if path.startswith("/api/orders/"):
            o=get_entity(c,user,"orders",int(path.split("/")[3]));action=b.get("action")
            if action=="report":
                role(user,"operator","engineer","manager")
                if one(c,'SELECT id FROM demo_runs WHERE order_id=?',(o['id'],)):raise ApiError('演示产线由采集器自动报工，不能手动补报；请使用普通生产工单',409)
                if o["status"]!="生产中":raise ApiError("只有生产中的工单可以报工")
                qty=number(b,"quantity",1,1000000,True)
                if o["completed"]+qty>o["quantity"]:raise ApiError("报工数量超过剩余计划数量")
                completed=o["completed"]+qty
                c.execute("UPDATE orders SET completed=?,status=? WHERE id=?",(completed,"已完成" if completed==o["quantity"] else "生产中",o["id"]))
                c.execute("INSERT INTO production_reports(order_id,quantity,user_id,created_at) VALUES(?,?,?,?)",(o["id"],qty,user["id"],now()))
            else:
                role(user,"engineer","manager")
                target={"start":"生产中","pause":"已暂停","resume":"生产中","cancel":"已取消"}.get(action)
                valid={"待排产":["start","cancel"],"生产中":["pause"],"已暂停":["resume","cancel"]}
                if action not in valid.get(o["status"],[]):raise ApiError("当前工单状态不允许此操作")
                if action in ('start','resume') and defense_owns_device(c,o['device_id'],o['id']):
                    raise ApiError('设备正在进行答辩演示，请停止演示后再启动生产工单',409)
                c.execute("UPDATE orders SET status=? WHERE id=?",(target,o["id"]))
            audit(c,user,"生产工单 "+str(action),str(o["id"]),factory=o["factory_id"]);return {"ok":True}
        if path.startswith("/api/devices/") and path.endswith("/reading"):
            role(user,"operator","engineer","manager")
            d=get_entity(c,user,"devices",int(path.split("/")[3]))
            if demo_owns_device(c,d['id']):raise ApiError('演示设备由工况采集器维护，请在大屏切换工况',409)
            t=number(b,"temperature",-50,500);pr=number(b,"pressure",0,50);v=number(b,"vibration",0,100)
            status="预警" if t>90 or pr>8 or v>3 else "运行"
            c.execute("UPDATE devices SET temperature=?,pressure=?,vibration=?,status=?,updated_at=? WHERE id=?",(t,pr,v,status,now(),d["id"]))
            c.execute("INSERT INTO readings(device_id,temperature,pressure,vibration,created_at) VALUES(?,?,?,?,?)",(d["id"],t,pr,v,now()))
            if status=="预警" and not one(c,"SELECT id FROM anomalies WHERE device_id=? AND status!='已关闭'",(d["id"],)):
                c.execute("INSERT INTO anomalies(factory_id,device_id,title,severity,description,source,created_at) VALUES(?,?,?,?,?,?,?)",
                 (d["factory_id"],d["id"],d["name"]+"运行参数越限","高","温度 %.1f℃，压力 %.2fMPa，振动 %.2fmm/s"%(t,pr,v),"手动采集记录",now()))
            audit(c,user,"记录设备采集值",str(d["id"]),factory=d["factory_id"]);return {"status":status}
        if path=="/api/quality":
            role(user,"operator","engineer","manager")
            o=get_entity(c,user,"orders",number(b,"order_id",1,1000000,True));n=number(b,"sample_size",1,1000000,True);bad=number(b,"defects",0,n,True)
            if o["status"]=="历史归档":raise ApiError("历史工单仅供追溯，请选择当前生产工单")
            dtype=required(b,"defect_type")
            id=c.execute("INSERT INTO quality(factory_id,order_id,batch,sample_size,defects,defect_type,inspector,created_at) VALUES(?,?,?,?,?,?,?,?)",
             (o["factory_id"],o["id"],o["batch"],n,bad,dtype,user["name"],now())).lastrowid
            if bad/n>.05:
                if not one(c,"SELECT id FROM anomalies WHERE order_id=? AND status!='已关闭'",(o["id"],)):
                    c.execute("INSERT INTO anomalies(factory_id,device_id,order_id,title,severity,description,source,created_at) VALUES(?,?,?,?,?,?,?,?)",
                     (o["factory_id"],o["device_id"],o["id"],o["product"]+"质检异常","高","抽检 %s 件，不合格 %s 件，不合格率 %.1f%%"%(n,bad,bad/n*100),"用户录入质检",now()))
            audit(c,user,"新增质检",str(id),factory=o["factory_id"]);return {"id":id,"rate":bad/n}
        if path=="/api/analyze":
            role(user,"engineer","manager")
            a=get_entity(c,user,"anomalies",number(b,"anomaly_id",1,1000000,True))
            if not a["order_id"]:raise ApiError("此事件未关联质量批次，不能套用质量因果模型。请直接创建现场检查工单。")
            source=b.get("source") or "已知生成机制的模拟工艺样本"
            if not isinstance(source,str) or not one(c,"SELECT id FROM samples WHERE factory_id=? AND source=?",(a["factory_id"],source)):raise ApiError("请选择本厂已有的样本来源")
            result=analyze(c,a["factory_id"],source)
            result["context"]={"anomaly_id":a["id"],"title":a["title"],"batch_scope":"本厂工艺样本用于候选原因分析，尚未证明当前批次的个体原因"}
            id=c.execute("INSERT INTO analyses(factory_id,anomaly_id,result,created_at) VALUES(?,?,?,?)",(a["factory_id"],a["id"],json.dumps(result,ensure_ascii=False),now())).lastrowid
            if a["status"]=="待分析":c.execute("UPDATE anomalies SET status='待处置' WHERE id=?",(a["id"],))
            audit(c,user,"完成原因分析",str(a["id"]),"分析编号 "+str(id),a["factory_id"])
            return {"id":id,"factory_id":a["factory_id"],"anomaly_id":a["id"],"result":result}
        if path=="/api/tasks":
            role(user,"engineer","manager")
            a=get_entity(c,user,"anomalies",number(b,"anomaly_id",1,1000000,True))
            if a["status"]=="已关闭":raise ApiError("该异常已关闭")
            assignee=number(b,"assignee",1,1000000,True)
            assigned=one(c,"SELECT id FROM users WHERE id=? AND factory_id=? AND active=1",(assignee,a["factory_id"]))
            if not assigned:raise ApiError("处理人必须属于该工厂")
            analysis_id=b.get("analysis_id")
            if analysis_id:
                analysis_record=get_entity(c,user,"analyses",int(analysis_id))
                if analysis_record["anomaly_id"]!=a["id"]:raise ApiError("分析结果与异常不一致")
            if one(c,"SELECT id FROM tasks WHERE anomaly_id=? AND status!='已关闭'",(a["id"],)):raise ApiError("该异常已经有进行中的处置工单",409)
            from .workforce import dispatch_note
            staffing_note=dispatch_note(c,user,b,a)
            id=c.execute("INSERT INTO tasks(factory_id,anomaly_id,analysis_id,title,action,assignee,status,priority,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
             (a["factory_id"],a["id"],analysis_id,a["title"],required(b,"action",2000),assignee,"待接单",a["severity"],now(),now())).lastrowid
            c.execute("UPDATE anomalies SET status='处置中' WHERE id=?",(a["id"],))
            c.execute("INSERT INTO task_events(task_id,user_name,action,note,created_at) VALUES(?,?,?,?,?)",(id,user["name"],"创建工单",b["action"]+"\n"+staffing_note,now()))
            audit(c,user,"创建处置工单",str(id),factory=a["factory_id"]);return {"id":id}
        if path.startswith("/api/tasks/"):
            t=get_entity(c,user,"tasks",int(path.split("/")[3]));action=b.get("action")
            if user["role"]=="operator" and t["assignee"]!=user["id"]:raise ApiError("只能处理分配给自己的工单",403)
            if path.endswith("/photo"):
                role(user,"operator","engineer","manager")
                if t["status"] not in ("待接单","处理中"):raise ApiError("仅可在现场处理阶段补充照片")
                if user["role"]!="admin" and t["assignee"]!=user["id"]:raise ApiError("请由指定处理人上传照片",403)
                raw=required(b,"data",3000000)
                try:image=base64.b64decode(raw,validate=True)
                except Exception:raise ApiError("图片格式不正确")
                if len(image)>2*1024*1024:raise ApiError("图片不得超过2MB")
                ext="png" if image.startswith(b"\x89PNG\r\n\x1a\n") else "jpg" if image.startswith(b"\xff\xd8\xff") else None
                if not ext:raise ApiError("仅支持 PNG 或 JPEG 图片")
                name=secrets.token_hex(16)+"."+ext;(DATA/"uploads"/name).write_bytes(image)
                c.execute("INSERT INTO attachments(task_id,filename,original_name,mime,created_at) VALUES(?,?,?,?,?)",(t["id"],name,required(b,"name"),"image/png" if ext=="png" else "image/jpeg",now()))
                audit(c,user,"上传现场照片",str(t["id"]),factory=t["factory_id"]);return {"ok":True}
            version=number(b,"version",1,1000000,True)
            if version!=t["version"]:raise ApiError("工单已更新，请刷新后重试",409)
            note=str(b.get("note","")).strip()[:2000]
            if action=="accept":
                role(user,"operator","engineer","manager")
                if user["role"]!="admin" and t["assignee"]!=user["id"]:raise ApiError("请由指定处理人接单",403)
                if t["status"]!="待接单":raise ApiError("当前状态不可接单")
                status="处理中"
            elif action=="submit":
                role(user,"operator","engineer","manager")
                if user["role"]!="admin" and t["assignee"]!=user["id"]:raise ApiError("请由指定处理人提交",403)
                if t["status"]!="处理中" or not note:raise ApiError("请在处理中填写实际处置记录")
                status="待复检";c.execute("UPDATE tasks SET note=? WHERE id=?",(note,t["id"]))
            elif action=="review":
                role(user,"engineer","manager")
                if t["status"]!="待复检":raise ApiError("当前工单尚未提交复检")
                if not note:raise ApiError("请填写复检说明")
                a=get_entity(c,user,"anomalies",t["anomaly_id"])
                if a["order_id"]:
                    n=number(b,"sample_size",1,1000000,True);bad=number(b,"defects",0,n,True)
                    status="已关闭" if bad/n<=.05 else "处理中"
                    c.execute("UPDATE tasks SET review_note=?,sample_size=?,defects=? WHERE id=?",(note,n,bad,t["id"]))
                    o=one(c,"SELECT batch FROM orders WHERE id=?",(a["order_id"],))
                    c.execute("INSERT INTO quality(factory_id,order_id,batch,sample_size,defects,defect_type,inspector,created_at) VALUES(?,?,?,?,?,?,?,?)",
                     (t["factory_id"],a["order_id"],o["batch"],n,bad,"处置后复检",user["name"],now()))
                    note+="；抽检 %s，不合格 %s，%s"%(n,bad,"复检通过" if status=="已关闭" else "退回继续处理")
                else:
                    passed=b.get("inspection_pass") in (True,"true")
                    status="已关闭" if passed else "处理中"
                    c.execute("UPDATE tasks SET review_note=? WHERE id=?",(note,t["id"]))
                    note+="；设备点检"+("通过" if passed else "未通过，退回处理")
                c.execute("UPDATE anomalies SET status=? WHERE id=?",("已关闭" if status=="已关闭" else "处置中",t["anomaly_id"]))
            else:raise ApiError("无效的工单操作")
            c.execute("UPDATE tasks SET status=?,version=version+1,updated_at=? WHERE id=?",(status,now(),t["id"]))
            event_id=c.execute("INSERT INTO task_events(task_id,user_name,action,note,created_at) VALUES(?,?,?,?,?)",(t["id"],user["name"],status,note,now())).lastrowid
            if action=='review' and not a['order_id']:
                record_equipment_review(c,a,t['id'],event_id,passed)
            audit(c,user,"工单"+status,str(t["id"]),note,t["factory_id"]);return {"status":status}
        if path.startswith("/api/materials/"):
            role(user,"operator","engineer","manager")
            m=get_entity(c,user,"materials",int(path.split("/")[3]));qty=number(b,"quantity",.01,1000000)
            if one(c,"SELECT 1 FROM source_records WHERE entity='materials' AND record_id=?",(m["id"],)):raise ApiError("历史库存存档仅供查询，不能作为当前可用库存出入库")
            if defense_owns_material(c,m):raise ApiError('答辩演示原料请通过设备监控的模拟库位操作移库',409)
            direction=b.get("direction")
            if direction not in ("入库","出库"):raise ApiError("请选择入库或出库")
            new=m["stock"]+(qty if direction=="入库" else -qty)
            if new<0:raise ApiError("库存不足，无法出库")
            note=required(b,"note",1000)
            c.execute("UPDATE materials SET stock=? WHERE id=?",(new,m["id"]))
            c.execute("INSERT INTO stock_moves(material_id,direction,quantity,note,user_name,created_at) VALUES(?,?,?,?,?,?)",(m["id"],direction,qty,note,user["name"],now()))
            audit(c,user,direction,str(m["id"]),str(qty)+" "+m["unit"],m["factory_id"]);return {"stock":new}
        if path=="/api/samples/import":
            role(user,"engineer","manager")
            f=scope(user,b.get("factory_id")) or 1;content=required(b,"csv",2000000);source=required(b,"source",120)
            parsed=list(csv.DictReader(io.StringIO(content.lstrip("\ufeff"))))
            if not 1<=len(parsed)<=10000:raise ApiError("每次导入1至10000行")
            values=[]
            for i,r in enumerate(parsed,2):
                if any(r.get(k) not in ("0","1") for k in ("temp","pressure","wear","material","product","defect")):raise ApiError("第 %s 行：六个数据字段必须是 0 或 1"%i)
                values.append((f,)+tuple(int(r[k]) for k in ("temp","pressure","wear","material","product","defect"))+("用户导入："+source,now()))
            c.executemany("INSERT INTO samples(factory_id,temp,pressure,wear,material,product,defect,source,created_at) VALUES(?,?,?,?,?,?,?,?,?)",values)
            audit(c,user,"导入工艺样本",str(f),str(len(values))+"行；"+source,f)
            return {"count":len(values),"message":"已追加到本厂分析样本；联邦节点仍使用独立模拟数据"}
        if path=="/api/federation/predict":
            role(user,"engineer","manager")
            f=scope(user,b.get("factory_id")) or 1
            features=[number(b,k,0,1,True) for k in ("temp","pressure","wear","material","product")]
            try:return federation.call(f,"predict",{"features":features})
            except Exception:raise ApiError("本厂模型尚不可用，请完成一次联合训练并确认节点在线")
        if path=="/api/assistant/ask":
            f=scope(user,b.get("factory_id")) or 1
            question=required(b,"question",1500);source=b.get("source") or "已知生成机制的模拟工艺样本"
            if not isinstance(source,str) or not one(c,"SELECT id FROM samples WHERE factory_id=? AND source=?",(f,source)):raise ApiError("请选择本厂已有的样本来源")
            a=get_entity(c,user,"anomalies",number(b,"anomaly_id",1,1000000,True)) if b.get("anomaly_id") else None
            if a and a["factory_id"]!=f:raise ApiError("异常与当前工厂不一致")
            use_model=b.get("use_model",False)
            if not isinstance(use_model,bool):raise ApiError("模型选项无效")
            try:result=assistant_answer(c,user,f,question,source,a,str(b.get("scenario","quality")),use_model)
            except ValueError as e:raise ApiError(str(e))
            audit(c,user,"因果问答",str(result["id"]),"模式："+result["response"]["mode"],f)
            return result
        if path=="/api/federation/pause":
            role(user);paused=b.get("paused")
            if not isinstance(paused,bool):raise ApiError("暂停状态必须为布尔值")
            try:federation.pause(paused)
            except ValueError as e:raise ApiError(str(e),409)
            audit(c,user,"请求暂停训练" if paused else "恢复训练","训练")
            return {"paused":paused}
        if path=="/api/federation/start":
            role(user)
            rounds=number(b,"rounds",2,30,True);epochs=number(b,"epochs",2,15,True)
            # Release SQLite write lock before the coordinator persists its job.
            c.commit()
            pace=number(b,"pace",0,3) if "pace" in b else 0
            try:id=federation.start(rounds,epochs,pace)
            except ValueError as e:raise ApiError(str(e),409)
            audit(c,user,"启动联邦训练",id);return {"id":id}
        if path=="/api/federation/cancel":
            role(user);federation.stop_event.set();audit(c,user,"取消联邦训练","训练");return {"ok":True}
        if path.startswith("/api/federation/nodes/"):
            role(user);f=int(path.rsplit("/",1)[1])
            if f not in (1,2,3):raise ApiError("节点不存在",404)
            enabled=b.get("enabled")
            if not isinstance(enabled,bool):raise ApiError("节点状态必须为布尔值")
            c.commit()
            if enabled:federation.start_node(f)
            else:federation.stop_node(f)
            c.execute("UPDATE node_status SET enabled=? WHERE factory_id=?",(int(enabled),f));audit(c,user,"节点上线" if enabled else "节点离线",str(f))
            return {"online":enabled}
        raise ApiError("接口不存在",404)
