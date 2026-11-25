"""Meaningful service integration tests against an isolated temporary database."""
import unittest,tempfile,subprocess,sys,os,time,json,urllib.request,urllib.error,http.cookiejar,socket,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.ml import train,metrics,aggregate
from backend.db import observations,connect
from mysql_support import TestDatabases

class Client:
    def __init__(self,base,user="admin"):
        self.base=base;self.csrf=""
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        _,u=self.call("/login",{"username":user,"password":"Zyyl@2026"});self.csrf=u["csrf"]
    def call(self,path,body=None,key=None,csrf=True):
        headers={"Content-Type":"application/json"}
        if csrf:headers["X-CSRF-Token"]=self.csrf
        if key:headers["Idempotency-Key"]=key
        request=urllib.request.Request(self.base+"/api"+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        try:
            with self.opener.open(request,timeout=30) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)

class PlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mysql=TestDatabases();cls.addClassCleanup(cls.mysql.close)
        cls.tmp=tempfile.TemporaryDirectory(prefix="zyyl-tests-")
        cls.data=Path(cls.tmp.name)
        with socket.socket() as s:s.bind(("127.0.0.1",0));cls.port=s.getsockname()[1]
        cls.base="http://127.0.0.1:"+str(cls.port)
        cls.start_server()
        cls.admin=Client(cls.base);cls.eng=Client(cls.base,"engineer");cls.op=Client(cls.base,"operator");cls.other=Client(cls.base,"factory_b")
    @classmethod
    def start_server(cls):
        env=os.environ.copy();env["ZY_DATA_DIR"]=str(cls.data);env["PYTHONUTF8"]="1";env["ZY_MYSQL_CONFIG"]=str(cls.mysql.path)
        cls.log=(cls.data/"server.log").open("ab")
        cls.proc=subprocess.Popen([sys.executable,"-B","run.py","--port",str(cls.port)],cwd=ROOT,env=env,stdout=cls.log,stderr=cls.log)
        for _ in range(150):
            try:
                with urllib.request.urlopen(cls.base+"/api/health",timeout=.5):return
            except Exception:
                if cls.proc.poll() is not None:
                    cls.log.close()
                    raise RuntimeError((cls.data/"server.log").read_text(encoding="utf-8"))
                time.sleep(.1)
        raise RuntimeError("Server did not start")
    @classmethod
    def tearDownClass(cls):
        # Stop workers through the authenticated API before terminating the test server.
        try:
            for i in (1,2,3):cls.admin.call("/federation/nodes/"+str(i),{"enabled":False})
        finally:
            cls.proc.terminate();cls.proc.wait(timeout=10);cls.log.close()
        cls.tmp.cleanup()
    def test_01_login_and_factory_isolation(self):
        self.assertEqual(self.eng.call("/devices?factory_id=2")[0],403)
        self.assertEqual(self.other.call("/devices/1")[0],403)
        self.assertEqual(self.op.call("/audit?factory_id=1")[0],403)
        self.assertEqual(self.op.call("/federation/start",{"rounds":2,"epochs":2})[0],403)
        self.assertEqual(self.eng.call("/quality",{},csrf=False)[0],403)
    def test_02_stock_transaction_and_idempotency(self):
        _,items=self.eng.call("/materials?factory_id=1");m=next(x for x in items if not x["archived"])
        req={"direction":"出库","quantity":m["stock"]+1,"note":"测试库存边界"}
        self.assertEqual(self.eng.call("/materials/"+str(m["id"]),req)[0],400)
        req={"direction":"入库","quantity":7,"note":"幂等测试"}
        a=self.eng.call("/materials/"+str(m["id"]),req,key="test-same")
        b=self.eng.call("/materials/"+str(m["id"]),req,key="test-same")
        self.assertEqual(a,b)
        _,items=self.eng.call("/materials?factory_id=1")
        self.assertEqual(next(i for i in items if i["id"]==m["id"])["stock"],m["stock"]+7)
    def test_03_production_quality_alert(self):
        code,o=self.eng.call("/orders",{"factory_id":1,"product":"测试零件","batch":"QA-LOT","quantity":20,"due_date":"2026-12-01","device_id":1})
        self.assertEqual(code,200);id=o["id"]
        self.assertEqual(self.op.call("/orders/"+str(id),{"action":"report","quantity":1})[0],400)
        self.assertEqual(self.eng.call("/orders/"+str(id),{"action":"start"})[0],200)
        self.assertEqual(self.op.call("/orders/"+str(id),{"action":"report","quantity":21})[0],400)
        self.assertEqual(self.op.call("/orders/"+str(id),{"action":"report","quantity":20})[0],200)
        self.assertEqual(self.eng.call("/quality",{"order_id":id,"sample_size":20,"defects":21,"defect_type":"外观"})[0],400)
        self.assertEqual(self.eng.call("/quality",{"order_id":id,"sample_size":20,"defects":3,"defect_type":"外观"})[0],200)
        _,alerts=self.eng.call("/anomalies?factory_id=1");self.assertTrue(any(a["order_id"]==id for a in alerts))
    def test_04_analysis_and_full_resolution_workflow(self):
        code,r=self.eng.call("/analyze",{"anomaly_id":1});self.assertEqual(code,200)
        self.assertEqual(r["result"]["sample_count"],1800)
        self.assertTrue(all(f["sufficient"] for f in r["result"]["factors"]))
        self.assertGreater(next(f for f in r["result"]["factors"] if f["key"]=="temp")["effect"],.08)
        self.assertEqual(self.eng.call("/tasks",{"anomaly_id":1,"analysis_id":r["id"],"assignee":5,"action":"跨厂派单"})[0],400)
        body={"anomaly_id":1,"analysis_id":r["id"],"assignee":3,"action":"检查工艺与温控","dispatch_note":"已确认临时支援人员与工艺技能"}
        code,t=self.eng.call("/tasks",body);self.assertEqual(code,200);id=t["id"]
        self.assertEqual(self.eng.call("/tasks",body)[0],409)
        self.assertEqual(self.other.call("/tasks/"+str(id))[0],403)
        self.assertEqual(self.op.call("/tasks/"+str(id),{"action":"accept","version":1})[0],200)
        self.assertEqual(self.op.call("/tasks/"+str(id),{"action":"submit","version":1,"note":"已检查"})[0],409)
        self.assertEqual(self.op.call("/tasks/"+str(id),{"action":"submit","version":2,"note":"检查传感器后恢复工艺条件"})[0],200)
        self.assertEqual(self.op.call("/tasks/"+str(id),{"action":"review","version":3,"note":"试图越权","sample_size":100,"defects":0})[0],403)
        code,result=self.eng.call("/tasks/"+str(id),{"action":"review","version":3,"note":"仍需进一步处理","sample_size":100,"defects":9})
        self.assertEqual(result["status"],"处理中")
        self.assertEqual(self.op.call("/tasks/"+str(id),{"action":"submit","version":4,"note":"再次检查完成"})[0],200)
        code,result=self.eng.call("/tasks/"+str(id),{"action":"review","version":5,"note":"复检合格","sample_size":100,"defects":2})
        self.assertEqual(result["status"],"已关闭")
        _,alerts=self.eng.call("/anomalies?factory_id=1");self.assertEqual(next(a for a in alerts if a["id"]==1)["status"],"已关闭")
    def test_05_import_is_atomic_and_isolated(self):
        self.assertEqual(self.eng.call("/samples/import",{"factory_id":2,"source":"测试","csv":"temp,pressure,wear,material,product,defect\n0,0,0,0,0,0"})[0],403)
        _,before=self.eng.call("/samples?factory_id=1")
        bad="temp,pressure,wear,material,product,defect\n0,0,0,0,0,0\n2,0,0,0,0,0"
        self.assertEqual(self.eng.call("/samples/import",{"factory_id":1,"source":"测试","csv":bad})[0],400)
        _,after=self.eng.call("/samples?factory_id=1");self.assertEqual(before["count"],after["count"])
    def test_06_real_federation(self):
        code,r=self.admin.call("/federation/start",{"rounds":5,"epochs":5});self.assertEqual(code,200)
        id=r["id"]
        for _ in range(150):
            _,state=self.admin.call("/federation");job=next(j for j in state["jobs"] if j["id"]==id)
            if job["status"] not in ("准备中","训练中"):break
            time.sleep(.1)
        self.assertEqual(job["status"],"已完成",job)
        self.assertEqual(len(job["history"]),5);self.assertEqual(len(job["result"]["factories"]),3)
        self.assertLess(job["history"][-1]["loss"],job["history"][0]["loss"])
        self.assertTrue(any(abs(w)>.01 for w in job["result"]["weights"]))
        code,pred=self.eng.call("/federation/predict",{"temp":1,"pressure":1,"wear":0,"material":0,"product":0})
        self.assertEqual(code,200);self.assertGreater(pred["risk"],0);self.assertLess(pred["risk"],1)
        self.admin.call("/federation/nodes/3",{"enabled":False})
        code,r=self.admin.call("/federation/start",{"rounds":2,"epochs":2});self.assertEqual(code,200)
        for _ in range(150):
            _,state=self.admin.call("/federation");job=next(j for j in state["jobs"] if j["id"]==r["id"])
            if job["status"] not in ("准备中","训练中"):break
            time.sleep(.1)
        self.assertEqual(job["status"],"已完成");self.assertEqual(len(job["result"]["factories"]),2)
        self.admin.call("/federation/nodes/2",{"enabled":False})
        self.assertEqual(self.admin.call("/federation/start",{"rounds":2,"epochs":2})[0],409)
        self.admin.call("/federation/nodes/2",{"enabled":True});self.admin.call("/federation/nodes/3",{"enabled":True})
    def test_07_persistence(self):
        with connect(config=self.mysql.config) as c:
            self.assertGreater(c.execute("SELECT count(*) FROM audit").fetchone()[0],5)
            self.assertIsNotNone(c.execute("SELECT id FROM orders WHERE batch='QA-LOT'").fetchone())
    def test_08_model_learning_and_aggregation(self):
        data=[(list(r[:5]),r[5]) for r in observations(101,500)]
        self.assertLess(metrics(data,train(data,epochs=60))["loss"],metrics(data,[0]*6)["loss"])
        self.assertEqual(aggregate([{"n":1,"weights":[0]*6},{"n":3,"weights":[4]*6}]),[3]*6)

    def test_09_source_import_and_sample_provenance(self):
        from backend.legacy import sql_values,import_snapshot
        self.assertEqual(sql_values("('a,b', 'it\\'s', NULL, '');"),[["a,b","it's",None,""]])
        with connect(config=self.mysql.config) as c:
            before=c.execute("SELECT count(*) FROM source_records").fetchone()[0]
            self.assertEqual(before,72)
            import_snapshot(c)
            self.assertEqual(c.execute("SELECT count(*) FROM source_records").fetchone()[0],before)
        _,devices=self.eng.call("/devices?factory_id=1")
        self.assertTrue(all(x["temperature"] is None for x in devices if x["archived"]))
        _,materials=self.eng.call("/materials?factory_id=1")
        archived=next(m for m in materials if m["archived"])
        self.assertEqual(self.eng.call("/materials/"+str(archived["id"]),{"direction":"入库","quantity":1,"note":"禁止修改历史余额"})[0],400)
        self.assertEqual(self.eng.call("/analyze",{"anomaly_id":2})[0],400)
        csv="temp,pressure,wear,material,product,defect\n0,0,0,0,0,0\n1,0,0,0,0,1"
        self.assertEqual(self.eng.call("/samples/import",{"factory_id":1,"source":"独立测试来源","csv":csv})[0],200)
        _,result=self.eng.call("/analyze",{"anomaly_id":1,"source":"用户导入：独立测试来源"})
        self.assertEqual(result["result"]["sample_count"],2)
        self.assertFalse(any(f["sufficient"] for f in result["result"]["factors"]))
        _,result=self.eng.call("/analyze",{"anomaly_id":1})
        self.assertEqual(result["result"]["sample_count"],1800)

    def test_10_equipment_review_does_not_invent_quality_samples(self):
        _,before=self.eng.call("/quality?factory_id=1")
        code,t=self.eng.call("/tasks",{"anomaly_id":2,"assignee":3,"action":"检查设备润滑与安全状态","dispatch_note":"已确认临时点检支援人员"})
        self.assertEqual(code,200)
        self.op.call("/tasks/"+str(t["id"]),{"action":"accept","version":1})
        self.op.call("/tasks/"+str(t["id"]),{"action":"submit","version":2,"note":"点检完成"})
        code,result=self.eng.call("/tasks/"+str(t["id"]),{"action":"review","version":3,"inspection_pass":True,"note":"现场复核通过"})
        self.assertEqual(result["status"],"已关闭")
        _,after=self.eng.call("/quality?factory_id=1")
        self.assertEqual(len(before),len(after))

    def test_11_restart_preserves_business_records(self):
        _,before=self.admin.call("/orders?factory_id=1")
        for i in (1,2,3):self.admin.call("/federation/nodes/"+str(i),{"enabled":False})
        self.__class__.proc.terminate();self.__class__.proc.wait(timeout=10);self.__class__.log.close()
        self.__class__.start_server();self.__class__.admin=Client(self.base)
        _,after=self.admin.call("/orders?factory_id=1")
        self.assertEqual(before,after)

    def test_12_duplicate_start_does_not_restart_running_service(self):
        env=os.environ.copy();env["ZY_DATA_DIR"]=str(self.data);env["PYTHONUTF8"]="1";env["ZY_MYSQL_CONFIG"]=str(self.mysql.path)
        _,before=self.admin.call("/federation")
        proc=subprocess.run([sys.executable,"-B","run.py","--port",str(self.port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        self.assertEqual(proc.returncode,0,proc.stderr)
        _,after=self.admin.call("/federation")
        self.assertEqual(before["jobs"],after["jobs"])

    def test_13_video_authorization_and_byte_ranges(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.base+"/api/media/factory.mp4")
        self.assertEqual(error.exception.code,401)
        request=urllib.request.Request(self.base+"/api/media/factory.mp4",headers={"Range":"bytes=0-31"})
        with self.admin.opener.open(request) as response:
            self.assertEqual(response.status,206);self.assertEqual(len(response.read()),32)
            self.assertTrue(response.headers["Content-Range"].startswith("bytes 0-31/"))
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.admin.opener.open(urllib.request.Request(self.base+"/api/media/factory.mp4",headers={"Range":"bytes=99999999-"}))
        self.assertEqual(error.exception.code,416)

    def test_14_causal_conversation_grounded_and_isolated(self):
        engineer=Client(self.base,"engineer");manager=Client(self.base,"manager")
        code,result=engineer.call("/assistant/ask",{"factory_id":1,"anomaly_id":1,"question":"为什么质量缺陷升高，应该先排查什么？"})
        self.assertEqual(code,200);self.assertIn("1800",result["response"]["answer"])
        self.assertEqual(result["response"]["mode"],"本地证据助手")
        self.assertTrue(result["response"]["analysis"]["id"])
        self.assertEqual(engineer.call("/assistant/ask",{"factory_id":2,"question":"查询二厂质量"})[0],403)
        self.assertEqual(engineer.call("/assistant?factory_id=2")[0],403)
        _,history=engineer.call("/assistant?factory_id=1")
        self.assertTrue(any(m["id"]==result["id"] for m in history["messages"]))
        _,other=manager.call("/assistant?factory_id=1")
        self.assertEqual(other["messages"],[])
        code,unsupported=engineer.call("/assistant/ask",{"factory_id":1,"question":"焊接不良率上升怎么办？","scenario":"solder"})
        self.assertEqual(code,200);self.assertIsNone(unsupported["response"]["analysis"])
        self.assertEqual(unsupported["response"]["factors"],[])
        self.assertIn("尚不能证明",unsupported["response"]["answer"])
        _,followup=engineer.call("/assistant/ask",{"factory_id":1,"question":"下一步怎么验证？"})
        self.assertEqual(followup["response"]["scenario"],"solder")
        self.assertIsNone(followup["response"]["analysis"])
        code,material=engineer.call("/assistant/ask",{"factory_id":1,"question":"原材料批次是原因吗？"})
        self.assertIn("不是已估计的处理因素",material["response"]["answer"])

    def test_15_dynamic_federation_pause_resume_events(self):
        for f in (1,2,3):self.admin.call("/federation/nodes/"+str(f),{"enabled":True})
        code,result=self.admin.call("/federation/start",{"rounds":4,"epochs":3,"pace":.3})
        self.assertEqual(code,200);id=result["id"]
        self.assertEqual(self.admin.call("/federation/pause",{"paused":True})[0],200)
        for _ in range(80):
            _,state=self.admin.call("/federation")
            job=next(j for j in state["jobs"] if j["id"]==id)
            if job["status"]=="已暂停":break
            time.sleep(.05)
        self.assertEqual(job["status"],"已暂停");at=job["round"];time.sleep(.35)
        _,state=self.admin.call("/federation")
        self.assertEqual(next(j for j in state["jobs"] if j["id"]==id)["round"],at)
        self.assertEqual(self.admin.call("/federation/pause",{"paused":False})[0],200)
        for _ in range(100):
            _,state=self.admin.call("/federation");job=next(j for j in state["jobs"] if j["id"]==id)
            if job["status"]=="已完成":break
            time.sleep(.05)
        self.assertEqual(job["status"],"已完成")
        self.assertTrue(all("accuracy" in h and len(h["nodes"])==3 for h in job["history"]))
        phases={e["phase"] for e in state["events"]}
        self.assertTrue({"upload","aggregate","paused","resume","deploy"}.issubset(phases))
        _,scoped=Client(self.base,"factory_b").call("/federation")
        self.assertTrue(all(n["factory_id"]==2 for h in scoped["jobs"][0]["history"] for n in h.get("nodes",[])))
        self.assertEqual(Client(self.base,"operator").call("/federation/pause",{"paused":True})[0],403)

    def test_16_logout_invalidates_session_and_private_media(self):
        client=Client(self.base,"engineer")
        self.assertEqual(client.call("/logout",{})[0],200)
        self.assertEqual(client.call("/me")[0],401)
        self.assertEqual(client.call("/assistant?factory_id=1")[0],401)
        with self.assertRaises(urllib.error.HTTPError) as error:
            client.opener.open(self.base+"/api/media/factory.mp4")
        self.assertEqual(error.exception.code,401)

    def test_17_live_control_access_and_factory_isolation(self):
        self.assertEqual(self.op.call('/live/demo',{'factory_id':1,'action':'start'})[0],403)
        self.assertEqual(self.eng.call('/live/demo',{'factory_id':2,'action':'start'})[0],403)
        self.assertEqual(self.other.call('/live?factory_id=1')[0],403)
        self.assertEqual(self.eng.call('/live/demo',{'factory_id':1,'action':'invalid'})[0],400)
        code,run=self.eng.call('/live/demo',{'factory_id':1,'action':'start'});self.assertEqual(code,200)
        self.assertNotIn('user_id',run)
        self.assertEqual(run['phase'],'warming')
        self.assertEqual(self.eng.call('/orders/'+str(run['order_id']),{'action':'report','quantity':1})[0],409)
        self.assertEqual(self.eng.call('/devices/'+str(run['device_id'])+'/reading',{'temperature':72,'pressure':5,'vibration':.7})[0],409)
        self.assertEqual(self.eng.call('/live/demo',{'factory_id':1,'action':'resume'})[0],409)
        _,overview=self.eng.call('/overview?factory_id=1')
        self.assertEqual(overview['kpi']['running'],sum(d['fresh'] and d['status']=='运行' for d in overview['devices']))
        self.assertEqual(self.eng.call('/live/demo',{'factory_id':1,'action':'stop'})[0],200)
        _,snapshot=self.eng.call('/live?factory_id=1');self.assertFalse(snapshot['demo']['running'])
        self.assertTrue(snapshot['device']['simulated'])
        self.assertEqual(self.other.call('/live?factory_id=2&device_id='+str(run['device_id']))[0],403)

    def test_18_defense_preparation_and_equipment_review_are_traceable(self):
        prepare={'factory_id':1,'action':'prepare-defense'}
        self.assertEqual(self.op.call('/live/demo',prepare)[0],403)
        self.assertEqual(self.other.call('/live/demo',prepare)[0],403)
        manager=Client(self.base,'manager')
        self.assertEqual(manager.call('/live/demo',prepare)[0],403)
        code,run=self.eng.call('/live/demo',prepare)
        self.assertEqual(code,200,run)
        self.assertEqual(run['mode'],'defense')
        self.assertEqual(run['device_id'],3)
        self.assertEqual(run['staffing']['operator_id'],3)
        self.assertEqual(self.eng.call('/live/demo',prepare)[1]['id'],run['id'])
        self.assertEqual(self.eng.call('/live?factory_id=1')[1]['demo']['id'],run['id'])
        timeline='/live/timeline?factory_id=1&run_id='+str(run['id'])
        self.assertEqual(self.op.call(timeline)[0],403)
        self.assertEqual(self.other.call(timeline)[0],403)
        self.assertEqual(self.other.call(timeline.replace('factory_id=1','factory_id=2'))[0],404)
        self.assertEqual(self.eng.call(timeline)[1]['interlocks'],[])
        self.assertEqual(manager.call('/live/demo',{'factory_id':1,'action':'fault'})[0],403)
        self.assertEqual(self.eng.call('/live/demo',{'factory_id':1,'action':'fault'})[0],200)
        incident=self.eng.call(timeline)[1]['interlocks'][0]
        self.assertEqual(incident['shutdown']['output_count'],0)
        self.assertIsNone(incident['resume_at'])
        anomaly_id=incident['anomaly']['id']
        _,candidates=self.eng.call('/workforce/candidates?anomaly_id='+str(anomaly_id))
        self.assertTrue(next(c for c in candidates['candidates'] if c['id']==3)['recommended'])
        code,task=self.eng.call('/tasks',{'anomaly_id':anomaly_id,'assignee':3,'action':'现场核对模拟温控回路'})
        self.assertEqual(code,200,task)
        task_path='/tasks/'+str(task['id'])
        self.assertEqual(self.op.call(task_path,{'action':'accept','version':1})[0],200)
        self.assertEqual(self.op.call(task_path,{'action':'submit','version':2,'note':'模拟温控回路已核对'})[0],200)
        self.assertEqual(self.eng.call(task_path,{'action':'review','version':3,'note':'设备点检通过','inspection_pass':True})[0],200)
        record=self.eng.call(timeline)[1]['interlocks'][0]
        self.assertEqual(record['task']['id'],task['id'])
        self.assertEqual(record['anomaly']['status'],'已关闭')
        self.assertEqual(record['inspection']['status'],'passed')
        self.assertEqual(record['restart']['quality_records'],[])
        self.assertEqual(self.eng.call('/live/demo',prepare)[1]['id'],run['id'])
        self.assertEqual(self.eng.call('/live/demo',{'factory_id':1,'action':'stop'})[0],200)
        code,rehearsal=self.eng.call('/live/demo',prepare)
        self.assertEqual(code,200,rehearsal)
        self.assertNotEqual(rehearsal['id'],run['id'])
        self.assertNotEqual(rehearsal['order_id'],run['order_id'])
        self.assertNotEqual(rehearsal['material_id'],run['material_id'])
        self.assertEqual(rehearsal['device_id'],3)
        self.assertEqual(self.eng.call(timeline)[1]['interlocks'][0]['anomaly']['id'],anomaly_id)
        self.assertEqual(self.eng.call('/live/demo',{'factory_id':1,'action':'stop'})[0],200)
        self.assertEqual(self.eng.call('/devices/3/reading',{'temperature':74,'pressure':5,'vibration':.7})[0],200)
        _,snapshot=self.eng.call('/live?factory_id=1&device_id=3')
        self.assertEqual(snapshot['source'],'最近采集记录')
        self.assertEqual(snapshot['readings'][-1]['temperature'],74)

    def test_19_standard_demo_can_resume_after_opt_in_defense(self):
        def action(name):
            return self.eng.call('/live/demo',{'factory_id':1,'action':name})
        code,regular=action('start')
        self.assertEqual(code,200,regular)
        self.assertEqual(action('prepare-defense')[0],409)
        self.assertEqual(action('stop')[0],200)
        code,defense=action('prepare-defense')
        self.assertEqual(code,200,defense)
        self.assertNotEqual(defense['id'],regular['id'])
        self.assertEqual(action('stop')[0],200)
        code,resumed=action('start')
        self.assertEqual(code,200,resumed)
        self.assertEqual(resumed['id'],regular['id'])
        self.assertEqual(resumed['order_id'],regular['order_id'])
        self.assertEqual(action('stop')[0],200)
        self.assertEqual(self.eng.call('/live?factory_id=1')[1]['demo']['id'],regular['id'])

if __name__=="__main__":unittest.main(verbosity=2)
