using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Zhiyin.FactoryTwin
{
    // Opt-in executable checks. No test UI appears during normal use.
    public class FactorySelfCheck : MonoBehaviour
    {
        [Serializable] class Report {public List<string> passed=new List<string>();public List<string> failed=new List<string>();}
        Report report=new Report();string output;FactoryTwinApp app;
        void Check(bool condition,string name){(condition?report.passed:report.failed).Add(name);Debug.Log((condition?"QA PASS ":"QA FAIL ")+name);}
        IEnumerator Capture(string name)
        {
            yield return new WaitForEndOfFrame();ScreenCapture.CaptureScreenshot(Path.Combine(output,name+".png"));yield return new WaitForSecondsRealtime(.7f);
        }
        IEnumerator Start()
        {
            app=FactoryTwinApp.Instance;var args=Environment.GetCommandLineArgs();int index=System.Array.IndexOf(args,"--factory-qa-output");
            output=index>=0&&index+1<args.Length?args[index+1]:Path.Combine(Application.persistentDataPath,"QA");Directory.CreateDirectory(output);
            Application.logMessageReceived+=Log;
            yield return new WaitForSecondsRealtime(3);
            app.simulation.playing=false;app.Refresh();
            Check(app.simulation.model!=null&&app.simulation.model.nodes.Length==3,"Trained model artifact loaded");
            Check(FindObjectsOfType<FactorySelectable>().Length>=20,"Four halls and selectable equipment exist");
            Check(GameObject.Find("Factory Dashboard")!=null&&FactoryUI.font!=null,"Dashboard and redistributable Chinese font loaded");
            var campus=GameObject.Find("质因云联 · 仿真园区");var renderers=campus.GetComponentsInChildren<Renderer>();Bounds bounds=renderers[0].bounds;
            foreach(var renderer in renderers)bounds.Encapsulate(renderer.bounds);
            bool fits=true;var camera=Camera.main;
            foreach(float x in new[]{bounds.min.x,bounds.max.x})foreach(float y in new[]{bounds.min.y,bounds.max.y})foreach(float z in new[]{bounds.min.z,bounds.max.z})
            {
                Vector3 projected=camera.WorldToScreenPoint(new Vector3(x,y,z));if(projected.z<=0||!camera.pixelRect.Contains(projected))fits=false;
            }
            Check(fits,"Full campus bounds fit central viewport at startup");
            Check(GameObject.Find("生态景观 · 远山树林与湖泊")!=null&&GameObject.Find("生态湖 · 动态水面")!=null,"Editable forest, mountains and animated lake exist");
            Check(GameObject.Find("林带树冠 0").GetComponent<MeshFilter>().sharedMesh.vertexCount>1000,"Combined forest retains visible canopy geometry");
            Check(GameObject.Find("参考风格 · 配套工业园")!=null,"Blue-roof auxiliary industrial campus exists");
            Check(GameObject.Find("林带透光枝叶 0").GetComponent<Renderer>().sharedMaterial.mainTexture!=null,"Original foliage texture persists in exported player");
            Check(RenderSettings.fog&&RenderSettings.fogDensity<.002f,"Light atmospheric depth fog enabled");
            var backdrop=GameObject.Find("Dashboard Background").GetComponent<Camera>();
            Vector3 testPoint=new Vector3(31,5,20);
            var backgroundPoint=backdrop.WorldToScreenPoint(testPoint);var centralPoint=camera.WorldToScreenPoint(testPoint);
            Debug.Log("QA projection pixels: background="+backgroundPoint.ToString("F3")+" central="+centralPoint.ToString("F3"));
            Check(Vector2.Distance(backgroundPoint,centralPoint)<1,"Full-screen scenery projection aligns within one raster pixel");
            Check(FindObjectsOfType<FactoryGlassGraphic>().Length==8,"Four data cards and four bars use translucent glass");
            Check(GameObject.Find("01 成型车间").transform.Find("外墙与屋顶/屋顶光伏").GetComponent<Renderer>().sharedMaterial.shader.name=="Zhiyin/Photovoltaic","Deep-blue photovoltaic cell shader loaded");
            yield return Capture("01-campus");
            for(int i=0;i<4;i++){app.SelectLine(i,false);Check(app.selectedLine==i,"Selection scope line "+i);}
            app.SelectLine(0,true);yield return new WaitForSecondsRealtime(2);yield return Capture("02-workshop");
            Check(app.interior&&!GameObject.Find("01 成型车间").transform.Find("外墙与屋顶").gameObject.activeSelf,"Workshop cutaway hides selected shell");
            app.Home();Check(!app.interior&&GameObject.Find("01 成型车间").transform.Find("外墙与屋顶").gameObject.activeSelf,"Home restores workshop shell");
            var sim=app.simulation;sim.playing=true;
            Check(!sim.Recover(0)&&sim.lines[0].task=="暂无待办","Running line does not create phantom repair review");
            sim.Fault(0);sim.Tick(1);sim.Recover(0);
            Check(sim.lines[0].running&&sim.lines[0].status=="运行","Early fault cancellation preserves running status");
            sim.Fault(0);for(int i=0;i<100;i++)sim.Tick(.1f);
            Check(!sim.lines[0].running&&sim.lines[0].temperature>=90,"Temperature limit stops line");
            int completed=sim.lines[0].completed;for(int i=0;i<50;i++)sim.Tick(.1f);
            Check(sim.lines[0].completed==completed,"Stopped line does not produce");
            sim.Dispatch(0);Check(sim.lines[0].task=="处理中","Inspection task assigned");
            sim.Recover(0);Check(!sim.Recover(0),"Unsafe premature restart blocked");
            for(int i=0;i<140;i++)sim.Tick(.1f);Check(sim.Recover(0)&&sim.lines[0].running,"Stable cooling allows manual restart");
            completed=sim.lines[0].completed;sim.Tick(6);Check(sim.lines[0].completed>completed,"Production resumes at cycle boundary");
            Check(!sim.Review(0),"Repair review requires new post-restart sample");
            for(int i=0;i<120&&!sim.Review(0);i++)sim.Tick(1);
            Check(sim.lines[0].task=="已关闭","Clean post-restart sample closes inspection task");
            sim.playing=false;completed=sim.lines[0].completed;sim.Tick(20);Check(sim.lines[0].completed==completed,"Paused simulation holds cumulative totals");
            float low=sim.model.Predict(new float[5],1),high=sim.model.Predict(new[]{1f,1f,1f,1f,1f},1);
            Check(low>=0&&high<=1&&high>low,"Actual model inference responds to conditions");
            float value=0;foreach(var line in sim.lines)value+=line.completed*line.referencePrice;Check(Mathf.Approximately(value,sim.ProductionValue),"Output value equals completed quantity times reference unit price");
            sim.Reset(2);Check(sim.lines[0].deviceId==5&&sim.factory==2,"Factory switch resets equipment and batch scope");sim.Reset(1);sim.playing=false;app.Refresh();
            app.ShowAbout();yield return Capture("03-profile");
            app.ShowModel();yield return Capture("04-model");
            app.ShowQuality();yield return Capture("05-quality");
            app.ShowSchedule();yield return Capture("06-schedule");
            app.CloseDialog();app.Home();
            orbitReview();yield return new WaitForSecondsRealtime(2);yield return Capture("07-landscape-orbit");
            app.Home();yield return new WaitForSecondsRealtime(2);
            int serverArg=System.Array.IndexOf(args,"--factory-qa-server");
            if(serverArg>=0&&serverArg+1<args.Length){yield return OnlineCheck(args[serverArg+1]);}

            File.WriteAllText(Path.Combine(output,"report.json"),JsonUtility.ToJson(report,true));
            Application.logMessageReceived-=Log;Application.Quit(report.failed.Count==0?0:1);
        }
        void orbitReview(){app.orbit.SetView(34);}
        IEnumerator OnlineCheck(string url)
        {
            string error=null;yield return app.bridge.Login(url,"qa-engineer","qa-only",e=>error=e);
            Check(error==null&&app.Connected&&app.simulation.factory==2,"Authenticated platform selects account factory");
            Check(app.bridge.CanFactory(2)&&!app.bridge.CanFactory(1),"Non-admin factory isolation");
            float deadline=Time.realtimeSinceStartup+12;
            while(Time.realtimeSinceStartup<deadline&&!app.simulation.lines[0].fresh)yield return null;
            Check(app.simulation.lines[0].deviceId==5&&app.simulation.lines[0].fresh,"Platform equipment sync");
            Check(app.simulation.lines[0].batch=="QA-BATCH-2"&&app.simulation.lines[0].inspected==100&&app.simulation.lines[0].defects==3,"Platform order and quality association");
            Check(app.bridge.staff.Count==2&&app.bridge.shiftTitle.Contains("当班"),"Actual active shift and leave exclusion");
            Check(Mathf.Abs(app.bridge.factoryF1[1]-.73f)<.001f&&app.bridge.factoryF1[0]==0,"Scoped completed model metrics");
            yield return app.bridge.Predict(app.simulation.lines[0]);Check(app.bridge.riskReady&&Mathf.Abs(app.bridge.risk-.42f)<.001f,"Authenticated risk calculation");
            app.SelectLine(1,false);Check(!app.bridge.riskReady,"Selection clears prior batch risk");
            app.bridge.Disconnect();Check(!app.Connected,"Platform logout returns offline mode");
            app.simulation.Reset(1);app.Refresh();yield return new WaitForSecondsRealtime(1);
        }
        void Log(string message,string stack,LogType type){if(type==LogType.Exception||type==LogType.Error||type==LogType.Assert)report.failed.Add(type+": "+message);}
    }
}
