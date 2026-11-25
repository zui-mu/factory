"""Reproduce the bundled demonstration model. Python 3.9+, no third-party packages."""
import json, random
from pathlib import Path
"""Dependency-free logistic regression and reproducible metrics."""
import math
FEATURES=["温度偏高","压力偏高","设备磨损","原料等级","产品规格"]
def sigmoid(z):return 1/(1+math.exp(-max(-35,min(35,z))))
def predict(w,x):return sigmoid(w[0]+sum(a*b for a,b in zip(w[1:],x)))
def train(data,w=None,epochs=5,rate=.65):
    w=list(w or [0.0]*6);n=len(data)
    if not n:raise ValueError("节点没有训练样本")
    for _ in range(epochs):
        grad=[0.0]*6
        for x,y in data:
            e=predict(w,x)-y;grad[0]+=e
            for j in range(5):grad[j+1]+=e*x[j]
        for j in range(6):w[j]-=rate*(grad[j]/n+(.002*w[j] if j else 0))
    return w
def metrics(data,w):
    scored=[(predict(w,x),y) for x,y in data]
    tp=sum(p>=.35 and y==1 for p,y in scored);fp=sum(p>=.35 and y==0 for p,y in scored)
    fn=sum(p<.35 and y==1 for p,y in scored);tn=len(scored)-tp-fp-fn
    precision=tp/max(tp+fp,1);recall=tp/max(tp+fn,1)
    # Average precision over distinct thresholds; ties must not favor positives.
    groups={}
    for p,y in scored:
        count,positive=groups.get(p,(0,0));groups[p]=(count+1,positive+y)
    hit=0;seen=0;ap=0
    for p in sorted(groups,reverse=True):
        count,positive=groups[p];seen+=count;hit+=positive;ap+=positive*hit/seen
    loss=-sum(y*math.log(max(p,1e-12))+(1-y)*math.log(max(1-p,1e-12)) for p,y in scored)/max(len(scored),1)
    return {"n":len(data),"accuracy":(tp+tn)/max(len(data),1),"precision":precision,"recall":recall,"f1":2*precision*recall/max(precision+recall,1e-12),
      "average_precision":ap/max(hit,1),"false_positive_rate":fp/max(fp+tn,1),"loss":loss,"threshold":.35,"tp":tp,"fp":fp,"fn":fn,"tn":tn}
def aggregate(updates):
    total=sum(u["n"] for u in updates)
    if total<=0:raise ValueError("没有有效节点更新")
    for u in updates:
        if len(u["weights"])!=6 or not all(math.isfinite(v) and abs(v)<100 for v in u["weights"]):raise ValueError("模型参数不合法")
    return [sum(u["weights"][j]*u["n"] for u in updates)/total for j in range(6)]

def observations(seed,n,shift=0):
    r=random.Random(seed); result=[]
    for i in range(n):
        material=int(r.random()<(.25+shift*.10))
        product=int(r.random()<(.35+shift*.12))
        temp=int(r.random()<(.12+.46*material+.10*product))
        pressure=int(r.random()<(.17+.19*product))
        wear=int(r.random()<(.14+.13*shift))
        logit=-3.35+1.65*temp+1.12*pressure+1.03*wear+.85*material+.45*product
        defect=int(r.random()<1/(1+math.exp(-logit)))
        result.append((temp,pressure,wear,material,product,defect))
    return result
def main():
    counts=[900,450,180]
    datasets=[[(list(row[:5]),row[5]) for row in observations(701+f,counts[f],f)] for f in range(3)]
    validation=[[(list(row[:5]),row[5]) for row in observations(901+f,240,f)] for f in range(3)]
    tests=[[(list(row[:5]),row[5]) for row in observations(1101+f,400,f)] for f in range(3)]
    local=[train(data,epochs=80) for data in datasets]
    weights=[0.0]*6
    for _ in range(10):
        weights=aggregate([{"weights":train(data,weights,epochs=8),"n":len(data)} for data in datasets])
    nodes=[]
    for f in range(3):
        previous=metrics(validation[f],local[f]);candidate=metrics(validation[f],weights)
        lm=metrics(tests[f],local[f]);fm=metrics(tests[f],weights)
        nodes.append({"id":f+1,"localWeights":local[f],"localF1":lm["f1"],"trainCount":counts[f],
                      "validationCount":240,"testCount":400,"federatedF1":fm["f1"],"recall":fm["recall"],
                      "falsePositiveRate":fm["false_positive_rate"],
                      "accepted":candidate["f1"]>=previous["f1"] and candidate["loss"]<=previous["loss"]+.02})
    artifact={"version":"DEMO-FED-10","rounds":10,"threshold":.35,"weights":weights,"nodes":nodes,
              "source":"三个工厂独立生成的模拟工艺样本，固定种子，FedAvg逻辑回归；非真实生产模型。"}
    path=Path(__file__).resolve().parents[1]/'Assets/FactoryTwin/Resources/DemoModels.json'
    old=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    path.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Model reproduced; matches existing artifact:',old==artifact)
    print(path)

if __name__=='__main__':main()
