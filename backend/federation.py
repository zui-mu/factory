"""HTTP FedAvg coordinator with isolated worker processes and persisted jobs."""
import os,sys,json,time,threading,subprocess,socket,secrets,urllib.request,urllib.error
from concurrent.futures import ThreadPoolExecutor,as_completed
from .db import DATA,ROOT,connect,rows,one,FACTORIES,now
from .ml import aggregate

class Federation:
    def __init__(self):
        self.token=secrets.token_urlsafe(32);self.nodes={};self.lock=threading.Lock();self.stop_event=threading.Event();self.pause_event=threading.Event()
        self.thread=None
        with connect() as c:
            c.execute("UPDATE training_jobs SET status='中断',error='服务重启，请重新发起训练',updated_at=? WHERE status IN ('训练中','准备中','已暂停','暂停中')",(now(),))
        try:
            for factory,_,_ in FACTORIES:
                with connect() as c:enabled=one(c,"SELECT enabled FROM node_status WHERE factory_id=?",(factory,))["enabled"]
                if enabled:self.start_node(factory)
        except Exception:self.close();raise
    def start_node(self,factory):
        old=self.nodes.get(factory)
        if old and old["process"].poll() is None:return
        with socket.socket() as s:s.bind(("127.0.0.1",0));port=s.getsockname()[1]
        env=os.environ.copy();env["ZY_NODE_TOKEN"]=self.token;env["PYTHONUTF8"]="1"
        log=(DATA/"nodes"/("factory_%s.log"%factory)).open("ab")
        process=subprocess.Popen([sys.executable,"-B","-m","backend.node","--factory",str(factory),"--port",str(port)],
         cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        self.nodes[factory]={"process":process,"port":port,"log":log}
        for _ in range(40):
            try:self.call(factory,"health",{});return
            except Exception:time.sleep(.05)
        raise RuntimeError("工厂节点启动失败，请检查节点日志")
    def stop_node(self,factory):
        node=self.nodes.pop(factory,None)
        if node:
            node["process"].terminate()
            try:node["process"].wait(timeout=5)
            except subprocess.TimeoutExpired:node["process"].kill();node["process"].wait()
            node["log"].close()
    def call(self,factory,path,body):
        node=self.nodes.get(factory)
        if not node or node["process"].poll() is not None:raise RuntimeError("节点离线")
        req=urllib.request.Request("http://127.0.0.1:%s/%s"%(node["port"],path),data=json.dumps(body).encode(),headers={"Content-Type":"application/json","X-Node-Token":self.token},method="POST")
        with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
    def status(self):
        out=[]
        for f,name,city in FACTORIES:
            node=self.nodes.get(f)
            online=bool(node and node["process"].poll() is None)
            out.append({"id":f,"name":name,"city":city,"online":online,"train_n":[900,450,180][f-1],"validation_n":240,"test_n":400})
        return out
    def start(self,rounds=10,epochs=8,pace=0):
        if not self.lock.acquire(blocking=False):raise ValueError("已有训练任务正在运行")
        try:
            if sum(n["online"] for n in self.status())<2:raise ValueError("至少需要两个在线节点")
            job="FL-"+secrets.token_hex(4).upper();self.stop_event.clear();self.pause_event.clear()
            with connect() as c:c.execute("INSERT INTO training_jobs(id,status,total_rounds,config,created_at,updated_at) VALUES(?,?,?,?,?,?)",
             (job,"准备中",rounds,json.dumps({"epochs":epochs,"threshold":.35,"pace":pace,"algorithm":"FedAvg / Logistic Regression","source":"三个独立进程中的合成工厂数据"}),now(),now()))
            self.thread=threading.Thread(target=self.run,args=(job,rounds,epochs,pace),daemon=True);self.thread.start();return job
        except Exception:self.lock.release();raise
    def persist(self,job,**values):
        values["updated_at"]=now()
        for k in ("history","result"):
            if k in values:values[k]=json.dumps(values[k],ensure_ascii=False)
        with connect() as c:c.execute("UPDATE training_jobs SET "+",".join(k+"=?" for k in values)+" WHERE id=?",tuple(values.values())+(job,))
    def event(self,job,phase,detail,number=0,factory=None):
        with connect() as c:c.execute("INSERT INTO training_events(job_id,round,factory_id,phase,detail,created_at) VALUES(?,?,?,?,?,?)",(job,number,factory,phase,detail,now()))
    def pause(self,paused):
        if not self.lock.locked():raise ValueError("没有正在运行的训练任务")
        if paused:self.pause_event.set()
        else:self.pause_event.clear()
    def checkpoint(self,job):
        if self.pause_event.is_set() and not self.stop_event.is_set():
            self.persist(job,status="已暂停");self.event(job,"paused","训练已在轮次边界暂停")
            while self.pause_event.is_set() and not self.stop_event.wait(.1):pass
            if not self.stop_event.is_set():self.persist(job,status="训练中");self.event(job,"resume","继续训练")
        return not self.stop_event.is_set()
    def run(self,job,total,epochs,pace=0):
        history=[];w=[0.0]*6;baseline={};transferred=0;dropped=[]
        try:
            participants=[n["id"] for n in self.status() if n["online"]]
            self.event(job,"start","参与节点："+", ".join(str(f) for f in participants))
            for f in participants:
                baseline[f]=self.call(f,"baseline",{"epochs":total*epochs})
                self.event(job,"baseline","本厂独立训练基线计算完成",factory=f)
            self.persist(job,status="训练中")
            for number in range(1,total+1):
                if not self.checkpoint(job):self.persist(job,status="已取消",history=history);self.event(job,"cancel","任务已取消");return
                self.event(job,"distribute","向在线节点发送当前模型参数",number)
                updates=[];errors=[]
                with ThreadPoolExecutor(max_workers=3) as pool:
                    futures={pool.submit(self.call,f,"train",{"weights":w,"epochs":epochs}):f for f in participants}
                    for future in as_completed(futures):
                        f=futures[future]
                        try:
                            update=future.result();updates.append(update)
                            self.event(job,"upload","本地训练完成，收到 %s 条样本对应的参数更新"%update["n"],number,f)
                        except Exception:
                            errors.append(f);self.event(job,"offline","节点不可达，本轮未参与",number,f)
                if len(updates)<2:raise RuntimeError("有效节点不足两个；已保留历史记录，未部署新模型")
                w=aggregate(updates);transferred+=len(json.dumps(updates).encode())+len(json.dumps(w).encode())*len(updates)
                vals=[self.call(u["factory_id"],"evaluate",{"weights":w}) for u in updates]
                val_n=sum(v["validation"]["n"] for v in vals)
                history.append({"round":number,"participants":[u["factory_id"] for u in updates],"offline":errors,
                 "loss":sum(v["validation"]["loss"]*v["validation"]["n"] for v in vals)/val_n,
                 "f1":sum(v["validation"]["f1"]*v["validation"]["n"] for v in vals)/val_n,
                 "accuracy":sum(v["validation"]["accuracy"]*v["validation"]["n"] for v in vals)/val_n,
                 "nodes":[{"factory_id":v["factory_id"],"loss":v["validation"]["loss"],"f1":v["validation"]["f1"]} for v in vals],
                 "bytes":transferred})
                dropped=sorted(set(dropped+errors));self.persist(job,round=number,history=history)
                self.event(job,"aggregate","第 %s 轮聚合完成；验证损失 %.4f，F1 %.1f%%"%(number,history[-1]["loss"],history[-1]["f1"]*100),number)
                if pace:self.stop_event.wait(pace)
            if not self.checkpoint(job):self.persist(job,status="已取消");self.event(job,"cancel","任务已取消");return
            results=[]
            for f in participants:
                try:
                    evaluated=self.call(f,"evaluate",{"weights":w})
                    deployed=self.call(f,"deploy",{"weights":w,"version":job})
                    self.event(job,"deploy","验证通过，启用联合模型" if deployed["accepted"] else "验证未通过，保留本厂模型",total,f)
                    results.append({"factory_id":f,"name":FACTORIES[f-1][1],"local":baseline[f]["test"],"federated":evaluated["test"],"deployment":deployed})
                except Exception:dropped=sorted(set(dropped+[f]))
            self.persist(job,status="已完成",result={"factories":results,"weights":w,"bytes":transferred,"offline_nodes":dropped,
             "method":"相同训练轮数预算；训练、验证、测试数据独立生成。启用判断只使用验证集。","privacy":"原始样本由节点保管，HTTP 交换模型参数和汇总指标。当前为本机多进程模拟，未实现差分隐私或安全聚合。"})
            self.event(job,"complete","训练完成，已保存各厂效果与模型版本",total)
        except Exception as e:self.persist(job,status="失败",error=str(e),history=history);self.event(job,"error",str(e))
        finally:self.lock.release()
    def close(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():self.thread.join(timeout=25)
        for f in list(self.nodes):self.stop_node(f)
