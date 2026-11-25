using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;

namespace Zhiyin.FactoryTwin
{
    public class FactoryTwinApp : MonoBehaviour
    {
        public static FactoryTwinApp Instance;
        public FactorySimulation simulation;
        public FactoryOrbitCamera orbit;
        public int selectedLine;
        public bool interior;
        public bool Connected {get{return bridge!=null&&bridge.connected;}}
        public FactoryPlatformBridge bridge;
        RectTransform ui,modal;
        Text brand,clock,mode,selection,context,eventText,valueText,valueNote,shiftText,shiftNote,modelRisk,riskTitle,modelInfo,modelMetrics,qualityNumbers,qualitySummary,sensors,sourceText;
        Text[] staffTexts=new Text[3]; Text[] qualityRows=new Text[4];
        Text[] lineLabels=new Text[4];RectTransform[] labelRects=new RectTransform[4];
        Image[] modelBars=new Image[3];Text[] modelBarLabels=new Text[3];
        FactoryTrendGraphic revenueTrend,tempTrend;
        Button playButton,interiorButton,linkButton;
        Transform[] halls=new Transform[4];
        List<float> temperatures=new List<float>();
        float refreshClock;
        float screenScale=1,screenLeft,screenBottom;
        Renderer[][] outlineRenderers=new Renderer[4][];
        float[] trialFeatures;
        public string PlatformUrl {get{return Connected?bridge.BaseUrl:"http://127.0.0.1:8765";}}
        public void OpenPage(string page){Application.OpenURL(PlatformUrl+"/#"+page);}
        public void Awake()
        {
            Instance=this;simulation=new FactorySimulation();
            FactoryUI.font=Resources.Load<Font>("Fonts/NotoSansSC");
            if(FactoryUI.font==null)FactoryUI.font=Font.CreateDynamicFontFromOSFont(new[]{"Microsoft YaHei","Arial"},18);
            orbit=Camera.main.GetComponent<FactoryOrbitCamera>();
            if(orbit==null)orbit=Camera.main.gameObject.AddComponent<FactoryOrbitCamera>();
            foreach(var s in FindObjectsOfType<FactorySelectable>())if(!s.isEquipment&&s.transform.Find("外墙与屋顶")!=null)halls[s.lineIndex]=s.transform;
            if(EventSystem.current==null){new GameObject("EventSystem",typeof(EventSystem),typeof(StandaloneInputModule));}
            bridge=gameObject.AddComponent<FactoryPlatformBridge>();bridge.app=this;
            for(int i=0;i<4;i++)outlineRenderers[i]=halls[i].Find("设备状态光环").GetComponentsInChildren<Renderer>();
            BuildUI(); Refresh();
            if(System.Array.IndexOf(Environment.GetCommandLineArgs(),"--factory-qa")>=0)gameObject.AddComponent<FactorySelfCheck>();
            QualitySettings.vSyncCount=1;Application.targetFrameRate=60;
        }
        void Update()
        {
            if(!Connected)simulation.Tick(Time.deltaTime);
            refreshClock+=Time.deltaTime;
            if(refreshClock>.5f){refreshClock=0;Refresh();}
            for(int i=0;i<4;i++)
            {
                var line=simulation.lines[i];
                Color color=!line.fresh?new Color(.5f,.59f,.61f):line.faulty||(line.status.Contains("预警")||line.status.Contains("故障"))?FactoryUI.Red:i==selectedLine?FactoryUI.Cyan:new Color(.23f,.55f,.60f);
                foreach(var renderer in outlineRenderers[i])renderer.material.color=color;
            }
            if(Input.GetKeyDown(KeyCode.Escape)){if(modal!=null)CloseModal();else Home();}
            if(Input.GetKeyDown(KeyCode.Alpha1))SelectLine(0,false);
            if(Input.GetKeyDown(KeyCode.Alpha2))SelectLine(1,false);
            if(Input.GetKeyDown(KeyCode.Alpha3))SelectLine(2,false);
            if(Input.GetKeyDown(KeyCode.Alpha4))SelectLine(3,false);
        }
        void LateUpdate()
        {
            screenScale=Mathf.Min(Screen.width/1920f,Screen.height/1080f);
            screenLeft=(Screen.width-1920*screenScale)/2;screenBottom=(Screen.height-1080*screenScale)/2;
            Camera.main.rect=new Rect((screenLeft+463*screenScale)/Screen.width,(screenBottom+202*screenScale)/Screen.height,994*screenScale/Screen.width,708*screenScale/Screen.height);
            for(int i=0;i<4;i++)
            {
                Vector3 p=Camera.main.WorldToScreenPoint(halls[i].position+new Vector3(0,11.7f,0));
                labelRects[i].gameObject.SetActive(p.z>0&&!interior);
                if(p.z<=0)continue;
                float x=(p.x-screenLeft)/screenScale,y=1080-(p.y-screenBottom)/screenScale;
                labelRects[i].anchoredPosition=new Vector2(Mathf.Clamp(x-80,448,1297),-Mathf.Clamp(y,132,875));
            }
        }
        void BuildUI()
        {
            var canvasObject=new GameObject("Factory Dashboard",typeof(RectTransform),typeof(Canvas),typeof(CanvasScaler),typeof(GraphicRaycaster));
            var canvas=canvasObject.GetComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;
            var scale=canvasObject.GetComponent<CanvasScaler>();scale.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;scale.referenceResolution=new Vector2(1920,1080);scale.screenMatchMode=CanvasScaler.ScreenMatchMode.Expand;
            ui=new GameObject("Dashboard Content",typeof(RectTransform)).GetComponent<RectTransform>();
            ui.SetParent(canvasObject.transform,false);ui.anchorMin=ui.anchorMax=ui.pivot=new Vector2(.5f,.5f);ui.sizeDelta=new Vector2(1920,1080);ui.anchoredPosition=Vector2.zero;
            var header=FactoryUI.GlassPanel("Header",ui,0,0,1920,103);
            FactoryUI.Text("Logo",header,"◇",30,14,57,61,45,FactoryUI.Cyan,true);
            brand=FactoryUI.Text("Factory name",header,"质因云联 · 星铸工厂",92,18,650,42,30,FactoryUI.White,true);
            FactoryUI.Text("Subtitle",header,"ZHIYIN YUNLIAN  /  从车间感知到生产决策",94,63,720,24,13,FactoryUI.Muted);
            FactoryUI.Button("About",header,"工厂概况",956,28,104,44,ShowAbout);
            FactoryUI.Button("Switch factory",header,"切换工厂",1074,28,104,44,ShowFactories);
            linkButton=FactoryUI.Button("Platform",header,"连接平台",1192,28,104,44,ShowConnect,true);
            clock=FactoryUI.Text("Clock",header,"",1335,24,300,32,24,FactoryUI.White,true,TextAnchor.MiddleRight);
            mode=FactoryUI.Text("Date",header,"",1290,62,345,20,13,FactoryUI.Muted,false,TextAnchor.MiddleRight);
            FactoryUI.Button("Quit",header,"退出",1782,28,100,44,()=>{if(Application.isEditor){simulation.Event("编辑器中请点击顶部播放按钮停止运行");}else Application.Quit();});
            FactoryUI.Text("StatusDot",header,"●",1653,34,22,25,16,FactoryUI.Cyan);
            sourceText=FactoryUI.Text("Environment",header,"仿真演示",1678,33,90,26,15,FactoryUI.Muted);
            FactoryUI.Panel("Header rule",ui,0,103,1920,1,new Color(.23f,.48f,.55f,.5f));
            BuildRevenue();BuildWorkforce();BuildModel();BuildQuality();
            var center=FactoryUI.GlassPanel("Scene context",ui,463,122,994,48,true);
            context=FactoryUI.Text("Context",center,"园区全景",18,10,810,30,17,FactoryUI.White);
            FactoryUI.Text("Select hint",center,"可交互",888,13,83,22,13,FactoryUI.Cyan);
            for(int i=0;i<4;i++)
            {
                int index=i;
                var b=FactoryUI.Button("Workshop label "+i,ui,"",650,450,160,39,()=>SelectLine(index,false));
                labelRects[i]=b.GetComponent<RectTransform>();lineLabels[i]=b.GetComponentInChildren<Text>();
                lineLabels[i].color=FactoryUI.White;
            }
            var info=FactoryUI.GlassPanel("Selected device",ui,463,878,994,95);
            selection=FactoryUI.Text("Selected",info,"",18,13,520,28,20,FactoryUI.White,true);
            sensors=FactoryUI.Text("Sensors",info,"",18,48,710,24,15,FactoryUI.Muted);
            interiorButton=FactoryUI.Button("Interior",info,"进入车间",790,25,180,45,()=>{if(interior)Home();else SelectLine(selectedLine,true);},true);
            var footer=FactoryUI.GlassPanel("Footer",ui,0,995,1920,85);
            eventText=FactoryUI.Text("Event",footer,"",28,18,845,28,16,FactoryUI.White);
            FactoryUI.Text("Controls",footer,"左键拖动旋转  ·  滚轮缩放  ·  右键平移  ·  数字 1—4 选择车间",28,51,950,23,12,FactoryUI.Muted);
            FactoryUI.Button("Home",footer,"园区全景",969,21,126,44,Home);
            FactoryUI.Button("Orbit",footer,"自动漫游",1107,21,126,44,()=>{orbit.autoOrbit=!orbit.autoOrbit;simulation.Event(orbit.autoOrbit?"自动漫游开启":"自动漫游已暂停");});
            playButton=FactoryUI.Button("Pause",footer,"暂停演示",1245,21,126,44,()=>{if(Connected){simulation.Event("平台模式使用后台采集记录");return;}simulation.playing=!simulation.playing;Refresh();});
            FactoryUI.Button("Fault",footer,"温控故障",1383,21,126,44,()=>{if(Connected){simulation.Event("平台模式请在网页监控中触发演示工况");return;}simulation.Fault(selectedLine);},true);
            FactoryUI.Button("Recover",footer,"降温 / 复产",1521,21,151,44,()=>{if(Connected){simulation.Event("平台模式请在网页中处理恢复与复产");return;}simulation.Recover(selectedLine);});
            FactoryUI.Button("Workspace",footer,"网页工作台 ↗",1684,21,202,44,()=>OpenPage("workshop"));
        }
        void BuildRevenue()
        {
            var card=FactoryUI.Card(ui,"经营概况","01 / BUSINESS OVERVIEW",26,122,410,380,FactoryUI.Gold);
            FactoryUI.Text("Label",card,"当日估算产值",22,94,310,28,16,FactoryUI.Muted);
            valueText=FactoryUI.Text("Amount",card,"",22,123,365,66,47,FactoryUI.White,true);
            valueNote=FactoryUI.Text("Amount note",card,"",22,193,365,47,13,FactoryUI.Muted);
            var r=FactoryUI.Rect("Trend",card,23,252,364,65);revenueTrend=r.gameObject.AddComponent<FactoryTrendGraphic>();revenueTrend.raycastTarget=false;revenueTrend.lineColor=FactoryUI.Gold;
            FactoryUI.Text("Trend caption",card,"近 7 个生产日 · 独立模拟记录",23,326,340,25,12,FactoryUI.Muted);
            FactoryUI.Button("Business details",card,"查看经营口径",22,348,365,25,ShowBusiness);
        }
        void BuildWorkforce()
        {
            var card=FactoryUI.Card(ui,"当班人员与排班","02 / PEOPLE & SHIFT",26,523,410,450,FactoryUI.Cyan);
            shiftText=FactoryUI.Text("Shift",card,"",22,93,365,32,23,FactoryUI.White,true);
            shiftNote=FactoryUI.Text("Shift note",card,"",22,134,365,42,14,FactoryUI.Muted);
            for(int i=0;i<3;i++)
            {
                FactoryUI.Panel("Staff background",card,22,190+i*55,365,45,new Color(.08f,.18f,.23f,.8f));
                FactoryUI.Text("Staff icon",card,"●",33,202+i*55,22,24,12,FactoryUI.Cyan);
                staffTexts[i]=FactoryUI.Text("Staff "+i,card,"",62,200+i*55,309,28,16,FactoryUI.White);
            }
            FactoryUI.Text("Attendance boundary",card,"当班依据班表；实际到岗需现场确认。",22,368,365,24,12,FactoryUI.Muted);
            FactoryUI.Button("Schedule",card,"查看班表",22,400,173,31,ShowSchedule);
            FactoryUI.Button("Assign",card,"安排检查",211,400,176,31,()=>{if(Connected){OpenPage("analysis");return;}simulation.Dispatch(selectedLine);Refresh();},true);
        }
        void BuildModel()
        {
            var card=FactoryUI.Card(ui,"联邦质量研判","03 / FEDERATED INSIGHTS",1484,122,410,410,FactoryUI.Cyan);
            riskTitle=FactoryUI.Text("Risk title",card,"当前工艺条件 · 不合格风险",22,94,367,24,15,FactoryUI.Muted);
            modelRisk=FactoryUI.Text("Risk",card,"",22,121,365,54,42,FactoryUI.Cyan,true);
            modelInfo=FactoryUI.Text("Model link",card,"",22,179,366,55,13,FactoryUI.Muted);
            modelMetrics=FactoryUI.Text("Validation",card,"",22,240,366,45,14,FactoryUI.White);
            for(int i=0;i<3;i++)
            {
                FactoryUI.Text("Factory "+i,card,simulation.factories[i],22,300+i*25,89,21,12,FactoryUI.Muted);
                FactoryUI.Panel("Metric track",card,112,307+i*25,190,5,new Color(.17f,.28f,.34f));
                var bar=FactoryUI.Panel("Metric fill",card,112,307+i*25,100,5,FactoryUI.Cyan);modelBars[i]=bar.GetComponent<Image>();
                modelBarLabels[i]=FactoryUI.Text("Metric value",card,"",314,297+i*25,77,26,13,FactoryUI.White);
            }
            FactoryUI.Button("Evidence",card,"模型依据与适用范围",22,379,365,25,ShowModel);
        }
        void BuildQuality()
        {
            var card=FactoryUI.Card(ui,"零件质量与异常","04 / QUALITY & EXCEPTIONS",1484,552,410,421,FactoryUI.Gold);
            qualityNumbers=FactoryUI.Text("Quality KPI",card,"",22,94,365,43,30,FactoryUI.White,true);
            FactoryUI.Text("Quality KPI labels",card,"当前批次 · 抽检总数 / 不合格件数",22,141,365,23,13,FactoryUI.Muted);
            qualitySummary=FactoryUI.Text("Quality summary",card,"",22,177,365,42,14,FactoryUI.Muted);
            for(int i=0;i<4;i++)
            {
                qualityRows[i]=FactoryUI.Text("Line quality "+i,card,"",22,242+i*29,365,24,14,FactoryUI.White);
            }
            FactoryUI.Button("Quality detail",card,"查看缺陷与处置",22,378,365,29,ShowQuality,true);
        }
        public void SelectLine(int index,bool enter)
        {
            selectedLine=Mathf.Clamp(index,0,3);temperatures.Clear();
            if(bridge!=null)bridge.ClearPrediction();
            if(enter)
            {
                foreach(var h in halls)h.Find("外墙与屋顶").gameObject.SetActive(h!=halls[selectedLine]);
                interior=true;orbit.Focus(halls[selectedLine].position,true);
            }
            else if(interior) {Home();selectedLine=index;}
            simulation.Event("已选中"+simulation.lines[selectedLine].name+" · 四个面板按当前范围联动");Refresh();
        }
        public void Home()
        {
            interior=false;foreach(var h in halls)h.Find("外墙与屋顶").gameObject.SetActive(true);
            orbit.Home();Refresh();
        }
        public void Refresh()
        {
            if(brand==null)return;
            var l=simulation.lines[selectedLine];var node=simulation.model.nodes[simulation.factory-1];
            brand.text="质因云联 · "+simulation.factories[simulation.factory-1];
            clock.text=DateTime.Now.ToString("HH:mm:ss");mode.text=DateTime.Now.ToString("yyyy年MM月dd日")+"  北京时间";
            context.text=(interior?"车间设备视图":"厂区全景")+"  /  "+l.name+"  /  "+l.batch;
            selection.text="EQ-"+l.deviceId.ToString("00")+"  "+l.equipment+"   ·   "+(l.fresh?l.status:"通信未知");
            sensors.text=!l.fresh?"采集过期 / 通信未知 · 当前传感值不可用":"温度 "+l.temperature.ToString("F1")+" ℃     压力 "+l.pressure.ToString("F2")+" MPa     振动 "+l.vibration.ToString("F2")+" mm/s";
            interiorButton.GetComponentInChildren<Text>().text=interior?"返回厂区":"进入车间";
            eventText.text=(Connected?"平台数据  ":"仿真演示  ")+simulation.eventTime+"  "+simulation.lastEvent;
            playButton.GetComponentInChildren<Text>().text=simulation.playing?"暂停演示":"继续演示";
            sourceText.text=Connected?"平台数据":"仿真演示";
            linkButton.GetComponentInChildren<Text>().text=Connected?"平台已连接":"连接平台";
            valueText.text=Connected?"—":"¥ "+simulation.ProductionValue.ToString("N0");
            valueNote.text=Connected?"平台尚未配置销售收入数据。\n营业额需销售订单与收入确认记录。":"全厂口径 · 完成数量 × 演示参考单价\n估算产值，不等同于营业额或回款。";
            revenueTrend.gameObject.SetActive(!Connected);
            revenueTrend.Set(new[]{185000f,212000,194000,247000,269000,256000,simulation.ProductionValue});
            int hour=DateTime.Now.Hour;string shift=hour>=8&&hour<16?"早班 08:00—16:00":hour>=16?"晚班 16:00—次日00:00":"非排班时段";
            shiftText.text=Connected?bridge.shiftTitle:shift;
            shiftNote.text=Connected?bridge.shiftNote:(hour<8?"当前无排班 · 以下为下一班已排人员\n演示班表，不代表实际到岗":l.name+" · 需求 3 人 / 已排 3 人\n"+l.task+" · 演示班表");
            for(int i=0;i<3;i++)staffTexts[i].text=Connected?(i<bridge.staff.Count?bridge.staff[i]:"—"):simulation.staff[selectedLine][i];
            riskTitle.text=Connected?"已确认工艺编码 · 风险试算":"演示工艺条件 · 不合格风险";
            modelRisk.text=Connected?(bridge.riskReady?bridge.risk.ToString("P1"):"待试算"):l.risk.ToString("P1");
            modelRisk.color=(!Connected?l.risk>=simulation.model.threshold:bridge.riskReady&&bridge.risk>=.35f)?FactoryUI.Gold:FactoryUI.Cyan;
            string version=Connected?bridge.modelVersion:node.accepted?simulation.model.version:"本厂基线";
            modelInfo.text="EQ-"+l.deviceId.ToString("00")+"  ·  "+l.batch+"\n模型："+version;
            modelMetrics.text=Connected?bridge.modelSummary:"本厂测试 F1 "+node.localF1.ToString("P1")+"  →  联邦 "+node.federatedF1.ToString("P1")+"\n"+(node.accepted?"本厂验证通过，采用联合模型":"本厂验证未通过，保留本厂模型");
            for(int i=0;i<3;i++)
            {
                float f=Connected?bridge.factoryF1[i]:simulation.model.nodes[i].federatedF1;
                modelBars[i].rectTransform.sizeDelta=new Vector2(190*f,5);
                modelBarLabels[i].text=f>0?f.ToString("P0"):"—";
            }
            qualityNumbers.text=l.inspected.ToString("N0")+"      /      "+l.defects.ToString("N0");
            qualitySummary.text="批次 "+l.batch+"\n"+(l.inspected>0?"抽检合格率 "+(1f-(float)l.defects/l.inspected).ToString("P1"):"暂无抽检记录")+" · "+l.task;
            for(int i=0;i<4;i++)
            {
                var row=simulation.lines[i];lineLabels[i].text=(selectedLine==i?"● ":"")+row.name;
                qualityRows[i].text=row.name+"    不合格 "+row.defects+" 件    "+((row.status.Contains("预警")||row.status.Contains("故障"))?"预警":"记录");
                qualityRows[i].color=(row.status.Contains("预警")||row.status.Contains("故障"))?FactoryUI.Gold:FactoryUI.White;
            }
            if(temperatures.Count>=35)temperatures.RemoveAt(0);temperatures.Add(l.temperature);
            if(tempTrend!=null)tempTrend.Set(temperatures.ToArray());
        }
        public void CloseDialog(){CloseModal();}
        void CloseModal(){if(modal!=null)Destroy(modal.gameObject);modal=null;tempTrend=null;}
        RectTransform Modal(string title,string subtitle,int height=610)
        {
            CloseModal();modal=FactoryUI.Panel("Modal backdrop",ui,0,0,1920,1080,new Color(0,.025f,.045f,.66f));
            var card=FactoryUI.Card(modal,title,subtitle,530,(1080-height)/2,860,height,FactoryUI.Cyan);
            FactoryUI.Button("Close",card,"关闭",738,25,98,37,CloseModal);return card;
        }
        public void ShowAbout()
        {
            var card=Modal("工厂概况","FACTORY PROFILE",590);
            FactoryUI.Text("Introduction",card,simulation.factories[simulation.factory-1]+"以精密零部件制造为演示场景，涵盖成型、加工、装配与在线检测。三维空间关联设备、批次、当班人员和质量研判，让每一次异常都有可定位的对象与可追溯的处理过程。",30,106,797,115,21,FactoryUI.White);
            FactoryUI.Rule(card,30,248,797);
            FactoryUI.Text("Profile",card,"园区布局   4 个生产车间 + 研发办公楼 + 物流仓储中心\n生产环节   成型 → 加工 → 装配 → 检验\n空间交互   厂房选择、设备定位、车间剖切、旋转与缩放\n业务协同   排班与技能、联邦模型、质量记录、异常处置",30,271,797,172,20,FactoryUI.Muted);
            FactoryUI.Text("Scope",card,"当前园区为参考视频布局原创搭建的仿真场景；尺寸为演示设计，尚未接入真实工厂测绘、设备或考勤数据。",30,472,797,70,16,FactoryUI.Muted);
        }
        void ShowBusiness()
        {
            var card=Modal("经营指标口径","BUSINESS METRICS",430);
            FactoryUI.Text("Business explanation",card,"当前演示指标：估算产值 = 各产线累计完成数量 × 演示参考单价。\n\n营业额需要销售订单、实际成交价格与收入确认状态；回款额需要独立的收款记录。平台没有这些数据时显示“未配置”。\n\n累计完成数量只在生产节拍结束后增加，暂停、故障、工单完成时停止增长；厂房面积、人员档案等固定数据不随机波动。",30,110,798,257,19,FactoryUI.White);
        }
        public void ShowSchedule()
        {
            var l=simulation.lines[selectedLine];var card=Modal("产线班表 · "+l.name,"SHIFT PLANNING",490);
            FactoryUI.Text("Shift details",card,Connected?bridge.scheduleDetails:"早班   08:00—16:00   晨星班组   需求 3 人\n晚班   16:00—次日00:00   逐光班组   需求 3 人\n\n当前安排：\n"+string.Join("\n",simulation.staff[selectedLine])+"\n\n班次交接、请假与替班在网页“人员与排班”中维护。",30,108,798,280,20,FactoryUI.White);
            FactoryUI.Button("Open schedule",card,"打开网页排班管理 ↗",30,405,798,45,()=>OpenPage("workforce"),true);
        }
        public void ShowModel()
        {
            var l=simulation.lines[selectedLine];var card=Modal("模型依据 · "+l.batch,"FEDERATED MODEL EVIDENCE",620);
            var n=simulation.model.nodes[simulation.factory-1];
            string text=Connected?bridge.modelDetails:"三个工厂在独立合成样本上训练逻辑回归，按样本量进行 FedAvg 参数聚合，共 10 轮。本厂是否采用联合模型，由本厂验证集决定；测试指标只用于结果展示。\n\n输入编码：温度偏高、压力偏高、设备磨损、原料等级、产品规格。\n当前演示编码：["+string.Join(", ",l.features)+"]\n\n本厂训练 / 验证 / 测试样本："+n.trainCount+" / "+n.validationCount+" / "+n.testCount+"\n联合模型测试召回率："+n.recall.ToString("P1")+"    误报率："+n.falsePositiveRate.ToString("P1");
            FactoryUI.Text("Model evidence",card,text,30,108,798,285,19,FactoryUI.White);
            FactoryUI.Text("Boundary",card,"预测风险用于检查优先级，不等于已检出的不合格零件，也不是因果干预收益。原始训练样本留在各厂；当前演示没有差分隐私或安全聚合。",30,408,798,96,17,FactoryUI.Muted);
            FactoryUI.Button("Risk calculation",card,"调整工艺编码试算",30,539,381,45,ShowFeatures,true);
            FactoryUI.Button("Federation page",card,"打开联邦分析 ↗",430,539,398,45,()=>OpenPage("federation"));
        }
        public void ShowFeatures()
        {
            var card=Modal("工艺条件风险试算","PROCESS FEATURES",580);var l=simulation.lines[selectedLine];trialFeatures=(float[])l.features.Clone();
            string[] names={"温度偏高","压力偏高","设备磨损","原料等级（类别1）","产品规格（类别1）"};
            for(int i=0;i<5;i++)
            {
                int index=i;FactoryUI.Text("Feature "+i,card,names[i],30,107+i*63,510,34,20,FactoryUI.White);
                var button=FactoryUI.Button("Feature toggle "+i,card,trialFeatures[i]==1?"1 · 是":"0 · 否",610,102+i*63,215,41,()=>{});
                button.onClick.AddListener(()=>{trialFeatures[index]=1-trialFeatures[index];button.GetComponentInChildren<Text>().text=trialFeatures[index]==1?"1 · 是":"0 · 否";});
            }
            FactoryUI.Text("Feature note",card,"编码需与训练工艺一致；试算结果不自动修改设备参数。",30,429,797,28,16,FactoryUI.Muted);
            FactoryUI.Button("Calculate",card,"计算当前条件风险",30,489,797,46,()=>{
                if(Connected){l.features=(float[])trialFeatures.Clone();StartCoroutine(bridge.Predict(l));CloseModal();}else{
                    float result=simulation.model.Predict(trialFeatures,simulation.factory);
                    var resultCard=Modal("工艺试算结果","PROCESS RISK",400);
                    FactoryUI.Text("Trial result",resultCard,"所选条件风险："+result.ToString("P1")+"\n输入编码：["+string.Join(", ",trialFeatures)+"]\n\n这是一组假设工艺条件；设备实时参数与生产状态保持原值。\n请结合批次记录与现场核查，人工决定是否调整生产参数。",30,108,797,225,21,FactoryUI.White);
                    simulation.Event("假设工艺条件风险 "+result.ToString("P1"));
                }Refresh();
            },true);
        }
        public void ShowQuality()
        {
            var l=simulation.lines[selectedLine];var card=Modal("零件异常 · "+l.batch,"QUALITY TRACEABILITY",600);
            FactoryUI.Text("Quality context",card,"关联设备：EQ-"+l.deviceId.ToString("00")+"  "+l.equipment+"\n批次抽检："+l.inspected+" 件    不合格："+l.defects+" 件\n处置状态："+l.task,30,105,797,110,21,FactoryUI.White);
            FactoryUI.Text("Defect facts",card,Connected?bridge.qualityDetails:"演示缺陷记录：尺寸偏差、外观划伤、装配偏位。\n目前统计到批次级；没有单件追溯码或缺陷照片时，不显示虚构的单件定位。\n\n建议先核对实际工况、量具和批次记录，再结合模型结果确定检查优先级。",30,232,797,156,19,FactoryUI.Muted);
            var r=FactoryUI.Rect("Temperature trace",card,32,411,790,77);tempTrend=r.gameObject.AddComponent<FactoryTrendGraphic>();tempTrend.raycastTarget=false;tempTrend.Set(temperatures.ToArray());
            FactoryUI.Text("Trace label",card,"所选设备最近观察温度",30,495,790,23,13,FactoryUI.Muted);
            FactoryUI.Button("Analyze",card,"因果诊断与处置 ↗",30,532,Connected?797:540,43,()=>OpenPage("analysis"),true);
            if(!Connected)FactoryUI.Button("Review",card,"确认复检通过",592,532,235,43,()=>{simulation.Review(selectedLine);Refresh();ShowQuality();});
        }
        void ShowFactories()
        {
            var card=Modal("选择工厂","FACTORY NETWORK",410);
            for(int i=0;i<3;i++)
            {
                int index=i+1;
                var button=FactoryUI.Button("Factory "+index,card,simulation.factories[i]+"   /   节点 0"+index,30,109+i*75,797,52,()=>{
                    if(Connected&&!bridge.CanFactory(index)){simulation.Event("当前平台账号仅可访问自己的工厂");return;}
                    simulation.Reset(index);Home();CloseModal();if(Connected)bridge.RefreshNow();Refresh();
                },i==simulation.factory-1);
                if(Connected&&!bridge.CanFactory(index))button.interactable=false;
            }
        }
        void ShowConnect()
        {
            if(Connected)
            {
                var card=Modal("平台连接","PLATFORM SESSION",390);
                FactoryUI.Text("Connected",card,"当前用户："+bridge.userName+"\n通过现有登录与工厂权限读取平台数据。\n采集过期时显示通信未知；模型需要明确工艺编码后试算。",30,111,797,152,20,FactoryUI.White);
                FactoryUI.Button("Disconnect",card,"退出平台连接，返回独立演示",30,289,797,49,()=>{bridge.Disconnect();simulation.Reset(simulation.factory);CloseModal();Refresh();});return;
            }
            var panel=Modal("连接质因云联平台","PLATFORM CONNECTION",590);
            FactoryUI.Text("Connection note",panel,"先运行项目根目录中的 start.bat 启动网页服务。连接后按平台账号权限读取设备、工单、排班、质检和模型记录。",30,105,797,71,18,FactoryUI.Muted);
            var url=FactoryUI.Input("Server",panel,"http://127.0.0.1:8765",30,194,797,46);url.text="http://127.0.0.1:8765";
            var user=FactoryUI.Input("Username",panel,"平台账号",30,263,797,46);user.text="admin";
            var password=FactoryUI.Input("Password",panel,"网页登录密码",30,332,797,46,true);
            var error=FactoryUI.Text("Error",panel,"",30,405,797,65,16,FactoryUI.Gold);
            FactoryUI.Button("Login",panel,"登录并同步平台数据",30,490,797,48,()=>StartCoroutine(bridge.Login(url.text,user.text,password.text,result=>{
                if(result==null){CloseModal();Refresh();}else if(error!=null)error.text=result;
            })),true);
        }
    }
}
