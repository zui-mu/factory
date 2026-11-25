"""Evidence-grounded causal conversation; optional explicitly selected model provider."""
import json,os,urllib.request,urllib.parse
from .analytics import analyze
from .db import now,rows,one

PRESETS=[
 ("quality","质量缺陷升高","这次质量缺陷升高，应该先排查什么？"),
 ("solder","焊接不良率升高","焊接不良率升高，应该补充哪些数据并如何排查？"),
 ("assembly","组装缺陷增加","组装缺陷增加，怎样定位工位与工艺因素？"),
 ("material","原材料批次问题","如何判断原材料批次是否影响质量？"),
 ("action","处置与复检","下一步该怎么处理，怎样验证是否有效？")]

def provider_status():
    enabled=all(os.environ.get(k) for k in ("ZY_AI_URL","ZY_AI_MODEL"))
    return {"configured":enabled,"mode":"本地证据助手","model":os.environ.get("ZY_AI_MODEL","") if enabled else "",
     "description":"默认使用本厂统计证据生成建议；外部大模型仅在明确选择后调用。"}

def optional_model(question,evidence,history):
    url=os.environ.get("ZY_AI_URL","")
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" and not (parsed.scheme=="http" and parsed.hostname in ("localhost","127.0.0.1")):
        raise ValueError("模型地址须为 HTTPS 或本机服务")
    messages=[{"role":"system","content":"你是智慧工厂质量分析助手。只依据提供的统计证据回答，区分已知事实、推测和待补充数据。不得编造因果准确率、收益、具体危险设备参数或外部企业事实。不把总体效应说成当前批次已确认根因。不执行设备控制。使用简明中文。"}]
    for h in history[-3:]:
        messages.extend([{"role":"user","content":h["question"]},{"role":"assistant","content":h["answer"][:1600]}])
    messages.append({"role":"user","content":json.dumps({"question":question,"evidence":evidence},ensure_ascii=False)})
    body=json.dumps({"model":os.environ["ZY_AI_MODEL"],"messages":messages,"temperature":.2,"max_tokens":1000}).encode()
    headers={"Content-Type":"application/json"}
    if os.environ.get("ZY_AI_KEY"):headers["Authorization"]="Bearer "+os.environ["ZY_AI_KEY"]
    # Do not forward credentials across redirects.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    request=urllib.request.Request(url,data=body,headers=headers)
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=25) as response:
        data=json.loads(response.read(1000000))
    answer=data["choices"][0]["message"]["content"]
    if not isinstance(answer,str) or not answer.strip():raise ValueError("模型未返回有效内容")
    return answer[:8000]

