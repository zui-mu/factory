"""Capture reproducible demo evidence from a running local instance."""
import sys,json,time,argparse,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.db import DATA

def main():
    p=argparse.ArgumentParser(description="运行演示分析和一次联合训练，保存实际计算结果")
    p.add_argument("--url",default="http://127.0.0.1:8765")
    p.add_argument("--username",default="admin");p.add_argument("--password",default="Zyyl@2026")
    args=p.parse_args();csrf=""
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(path,body=None):
        req=urllib.request.Request(args.url+"/api"+path,data=json.dumps(body).encode() if body is not None else None,
         headers={"Content-Type":"application/json","X-CSRF-Token":csrf})
        with opener.open(req,timeout=30) as response:return json.load(response)
    user=call("/login",{"username":args.username,"password":args.password});csrf=user["csrf"]
    analysis=call("/analyze",{"anomaly_id":1})
    for factory in (1,2,3):call("/federation/nodes/"+str(factory),{"enabled":True})
    training=call("/federation/start",{"rounds":10,"epochs":8})
    for _ in range(300):
        state=call("/federation");job=next(j for j in state["jobs"] if j["id"]==training["id"])
        if job["status"] not in ("训练中","准备中"):break
        time.sleep(.2)
    if job["status"]!="已完成":raise RuntimeError("训练未完成："+job["status"])
    result={"environment":"本机模拟工厂数据；实际算法计算，不代表生产收益","analysis":analysis,"training":job,
     "sources":call("/sources"),"prediction":call("/federation/predict",{"factory_id":1,"temp":1,"pressure":0,"wear":0,"material":0,"product":0})}
    (DATA/"reports").mkdir(parents=True,exist_ok=True)
    (DATA/"reports"/"evaluation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    call("/logout",{})
    print(json.dumps({"status":job["status"],"rounds":job["round"],"factories":len(job["result"]["factories"]),
     "loss_start":job["history"][0]["loss"],"loss_end":job["history"][-1]["loss"],
     "effects":{f["name"]:round(f["effect"],4) for f in analysis["result"]["factors"]}},ensure_ascii=False))
if __name__=="__main__":main()
