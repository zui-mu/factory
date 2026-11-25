using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace Zhiyin.FactoryTwin
{
    // Reads the existing platform API. No database credentials or device-control commands are stored here.
    public class FactoryPlatformBridge : MonoBehaviour
    {
        public FactoryTwinApp app;
        public bool connected, riskReady;
        public float risk;
        public string userName, shiftTitle="等待班表", shiftNote="同步中", scheduleDetails="同步中";
        public string modelVersion="待同步", modelSummary="等待模型记录", modelDetails="暂无模型记录", qualityDetails="同步中";
        public readonly List<string> staff=new List<string>();
        public float[] factoryF1=new float[3];
        public string BaseUrl {get{return baseUrl;}}
        string baseUrl="http://127.0.0.1:8765", cookie, csrf;
        User user; int epoch; Coroutine polling;
        float syncedAt;bool authenticating,loggingOut;
        public bool CanFactory(int id){return user!=null&&(user.role=="admin"||user.factory_id==id);}
        [Serializable] class Credentials {public string username,password;}
        [Serializable] class User {public string name,role,csrf;public int factory_id;}
        [Serializable] class ErrorBody {public string error;}
        [Serializable] class Device {public int id;public string name,line,status,display_status;public float temperature,pressure,vibration;public bool fresh,archived;}
        [Serializable] class Devices {public Device[] items;}
        [Serializable] class Order {public int id,device_id,quantity,completed;public string batch,status;public bool archived;}
        [Serializable] class Orders {public Order[] items;}
        [Serializable] class Quality {public int order_id,sample_size,defects;public string batch,defect_type,created_at;}
        [Serializable] class Qualities {public Quality[] items;}
        [Serializable] class Employee {public int id;public string name,team;public string[] skills;}
        [Serializable] class Plan {public int id,required_count,available_count,shortage;public string line,start_at,end_at,phase,status,shift_name;public int[] employee_ids,leave_ids;}
        [Serializable] class Workforce {public Employee[] employees;public Plan[] plans;public int[] on_duty_ids;public bool personal;}
        [Serializable] class Metrics {public float f1,recall,false_positive_rate;}
        [Serializable] class Deployment {public bool accepted;public string active_version;}
        [Serializable] class FactoryResult {public int factory_id;public Metrics local,federated;public Deployment deployment;}
        [Serializable] class TrainingResult {public FactoryResult[] factories;}
        [Serializable] class Job {public string id,status;public TrainingResult result;}
        [Serializable] class Federation {public Job[] jobs;public string description,privacy;}
        [Serializable] class Prediction {public float risk,threshold;public string version,message;}
        [Serializable] class Features {public int factory_id,temp,pressure,wear,material,product;}

        IEnumerator Request(string path,string body,Action<string,string> done)
        {
            using(var request=new UnityWebRequest(baseUrl+path,body==null?"GET":"POST"))
            {
                request.downloadHandler=new DownloadHandlerBuffer(); request.timeout=8;
                if(body!=null){request.uploadHandler=new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));request.SetRequestHeader("Content-Type","application/json");}
                if(!string.IsNullOrEmpty(cookie))request.SetRequestHeader("Cookie",cookie);
                if(!string.IsNullOrEmpty(csrf))request.SetRequestHeader("X-CSRF-Token",csrf);
                yield return request.SendWebRequest();
                if(request.result!=UnityWebRequest.Result.Success)
                {
                    string error="无法连接平台，请检查服务器地址和运行状态";
                    try{var e=JsonUtility.FromJson<ErrorBody>(request.downloadHandler.text);if(!string.IsNullOrEmpty(e.error))error=e.error;}catch{}
                    done(null,error);yield break;
                }
                string setCookie=request.GetResponseHeader("Set-Cookie");
                if(path=="/api/login"&&!string.IsNullOrEmpty(setCookie))cookie=setCookie.Split(';')[0];
                done(request.downloadHandler.text,null);
            }
        }
        public IEnumerator Login(string url,string username,string password,Action<string> callback)
        {
            if(authenticating||loggingOut){callback("正在登录或退出，请稍后再试");yield break;}
            Uri uri;
            if(!Uri.TryCreate(url.Trim(),UriKind.Absolute,out uri)||(uri.Scheme!="http"&&uri.Scheme!="https")){callback("请输入完整的 http 或 https 平台地址");yield break;}
            if(connected){callback("请先退出当前平台连接");yield break;}
            authenticating=true;
            baseUrl=uri.GetLeftPart(UriPartial.Authority);cookie=null;csrf=null;
            string json=null,error=null;
            yield return Request("/api/login",JsonUtility.ToJson(new Credentials{username=username.Trim(),password=password}),(j,e)=>{json=j;error=e;});
            authenticating=false;
            if(error!=null){callback(error);yield break;}
            try{user=JsonUtility.FromJson<User>(json);}catch{callback("平台登录响应格式不正确");yield break;}
            if(user==null||string.IsNullOrEmpty(user.csrf)||string.IsNullOrEmpty(cookie)){callback("平台未返回有效会话");yield break;}
            csrf=user.csrf;userName=user.name;connected=true;
            int factory=user.role=="admin"?app.simulation.factory:user.factory_id;
            if(factory<1||factory>3){connected=false;callback("此账号没有可展示的工厂");yield break;}
            app.simulation.Reset(factory);app.Home();RefreshNow();callback(null);
        }
        void ClearReadings()
        {
            riskReady=false;staff.Clear();shiftTitle="等待班表";shiftNote="平台数据同步中";scheduleDetails="暂无当前班表";
            qualityDetails="等待本厂质检记录";modelVersion="待同步";modelSummary="等待本厂模型记录";modelDetails="暂无模型记录";factoryF1=new float[3];
            foreach(var line in app.simulation.lines){line.fresh=false;line.running=false;line.status="通信未知";line.batch="待同步";line.inspected=line.defects=line.completed=0;line.task="等待记录";}
        }
        public void RefreshNow()
        {
            epoch++;if(polling!=null)StopCoroutine(polling);ClearReadings();polling=StartCoroutine(Poll(epoch));
        }
        void Update()
        {
            if(connected&&Time.realtimeSinceStartup-syncedAt>15)
                foreach(var line in app.simulation.lines){line.fresh=false;line.running=false;}
        }
        IEnumerator Poll(int generation)
        {
            while(connected&&generation==epoch)
            {
                int factory=app.simulation.factory;
                string suffix="?factory_id="+factory;
                float readAt=Time.realtimeSinceStartup;
                string d=null,o=null,q=null,w=null,f=null,error=null;
                yield return Request("/api/devices"+suffix,null,(j,e)=>{d=j;error=e;});
                if(generation!=epoch)yield break;
                if(error!=null){app.simulation.Event(error);yield return new WaitForSecondsRealtime(3);continue;}
                yield return Request("/api/orders"+suffix,null,(j,e)=>o=j);
                yield return Request("/api/quality"+suffix,null,(j,e)=>q=j);
                yield return Request("/api/workforce"+suffix+"&date="+DateTime.Now.ToString("yyyy-MM-dd"),null,(j,e)=>w=j);
                yield return Request("/api/federation",null,(j,e)=>f=j);
                if(generation!=epoch||!connected)yield break;
                try{Apply(d,o,q,w,f);syncedAt=readAt;app.Refresh();}
                catch(Exception ex){app.simulation.Event("平台记录解析失败，请核对接口版本");Debug.LogWarning("Platform response: "+ex.GetType().Name);}
                yield return new WaitForSecondsRealtime(3);
            }
        }
        static T Array<T>(string json){return JsonUtility.FromJson<T>("{\"items\":"+(json??"[]")+"}");}
        void Apply(string devices,string orders,string quality,string workforce,string federation)
        {
            var ds=Array<Devices>(devices).items;var os=Array<Orders>(orders).items;var qs=Array<Qualities>(quality).items;
            foreach(var line in app.simulation.lines)
            {
                Device dev=System.Array.Find(ds,x=>x.id==line.deviceId&&!x.archived);
                line.fresh=dev!=null&&dev.fresh;line.running=line.fresh&&dev.status=="运行";line.faulty=dev!=null&&dev.status=="参数预警";
                if(dev!=null){line.temperature=dev.temperature;line.pressure=dev.pressure;line.vibration=dev.vibration;line.equipment=dev.name;line.name=dev.line;line.status=dev.display_status??dev.status;}
                Order order=System.Array.Find(os,x=>x.device_id==line.deviceId&&!x.archived&&x.status!="已完成");
                if(order==null)order=System.Array.Find(os,x=>x.device_id==line.deviceId&&!x.archived);
                line.batch=order==null?"无关联工单":order.batch;line.completed=order==null?0:order.completed;line.planned=order==null?0:order.quantity;
                line.inspected=0;line.defects=0;line.task="以平台任务为准";
                if(order!=null)foreach(var item in qs)if(item.order_id==order.id){line.inspected+=item.sample_size;line.defects+=item.defects;}
            }
            var selected=app.simulation.lines[app.selectedLine];
            qualityDetails=quality==null?"质检接口暂不可用。": "平台批次级质检记录：\n";
            foreach(var item in qs)if(item.batch==selected.batch)qualityDetails+=item.created_at+" · "+item.defect_type+" · "+item.defects+" / "+item.sample_size+" 件\n";
            if(qualityDetails.Length<25)qualityDetails+="当前批次暂无质检记录。";
            staff.Clear();scheduleDetails="暂无可见班表";shiftTitle="无当前班表";shiftNote="以已发布班表为准；不代表实际签到";
            if(workforce!=null)
            {
                var work=JsonUtility.FromJson<Workforce>(workforce);Plan current=null;var detail=new StringBuilder();
                foreach(var plan in work.plans)
                {
                    if(plan.line!=selected.name||plan.status!="已发布")continue;
                    if(plan.phase=="当班")current=plan;
                    if(detail.Length<700)detail.AppendLine(plan.shift_name+"  "+plan.start_at+" — "+plan.end_at+"  "+plan.phase+(work.personal?" / 本人安排":" / 缺 "+plan.shortage+" 人"));
                }
                scheduleDetails=detail.Length>0?detail.ToString():"所选产线暂无可见班表。";
                if(current!=null)
                {
                    shiftTitle=current.shift_name+" · 当班";shiftNote=selected.name+" · 需求 "+current.required_count+" / 可用 "+current.available_count+"\n"+(current.shortage>0?"缺岗 "+current.shortage+" 人":"按班表已满足人数");
                    if(work.personal)shiftNote=selected.name+" · 仅显示本人班表\n全班人员覆盖情况由负责人核对";
                    foreach(int id in current.employee_ids)
                    {
                        if(System.Array.IndexOf(current.leave_ids??new int[0],id)>=0)continue;
                        var person=System.Array.Find(work.employees,x=>x.id==id);if(person!=null)staff.Add(person.name+" · "+string.Join(" / ",person.skills??new string[0]));
                    }
                }
            }
            if(federation!=null)
            {
                var fed=JsonUtility.FromJson<Federation>(federation);modelDetails=fed.description+"\n\n"+fed.privacy;modelSummary="暂无已完成训练";modelVersion="待训练";
                foreach(var job in fed.jobs??new Job[0])
                {
                    if(job.status!="已完成"||job.result==null||job.result.factories==null)continue;
                    foreach(var result in job.result.factories)
                    {
                        if(result.factory_id<1||result.factory_id>3||!CanFactory(result.factory_id))continue;
                        factoryF1[result.factory_id-1]=result.federated.f1;
                        if(result.factory_id!=app.simulation.factory)continue;
                        modelVersion=result.deployment.active_version;modelSummary="本厂测试 F1 "+result.local.f1.ToString("P1")+" → 联邦 "+result.federated.f1.ToString("P1")+"\n"+(result.deployment.accepted?"已采用联合模型":"保留本厂模型");
                        modelDetails+="\n\n"+job.id+"\n"+modelSummary+"\n召回率 "+result.federated.recall.ToString("P1")+" / 误报率 "+result.federated.false_positive_rate.ToString("P1");
                    }
                    break;
                }
            }
        }
        public IEnumerator Predict(FactoryLine line)
        {
            int generation=epoch,selection=app.selectedLine;
            var b=new Features{factory_id=app.simulation.factory,temp=(int)line.features[0],pressure=(int)line.features[1],wear=(int)line.features[2],material=(int)line.features[3],product=(int)line.features[4]};
            string json=null,error=null;yield return Request("/api/federation/predict",JsonUtility.ToJson(b),(j,e)=>{json=j;error=e;});
            if(!connected||generation!=epoch||app.selectedLine!=selection)yield break;
            if(error!=null){app.simulation.Event(error);yield break;}
            var result=JsonUtility.FromJson<Prediction>(json);risk=result.risk;riskReady=true;modelVersion=result.version;app.simulation.Event("明确编码试算风险 "+risk.ToString("P1"));app.Refresh();
        }
        public void ClearPrediction(){riskReady=false;}
        public void Disconnect()
        {
            connected=false;loggingOut=true;epoch++;if(polling!=null)StopCoroutine(polling);StartCoroutine(Logout());riskReady=false;staff.Clear();
        }
        IEnumerator Logout(){yield return Request("/api/logout","{}",(j,e)=>{});cookie=null;csrf=null;user=null;loggingOut=false;}
    }
}