def answer(c,user,factory,question,source,anomaly=None,scenario="quality",use_model=False):
    latest=rows(c,"SELECT question,response FROM assistant_messages WHERE user_id=? AND factory_id=? ORDER BY id DESC LIMIT 3",(user["id"],factory))
    history=[{"question":h["question"],"answer":json.loads(h["response"])["answer"]} for h in latest[::-1]]
    if latest and scenario=="quality" and any(w in question for w in ("继续","下一步","那怎么","这个判断","这个问题","再解释","刚才")):
        previous=json.loads(latest[0]["response"])
        if previous.get("source")==source and previous.get("anomaly_id")== (anomaly["id"] if anomaly else None):
            scenario=previous.get("scenario","quality")
    if any(w in question for w in ("焊接","焊点")):scenario="solder"
    elif any(w in question for w in ("组装","装配")):scenario="assembly"
    unknown_process=scenario in ("solder","assembly") or any(w in question for w in ("焊接","焊点","组装","装配"))
    maintenance=bool(anomaly and not anomaly["order_id"])
    unrelated=not any(w in question for w in ("质量","缺陷","温度","压力","磨损","原料","材料","工艺","批次","焊","组装","装配","处置","复检","原因","排查","判断","依据","置信","区间","确定","为什么","继续","下一步","怎么","设备","这个","刚才","建议","分析"))
    result=None;analysis=None
    if not unknown_process and not maintenance and not unrelated:
        result=analyze(c,factory,source)
        if anomaly and user["role"] in ("admin","engineer","manager"):
            result["context"]={"anomaly_id":anomaly["id"],"title":anomaly["title"],"batch_scope":"总体样本候选证据，当前批次需现场核对"}
            id=c.execute("INSERT INTO analyses(factory_id,anomaly_id,result,created_at) VALUES(?,?,?,?)",
             (factory,anomaly["id"],json.dumps(result,ensure_ascii=False),now())).lastrowid
            if anomaly["status"]=="待分析":c.execute("UPDATE anomalies SET status='待处置' WHERE id=?",(anomaly["id"],))
            analysis={"id":id,"factory_id":factory,"anomaly_id":anomaly["id"],"result":result}
    references=[];recommendations=[];factors=[]
    if unrelated:
        result=None;analysis=None;factors=[]
        text="我可以协助分析工厂质量、工艺和现场处置问题。请描述异常、相关批次和已有检查结果，或选择下方预设场景；当前问题不足以对应到一个可核验的生产问题。"
        recommendations=[{"title":"补充问题上下文","detail":"例如：某批次尺寸偏差升高，已观察到温度变化，希望确定先检查什么。"}]
    elif maintenance:
        text="当前选择的是设备点检事件，没有关联产品质量批次。\n建议先核对点检周期、传感器状态、润滑与维护记录，再由有资质人员按设备规程检查。该事件不能直接套用产品质量因果模型。"
        references=[{"label":"设备事件 #"+str(anomaly["id"]),"detail":anomaly["title"]}]
        recommendations=[{"title":"安排现场点检","detail":"记录发现、检查过程及照片，提交后由工程师复核设备状态。"}]
    elif unknown_process:
        text="当前平台的温度、压力、磨损样本尚不能证明焊接或组装场景的根因。\n可以先按批次、工位、设备与缺陷类型分组，确定异常集中范围，再检查工艺变更、材料批次和设备维护记录。收集与该工艺对应的样本后，重新审查因果假设。"
        recommendations=[{"title":"补充场景数据","detail":"焊接需工艺曲线、焊料批次与焊点缺陷；组装需工位、定位、扭矩记录和装配缺陷。不要直接复用其他工艺的效应值。"},
         {"title":"先核对再试验","detail":"由工艺人员制定授权范围内的对照检查，保持其他条件可比，再以独立复检样本验证。"}]
        references=[{"label":"模型适用范围","detail":"当前固定假设：温度、压力、磨损，调整原料等级与产品规格。"}]
    else:
        factors=result["factors"];supported=[f for f in factors if f["supported"]]
        text="已根据本厂「%s」的 %s 条样本计算，结论针对总体工艺样本。"%(source,result["sample_count"])
        if supported:
            best=supported[0]
            text+="\n建议优先核对%s：调整原料等级与产品规格后，风险差为 %+.2f 个百分点，95%% 区间 %.2f 至 %.2f 个百分点。"%(best["name"],best["effect"]*100,best["ci"][0]*100,best["ci"][1]*100)
            text+="\n这为排查顺序提供证据，但不能直接断言当前批次已确认这一根因。"
        else:text+="\n目前没有同时满足样本充分性与正向区间证据的因素，请先补充或核验数据，不据此直接修改工艺。"
        if any(w in question for w in ("原料","材料","批次")):
            text+="\n原料等级是当前模型的调整变量，不是已估计的处理因素；不能据此计算某供应商或某批次的因果效应。应补充批次、检验和领料关联记录。"
        if any(w in question for w in ("为什么","依据","置信","区间","确定")):
            text+="\n计算将样本按原料等级与产品规格分层，再比较正常与暴露组的缺陷率。结论依赖无遗漏混杂、样本可比且主要分层都有两组样本等假设。"
        recommendations=[{"title":f["name"]+"检查","detail":f["action"]+"；先确认当前批次存在该因素。"} for f in supported]
        recommendations.append({"title":"处置后独立复检","detail":"记录实际操作与照片，提交工程师复检；比较同类条件的质量记录，未通过则退回继续处理。"})
        references=[{"label":"样本来源","detail":source+" · "+str(result["sample_count"])+" 条"},
         {"label":"估计方法","detail":result["method"]},{"label":"适用条件","detail":result["limitations"]}]
        if analysis:references.append({"label":"分析记录 #"+str(analysis["id"]),"detail":"关联异常 #"+str(anomaly["id"])+" · "+anomaly["title"]})
    mode="本地证据助手";warning=""
    if use_model:
        if not provider_status()["configured"]:raise ValueError("尚未配置外部大模型")
        c.commit()
        # Only the current user's selected factory summary and conversation are shared.
        try:
            text=optional_model(question,{"summary":text,"references":references,"recommendations":recommendations},history)
            mode="外部大模型建议"
        except Exception:
            warning="外部模型暂不可用，以下为本地证据建议。未保存或显示服务密钥。"
    response={"answer":text,"mode":mode,"warning":warning,"references":references,"recommendations":recommendations,
     "analysis":analysis,"factors":factors,"source":source,"scenario":scenario,"anomaly_id":anomaly["id"] if anomaly else None,
     "limitations":"建议需人工核对后执行；不自动控制设备，不承诺当前批次的因果结论。"}
    id=c.execute("INSERT INTO assistant_messages(user_id,factory_id,question,response,created_at) VALUES(?,?,?,?,?)",
     (user["id"],factory,question,json.dumps(response,ensure_ascii=False),now())).lastrowid
    return {"id":id,"question":question,"response":response,"created_at":now()}
