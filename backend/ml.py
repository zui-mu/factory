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
