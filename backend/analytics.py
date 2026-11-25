"""Stratified standardization under an explicit fixed causal hypothesis."""
import math
from .db import rows,now
FACTORS=[("temp","温度偏高","核对温控与传感器，在工艺许可范围内恢复标准温度"),("pressure","压力偏高","检查压力控制与设备设定，按工艺文件恢复标准压力"),("wear","设备磨损","安排点检，确认磨损情况后进行维护")]
def analyze(c,factory,source="已知生成机制的模拟工艺样本"):
    data=rows(c,"SELECT temp,pressure,wear,material,product,defect,source FROM samples WHERE factory_id=? AND source=?",(factory,source))
    n=len(data);out=[]
    for key,label,action in FACTORS:
        groups={}
        for s in data: groups.setdefault((s["material"],s["product"]),[[],[]])[s[key]].append(s["defect"])
        rd=0;var=0;covered=0;parts=[]
        for strata,(control,treated) in groups.items():
            if min(len(control),len(treated))<8:continue
            weight=(len(control)+len(treated))/max(n,1)
            p0=sum(control)/len(control);p1=sum(treated)/len(treated)
            rd+=weight*(p1-p0);var+=weight**2*(p1*(1-p1)/len(treated)+p0*(1-p0)/len(control))
            covered+=len(control)+len(treated)
            parts.append({"material":strata[0],"product":strata[1],"normal":len(control),"exposed":len(treated),"normal_rate":p0,"exposed_rate":p1})
        coverage=covered/max(n,1);sufficient=n>=100 and coverage>=.9
        if coverage:rd/=coverage;var/=coverage**2
        se=math.sqrt(var);lo=max(-1,rd-1.96*se);hi=min(1,rd+1.96*se)
        a=[s["defect"] for s in data if s[key]];b=[s["defect"] for s in data if not s[key]]
        raw=sum(a)/max(len(a),1)-sum(b)/max(len(b),1)
        out.append({"key":key,"name":label,"effect":rd,"raw_effect":raw,"ci":[lo,hi],"coverage":coverage,"sufficient":sufficient,
          "supported":sufficient and lo>0,"action":action,"strata":parts,"exposed_n":len(a),"normal_n":len(b)})
    out.sort(key=lambda x:x["effect"],reverse=True)
    return {"sample_count":n,"defect_rate":sum(s["defect"] for s in data)/max(n,1),"factors":out,
     "method":"按原料等级与产品规格分层的标准化风险差","outcome":"质检不合格（0/1）","treatment":"工艺状态由正常变为偏高／磨损",
     "adjustment":["原料等级","产品规格"],"sources":sorted(set(s["source"] for s in data)),
     "assumptions":["原料等级与产品规格足以控制本模型中的共同原因","每个主要分层同时存在正常和暴露样本","样本独立且字段含义一致；没有遗漏的重要混杂因素"],
     "limitations":"这是给定因果假设下的平均风险差估计，不是自动发现根因，也不是单个批次的效果保证。模拟数据可验证方法流程，真实数据需工艺专家审查假设。",
     "created_at":now(),"graph":{"nodes":["原料等级","产品规格","温度","压力","磨损","质量结果"],"edges":[[0,2],[0,5],[1,2],[1,3],[1,5],[2,5],[3,5],[4,5]]}}
