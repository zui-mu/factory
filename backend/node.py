"""A real local HTTP worker. The coordinator never requests raw sample rows."""
import argparse,json,os,secrets,math
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from .db import connect,now
from .ml import train,metrics,predict

def serve(factory,port):
    token=os.environ["ZY_NODE_TOKEN"]
    def dataset(split):
        with connect(factory=factory) as c:
            return [(list(r[:5]),r[5]) for r in c.execute("SELECT temp,pressure,wear,material,product,defect FROM samples WHERE split=?",(split,))]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,value,status=200):
            b=json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
        def do_POST(self):
            if not secrets.compare_digest(self.headers.get("X-Node-Token",""),token):return self.send({"error":"unauthorized"},401)
            try:
                size=int(self.headers.get("Content-Length",0))
                if size>16384:raise ValueError("payload too large")
                body=json.loads(self.rfile.read(size))
                if self.path=="/health":
                    return self.send({"factory_id":factory,"train_n":len(dataset("train")),"validation_n":len(dataset("validation")),"test_n":len(dataset("test"))})
                if self.path=="/baseline":
                    epochs=int(body.get("epochs",80))
                    if not 1<=epochs<=500:raise ValueError("invalid epochs")
                    w=train(dataset("train"),epochs=epochs)
                    with connect(factory=factory) as c:c.execute("REPLACE INTO state VALUES('baseline',?)",(json.dumps(w),))
                    return self.send({"test":metrics(dataset("test"),w),"validation":metrics(dataset("validation"),w)})
                if self.path=="/predict":
                    x=body["features"]
                    if len(x)!=5 or any(v not in (0,1) for v in x):raise ValueError("invalid features")
                    with connect(factory=factory) as c:
                        active=c.execute("SELECT value FROM state WHERE `key`='active'").fetchone()
                        baseline=c.execute("SELECT value FROM state WHERE `key`='baseline'").fetchone()
                    if not active and not baseline:raise ValueError("train first")
                    model=json.loads(active[0]) if active else {"weights":json.loads(baseline[0]),"version":"本厂基线"}
                    risk=predict(model["weights"],x)
                    return self.send({"risk":risk,"threshold":.35,"version":model["version"],"flagged":risk>=.35,
                     "source":"本地节点模拟数据训练模型","message":"结果用于流程演示与人工核对，未经真实生产样本校准，不自动控制设备。"})
                w=body["weights"]
                if len(w)!=6 or not all(isinstance(v,(float,int)) and math.isfinite(v) and abs(v)<100 for v in w):raise ValueError("invalid weights")
                if self.path=="/train":
                    epochs=int(body.get("epochs",8))
                    if not 1<=epochs<=30:raise ValueError("invalid epochs")
                    data=dataset("train");local=train(data,w,epochs)
                    return self.send({"factory_id":factory,"weights":local,"n":len(data),"train_loss":metrics(data,local)["loss"]})
                if self.path=="/evaluate":
                    return self.send({"factory_id":factory,"validation":metrics(dataset("validation"),w),"test":metrics(dataset("test"),w)})
                if self.path=="/deploy":
                    with connect(factory=factory) as c:
                        existing=c.execute("SELECT value FROM state WHERE `key`='active'").fetchone()
                        baseline=c.execute("SELECT value FROM state WHERE `key`='baseline'").fetchone()
                        old=json.loads(existing[0])["weights"] if existing else json.loads(baseline[0])
                        old_metric=metrics(dataset("validation"),old)
                        new_metric=metrics(dataset("validation"),w)
                        accepted=new_metric["f1"]>=old_metric["f1"] and new_metric["loss"]<=old_metric["loss"]+.02
                        if accepted:
                            c.execute("REPLACE INTO state VALUES('active',?)",(json.dumps({"weights":w,"version":body["version"],"updated_at":now()}),))
                        return self.send({"accepted":accepted,"previous_f1":old_metric["f1"],"candidate_f1":new_metric["f1"],
                          "active_version":body["version"] if accepted else json.loads(existing[0])["version"] if existing else "本厂基线"})
                self.send({"error":"unknown endpoint"},404)
            except (ValueError,KeyError,TypeError) as e:self.send({"error":str(e)},400)
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler);server.serve_forever()

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--factory",type=int,required=True);p.add_argument("--port",type=int,required=True)
    a=p.parse_args();serve(a.factory,a.port)
