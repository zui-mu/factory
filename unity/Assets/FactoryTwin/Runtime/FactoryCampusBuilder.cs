using System.Collections.Generic;
using UnityEngine;

namespace Zhiyin.FactoryTwin
{
    /// <summary>Original, editable geometry generated with Unity primitives. Units are metres.</summary>
    public static class FactoryCampusBuilder
    {
        static Dictionary<string, Material> materials = new Dictionary<string, Material>();
        static Material M(string name, Color color, float metal = 0, float smooth = .25f)
        {
            if (materials.ContainsKey(name)) return materials[name];
            string shader=name=="光伏面板"?"Zhiyin/Photovoltaic":name=="工业外墙"||name=="屋面"||name=="蓝色辅房屋面"||name=="仓库白墙"?"Zhiyin/Industrial Surface":"Standard";
            var m = new Material(Shader.Find(shader)); m.name = name;
            m.color = color; m.SetFloat("_Metallic", metal); m.SetFloat("_Glossiness", smooth);
            m.enableInstancing=true;
            materials[name] = m; return m;
        }
        static Material C(string name, string hex, float metal = 0, float smooth = .25f)
        { Color value; ColorUtility.TryParseHtmlString(hex, out value); return M(name,value,metal,smooth); }
        static GameObject Box(string name, Transform parent, Vector3 pos, Vector3 size, Material mat, bool collider = false)
        {
            var o = GameObject.CreatePrimitive(PrimitiveType.Cube); o.name = name;
            o.transform.SetParent(parent,false); o.transform.localPosition = pos; o.transform.localScale = size;
            o.GetComponent<Renderer>().sharedMaterial = mat;
            if (!collider) Object.DestroyImmediate(o.GetComponent<Collider>());
            return o;
        }
        static GameObject Cylinder(string name, Transform parent, Vector3 pos, float radius, float height, Material mat)
        {
            var o=GameObject.CreatePrimitive(PrimitiveType.Cylinder);o.name=name;
            o.transform.SetParent(parent,false);o.transform.localPosition=pos;o.transform.localScale=new Vector3(radius*2,height/2,radius*2);
            o.GetComponent<Renderer>().sharedMaterial=mat;Object.DestroyImmediate(o.GetComponent<Collider>());return o;
        }
        static Transform Group(string name,Transform parent,Vector3 pos)
        {var o=new GameObject(name);o.transform.SetParent(parent,false);o.transform.localPosition=pos;return o.transform;}
        public static GameObject Build()
        {
            materials.Clear();
            FactoryVegetationBuilder.Prepare();
            var root = new GameObject("质因云联 · 仿真园区");
            var t = root.transform;
            var grass=C("草坪","#526F40");var asphalt=C("沥青道路","#303C45",.03f,.26f);
            var paving=C("浅色铺装","#C3CBCB",0,.32f);var white=C("道路标线","#F1F1E5");
            Box("园区基座",t,new Vector3(0,-1.35f,0),new Vector3(168,2.4f,124),C("基座岩石","#8F9F96"));
            Box("外围草地",t,new Vector3(0,-.08f,0),new Vector3(167,.18f,123),grass);
            Box("园区铺装",t,new Vector3(0,.03f,0),new Vector3(154,.18f,110),paving);
            Box("前方主路",t,new Vector3(0,.16f,-46),new Vector3(154,.08f,10),asphalt);
            Box("后方主路",t,new Vector3(0,.16f,42),new Vector3(154,.08f,9),asphalt);
            Box("中央物流路",t,new Vector3(0,.16f,-1),new Vector3(154,.08f,10),asphalt);
            Box("西侧环路",t,new Vector3(-68,.16f,-1),new Vector3(8,.08f,89),asphalt);
            Box("东侧环路",t,new Vector3(66,.16f,-1),new Vector3(8,.08f,89),asphalt);
            Box("中间道路",t,new Vector3(0,.16f,0),new Vector3(8,.08f,88),asphalt);
            for(int i=-13;i<=13;i++)
            {
                foreach(float z in new[]{-46f,-1f,42f})Box("道路中线",t,new Vector3(i*5,.22f,z),new Vector3(2.5f,.012f,.16f),white);
            }
            for(int i=-8;i<=8;i++)
                foreach(float x in new[]{-68f,0f,66f})Box("环路中线",t,new Vector3(x,.22f,i*5),new Vector3(.16f,.012f,2.5f),white);
            for(int i=0;i<8;i++)
                foreach(float x in new[]{-5.2f,5.2f})Box("人行横道",t,new Vector3(x,.225f,-46+i*.45f-1.7f),new Vector3(2.5f,.014f,.22f),white);
            Vector3[] positions={new Vector3(-31,0,20),new Vector3(31,0,20),new Vector3(-31,0,-24),new Vector3(31,0,-24)};
            for(int i=0;i<4;i++)BuildWorkshop(t,positions[i],i);
            BuildOffice(t,new Vector3(-55,0,50));
            var warehouse=Group("物流仓储中心",t,new Vector3(42,0,51));
            Box("仓库主体",warehouse,new Vector3(0,3,0),new Vector3(28,6,10),C("仓库白墙","#D8DFE2",.15f,.45f));
            Box("仓库顶",warehouse,new Vector3(0,6.3f,0),new Vector3(29,.4f,11),C("蓝色辅房屋面","#3D85AB",.28f,.5f));
            for(int i=0;i<4;i++)Box("装卸口",warehouse,new Vector3(-9+i*6,2,-5.1f),new Vector3(3,4,.2f),C("装卸门","#3B5B66",.3f));
            for(int i=0;i<5;i++)Tree(t,new Vector3(-77,0,-43+i*20));
            for(int i=0;i<5;i++)Tree(t,new Vector3(77,0,-43+i*20));
            for(int i=0;i<13;i++)
            {
                Tree(t,new Vector3(-71+i*12,0,-56));
                if(i%2==0)Tree(t,new Vector3(-71+i*12,0,58));
            }
            for(int i=0;i<8;i++)
            {
                StreetLamp(t,new Vector3(-57+i*16,0,-40));
                StreetLamp(t,new Vector3(-57+i*16,0,36));
            }
            for(int i=0;i<10;i++)
            {
                float x=-57+i*5.3f;
                Box("停车位左线",t,new Vector3(x,.23f,-51),new Vector3(.12f,.02f,4),white);
                Box("停车位后线",t,new Vector3(x+2.55f,.23f,-53),new Vector3(5.1f,.02f,.12f),white);
                if(i%3!=1)Car(t,new Vector3(x+2.5f,0,-51),i);
            }
            BuildFence(t,new Vector3(-82,0,61),new Vector3(82,0,61));
            BuildFence(t,new Vector3(-83,0,-61),new Vector3(-83,0,61));
            BuildFence(t,new Vector3(83,0,-61),new Vector3(83,0,61));
            Box("门卫室",t,new Vector3(69,1.7f,-55),new Vector3(5,3.4f,4),C("办公外墙","#D7DEDB"));
            Box("入口蓝色门架",t,new Vector3(58,4.5f,-57),new Vector3(14,1.1f,.7f),C("品牌蓝","#28728A",.4f));
            Box("入口立柱",t,new Vector3(51,2,-57),new Vector3(.65f,4,.65f),C("品牌蓝","#28728A",.4f));
            Box("入口立柱",t,new Vector3(65,2,-57),new Vector3(.65f,4,.65f),C("品牌蓝","#28728A",.4f));
            for(int i=0;i<4;i++)
            {
                var l=Group("厂区导视",t,new Vector3(-55+i*36,0,-38));
                Box("导视板",l,new Vector3(0,1.5f,0),new Vector3(2.4f,2.5f,.2f),C("品牌蓝","#28728A",.4f));
            }
            BuildCampusDetails(t,paving,grass);
            ConfigureLighting();
            return root;
        }
        static void ConfigureLighting()
        {
            RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor=new Color(.65f,.75f,.87f);
            RenderSettings.ambientEquatorColor=new Color(.39f,.48f,.54f);
            RenderSettings.ambientGroundColor=new Color(.22f,.27f,.22f);
            RenderSettings.fog=true;RenderSettings.fogMode=FogMode.ExponentialSquared;
            RenderSettings.fogColor=new Color(.59f,.70f,.76f);RenderSettings.fogDensity=.0013f;
            var sky=new Material(Shader.Find("Skybox/Procedural"));sky.name="园区晴空";
            sky.SetFloat("_SunSize",.025f);sky.SetFloat("_AtmosphereThickness",1.05f);sky.SetFloat("_Exposure",1.05f);
            sky.SetColor("_SkyTint",new Color(.67f,.77f,.84f));
            sky.SetColor("_GroundColor",new Color(.57f,.65f,.59f));RenderSettings.skybox=sky;
            var sun=new GameObject("阳光");sun.transform.rotation=Quaternion.Euler(48,-32,0);
            var light=sun.AddComponent<Light>();light.type=LightType.Directional;light.color=new Color(1,.97f,.91f);light.intensity=1.28f;
            light.shadows=LightShadows.Soft;light.shadowStrength=.78f;light.shadowBias=.025f;light.shadowNormalBias=.15f;
            RenderSettings.sun=light;RenderSettings.reflectionIntensity=.8f;
            QualitySettings.shadowDistance=340;QualitySettings.shadowCascades=4;
        }
        static void BuildWorkshop(Transform parent,Vector3 position,int index)
        {
            var hall=Group(new[]{"01 成型车间","02 加工车间","03 装配车间","04 检测车间"}[index],parent,position);
            var selection=hall.gameObject.AddComponent<FactorySelectable>();selection.lineIndex=index;
            Box("车间地坪",hall,new Vector3(0,.18f,0),new Vector3(49,.32f,31),C("车间地面","#CBD5D0"),true);
            var shell=Group("外墙与屋顶",hall,Vector3.zero);
            var facade=C("工业外墙","#DCE3E6",.18f,.48f);var band=C("蓝色檐口","#BAC8D0",.52f,.60f);
            Box("北墙",shell,new Vector3(0,4.8f,15),new Vector3(48,9,.35f),facade,true);
            Box("西墙",shell,new Vector3(-24,4.8f,0),new Vector3(.35f,9,30),facade,true);
            Box("东墙",shell,new Vector3(24,4.8f,0),new Vector3(.35f,9,30),facade,true);
            Box("南墙左",shell,new Vector3(-14,4.8f,-15),new Vector3(20,9,.35f),facade,true);
            Box("南墙右",shell,new Vector3(14,4.8f,-15),new Vector3(20,9,.35f),facade,true);
            Box("南墙门头",shell,new Vector3(0,7.6f,-15),new Vector3(8,3.4f,.35f),facade,true);
            Box("卷帘门",shell,new Vector3(0,2.8f,-15.05f),new Vector3(7.8f,5.2f,.2f),C("卷帘门","#8799A8",.6f,.6f));
            Box("屋顶",shell,new Vector3(0,9.5f,0),new Vector3(49,.45f,31),C("屋面","#D7E0E4",.25f,.50f));
            foreach(float z in new[]{-15.35f,15.35f})
            {
                Box("蓝色腰线",shell,new Vector3(0,5.8f,z),new Vector3(48,.16f,.16f),band);
                Box("蓝色顶线",shell,new Vector3(0,8.95f,z),new Vector3(49,.2f,.25f),band);
                Box("连续玻璃窗带",shell,new Vector3(0,6.8f,z+.03f),new Vector3(47,1.3f,.09f),C("建筑玻璃","#476479",.35f,.82f));
                for(int k=0;k<11;k++)
                {
                    float x=-21+k*4.2f;
                    Box("长窗",shell,new Vector3(x,6.8f,z+.02f),new Vector3(3.4f,1.15f,.15f),C("建筑玻璃","#476479",.35f,.82f));
                    Box("窗框",shell,new Vector3(x,6.8f,z+.12f),new Vector3(.06f,1.3f,.07f),band);
                }
                for(int k=0;k<9;k++)Box("银灰立面分缝",shell,new Vector3(-23+k*5.75f,3.2f,z+.09f),new Vector3(.08f,5.25f,.07f),C("立面结构铝","#AAB8C1",.6f,.55f));
                Box("金属勒脚",shell,new Vector3(0,.8f,z+.09f),new Vector3(48,.8f,.12f),C("勒脚","#758792",.2f,.4f));
            }
            foreach(float x in new[]{-24.22f,24.22f})
            {
                Box("侧面窗带",shell,new Vector3(x,6.8f,0),new Vector3(.08f,1.3f,29),C("建筑玻璃","#476479",.35f,.82f));
                Box("侧面银灰檐口",shell,new Vector3(x,8.95f,0),new Vector3(.16f,.2f,31),band);
                for(int k=0;k<7;k++)Box("侧面金属竖缝",shell,new Vector3(x,3.2f,-14+k*4.65f),new Vector3(.06f,5.25f,.08f),C("立面结构铝","#AAB8C1",.6f,.55f));
            }
            Box("入口悬挑雨棚",shell,new Vector3(0,5.8f,-16.4f),new Vector3(9,.18f,2.8f),band);
            for(int x=0;x<8;x++)for(int z=0;z<4;z++)
            {
                var panel=Box("屋顶光伏",shell,new Vector3(-20.2f+x*5.75f,10.00f,-11.1f+z*7.4f),new Vector3(4.9f,.09f,5.5f),C("光伏面板","#173C60",.48f,.74f));
                panel.transform.localRotation=Quaternion.Euler(-5,0,0);
                Box("光伏支架",shell,new Vector3(-20.2f+x*5.75f,9.85f,-11.1f+z*7.4f),new Vector3(3.8f,.18f,.13f),C("立面结构铝","#AAB8C1",.6f,.55f));
            }
            BuildRoofDetails(shell);
            var blueGlow=C("建筑蓝色光带","#398DD2",.2f,.55f);blueGlow.EnableKeyword("_EMISSION");blueGlow.SetColor("_EmissionColor",new Color(.015f,.16f,.48f));
            foreach(float z in new[]{-15.33f,15.33f})Box("建筑底部科技光带",shell,new Vector3(0,.49f,z),new Vector3(47,.09f,.09f),blueGlow);
            foreach(float x in new[]{-24.28f,24.28f})Box("建筑侧边科技光带",shell,new Vector3(x,.49f,0),new Vector3(.09f,.09f,29),blueGlow);
            foreach(float x in new[]{-24.35f,24.35f})for(int k=0;k<3;k++)
            {
                float z=-9+k*9;
                Box("侧面装卸卷帘门",shell,new Vector3(x,2.4f,z),new Vector3(.12f,4.2f,4.2f),C("卷帘门","#8799A8",.6f,.6f));
                Box("装卸口雨棚",shell,new Vector3(x,4.7f,z),new Vector3(1.8f,.13f,4.6f),band);
            }
            var interior=Group("车间设备",hall,Vector3.zero);
            for(int k=0;k<4;k++)Machine(interior,new Vector3(-16+k*10,0,3),index,k);
            Box("安全通道",interior,new Vector3(0,.37f,-7),new Vector3(45,.01f,3),C("安全通道绿","#579A84"));
            for(int k=0;k<9;k++)Box("通道指示",interior,new Vector3(-20+k*5,.4f,-7),new Vector3(1,.02f,.16f),C("道路标线","#E8EADB"));
            for(int k=0;k<3;k++)
            {
                Box("物料托盘",interior,new Vector3(-15+k*8,.55f,11),new Vector3(4,.35f,2.6f),C("托盘木色","#A68157"));
                Box("待加工料箱",interior,new Vector3(-15+k*8,1.3f,11),new Vector3(3.3f,1.2f,2.3f),C("料箱","#829AA2"));
            }
            var mark=Group("设备状态光环",hall,new Vector3(0,.43f,0));
            for(int side=0;side<4;side++)
            {
                Vector3 p=side<2?new Vector3(0,0,side==0?-16:16):new Vector3(side==2?-25:25,0,0);
                Vector3 size=side<2?new Vector3(50,.06f,.22f):new Vector3(.22f,.06f,32);
                Box("状态轮廓",mark,p,size,C("状态青色","#39BDAE",.1f));
            }
        }
        static void Machine(Transform parent,Vector3 pos,int line,int number)
        {
            var machine=Group("工作站 "+(number+1),parent,pos);
            var selectable=machine.gameObject.AddComponent<FactorySelectable>();selectable.lineIndex=line;selectable.isEquipment=true;
            var steel=C("机床灰","#93ADB0",.35f);var blue=C("机床蓝","#347B91",.4f);
            Box("设备底座",machine,new Vector3(0,.75f,0),new Vector3(6,1,4),steel,true);
            Box("设备机身",machine,new Vector3(-1,2.8f,.7f),new Vector3(3.5f,3.2f,2.5f),blue,true);
            Box("玻璃观察窗",machine,new Vector3(-1,3,-.6f),new Vector3(2.4f,1.7f,.16f),C("机床观察窗","#244454",.5f,.8f));
            Box("设备控制台",machine,new Vector3(2.1f,2.3f,0),new Vector3(1.1f,2,1.3f),steel,true);
            Box("显示屏",machine,new Vector3(2.1f,2.65f,-.7f),new Vector3(.8f,.55f,.08f),C("显示屏绿","#4DCFB2"));
            Cylinder("警示灯",machine,new Vector3(2.1f,3.6f,0),.15f,.5f,C("状态青色","#39BDAE"));
            var actuator=Box("往复组件",machine,new Vector3(-1,4.7f,.7f),new Vector3(1,.6f,1),steel);
            var motion=machine.gameObject.AddComponent<FactoryMachineMotion>();motion.lineIndex=line;motion.actuator=actuator.transform;
            if(number==1)
            {
                Box("输送线",machine,new Vector3(6.5f,1.05f,-3.3f),new Vector3(11,.45f,1.4f),C("输送带","#40565F",.2f));
                for(int k=0;k<5;k++)Cylinder("滚轴",machine,new Vector3(2+k*2,1.28f,-3.3f),.22f,1.3f,steel).transform.localRotation=Quaternion.Euler(90,0,0);
                var part=Box("输送零件",machine,new Vector3(2,1.6f,-3.3f),new Vector3(.7f,.5f,.7f),C("零件金属","#BDC9C9",.8f));
                var transport=part.AddComponent<FactoryMachineMotion>();transport.lineIndex=line;transport.actuator=part.transform;transport.conveyor=true;
            }
        }
        static void BuildOffice(Transform parent,Vector3 pos)
        {
            var o=Group("研发办公楼",parent,pos);var wall=C("办公外墙","#DEE5E6",.15f,.45f);
            Box("办公楼体",o,new Vector3(0,6,0),new Vector3(27,12,13),wall);
            Box("入口雨棚",o,new Vector3(0,3,-8),new Vector3(8,.22f,4),C("立面结构铝","#AAB8C1",.6f,.55f));
            for(int level=0;level<3;level++)foreach(float z in new[]{-6.6f,6.6f})
                Box("办公连续玻璃幕墙",o,new Vector3(0,2.5f+level*3.5f,z),new Vector3(26,2.4f,.08f),C("建筑玻璃","#476479",.35f,.82f));
            for(int level=0;level<3;level++)for(int i=0;i<7;i++)
            {
                Box("办公窗",o,new Vector3(-11+i*3.7f,2.5f+level*3.5f,-6.55f),new Vector3(2.7f,2,.15f),C("建筑玻璃","#537889",.45f,.8f));
                Box("办公窗北",o,new Vector3(-11+i*3.7f,2.5f+level*3.5f,6.55f),new Vector3(2.7f,2,.15f),C("建筑玻璃","#537889",.45f,.8f));
            }
            Box("办公顶",o,new Vector3(0,12.25f,0),new Vector3(28,.5f,14),C("仓储屋顶","#708E99"));
        }
        static void Tree(Transform parent,Vector3 pos)
        {
            FactoryVegetationBuilder.Tree(parent,pos,7.5f,Mathf.RoundToInt(pos.x*23+pos.z*11),Mathf.Abs(pos.x)>75);
        }
        static void BuildRoofDetails(Transform shell)
        {
            var steel=C("屋顶设施银灰","#A5B5BF",.55f,.5f);var glass=C("屋顶采光玻璃","#82ABBC",.25f,.8f);
            foreach(float z in new[]{-15.4f,15.4f})Box("屋顶女儿墙",shell,new Vector3(0,9.83f,z),new Vector3(49,.48f,.17f),steel);
            foreach(float x in new[]{-24.4f,24.4f})Box("屋顶收边",shell,new Vector3(x,9.83f,0),new Vector3(.17f,.48f,31),steel);
            for(int k=0;k<4;k++)
            {
                float x=-17+k*11.3f;
                Box("采光天窗基座",shell,new Vector3(x,9.92f,0),new Vector3(5.4f,.35f,1.8f),steel);
                var window=Box("天窗",shell,new Vector3(x,10.13f,0),new Vector3(5.1f,.09f,1.6f),glass);
                window.transform.localRotation=Quaternion.Euler(-12,0,0);
                Box("屋顶空调机组",shell,new Vector3(x,10.14f,14),new Vector3(2,.8f,1.2f),steel);
                for(int rib=0;rib<4;rib++)Box("空调百叶",shell,new Vector3(x-.65f+rib*.42f,10.56f,14),new Vector3(.1f,.03f,1),C("机组风口","#536571",.2f));
            }
            foreach(float x in new[]{-24.45f,24.45f})foreach(float z in new[]{-13.5f,0f,13.5f})
                Cylinder("厂房雨水落管",shell,new Vector3(x,4.5f,z),.095f,8.7f,steel);
        }
        static void BuildFence(Transform parent,Vector3 start,Vector3 end)
        {
            Vector3 direction=(end-start).normalized;float length=Vector3.Distance(start,end);var metal=C("围栏","#70848A",.55f);
            for(float d=0;d<=length;d+=3.2f)Box("围栏立杆",parent,start+direction*d+Vector3.up*.85f,new Vector3(.075f,1.7f,.075f),metal);
            for(int i=0;i<3;i++)
            {
                var rail=Box("通透围栏横杆",parent,(start+end)*.5f+Vector3.up*(.35f+i*.55f),new Vector3(length,.045f,.045f),metal);
                rail.transform.localRotation=Quaternion.FromToRotation(Vector3.right,direction);
            }
        }
        static void StreetLamp(Transform parent,Vector3 pos)
        {
            Cylinder("路灯底座",parent,pos+Vector3.up*.13f,.19f,.26f,C("路灯金属","#687C8B",.65f,.6f));
            Cylinder("路灯杆",parent,pos+Vector3.up*3,.07f,6,C("路灯金属","#687C8B",.65f,.6f));
            Box("路灯臂",parent,pos+new Vector3(.6f,6,0),new Vector3(1.3f,.12f,.12f),C("路灯金属","#687C8B",.65f,.6f));
            Box("灯罩",parent,pos+new Vector3(1.1f,5.95f,0),new Vector3(1.05f,.12f,.42f),C("灯罩","#DFEBE4",.1f,.6f));
        }
        static void BuildCampusDetails(Transform parent,Material paving,Material grass)
        {
            var curb=C("路缘石","#DDE2DD",0,.25f);
            foreach(float z in new[]{-40.6f,-51.4f,36.8f,47.1f})
                Box("主路路缘",parent,new Vector3(0,.22f,z),new Vector3(151,.28f,.25f),curb);
            foreach(float x in new[]{-72.4f,-63.6f,61.6f,70.4f})
                Box("环路路缘",parent,new Vector3(x,.22f,-1),new Vector3(.25f,.28f,84),curb);
            var planter=C("绿化花池","#9AA9A5",.12f,.35f);
            var shrubs=C("园区灌木","#5D855D");
            foreach(float x in new[]{-76f,75f})for(int i=0;i<5;i++)
            {
                float z=-32+i*17;
                Box("线性花池",parent,new Vector3(x,.22f,z),new Vector3(2.2f,.35f,8),planter);
                Box("整形灌木",parent,new Vector3(x,.64f,z),new Vector3(1.85f,.7f,7.65f),shrubs);
            }
            for(int i=0;i<8;i++)
            {
                float x=-65+i*16;
                Box("透水绿化铺装",parent,new Vector3(x,.12f,-55.5f),new Vector3(5,.08f,3.5f),paving);
                Box("街边绿化带",parent,new Vector3(x,.18f,-58.3f),new Vector3(6,.12f,1.8f),grass);
            }
            for(int i=0;i<4;i++)
            {
                float x=-48+i*27;
                Box("休憩长椅",parent,new Vector3(x,.65f,-57.6f),new Vector3(2.8f,.16f,.6f),C("景观木色","#A29174"));
                foreach(float dx in new[]{-.95f,.95f})Box("长椅支架",parent,new Vector3(x+dx,.35f,-57.6f),new Vector3(.12f,.6f,.5f),C("路灯金属","#687C8B",.65f,.6f));
            }
            for(int i=0;i<5;i++)
                Box("入口铺装分缝",parent,new Vector3(58,.24f,-53+i*.55f),new Vector3(12,.015f,.035f),C("铺装分缝","#9AA9A5"));
            var truck=Group("园区物流车辆",parent,new Vector3(70,0,22));
            Box("物流车货箱",truck,new Vector3(0,1.6f,0),new Vector3(2.7f,2.9f,6.4f),C("物流货箱","#B6CDD7",.25f,.5f));
            Box("物流车驾驶室",truck,new Vector3(0,1.1f,-4.4f),new Vector3(2.6f,2,2.2f),C("物流蓝","#367AA3",.3f,.6f));
            Box("物流车前窗",truck,new Vector3(0,1.5f,-5.54f),new Vector3(2.2f,.8f,.05f),C("建筑玻璃","#476479",.35f,.82f));
            foreach(float x in new[]{-1.33f,1.33f})foreach(float z in new[]{-4.4f,-1.7f,2.1f})
                Cylinder("物流车轮",truck,new Vector3(x,.55f,z),.45f,.3f,C("轮胎","#2D3C40")).transform.localRotation=Quaternion.Euler(0,0,90);
        }
        static void Car(Transform parent,Vector3 pos,int index)
        {
            var car=Group("停放车辆",parent,pos);var body=C("车辆"+(index%3),new[]{"#DFE5E4","#385D70","#849998"}[index%3],.45f,.6f);
            Box("车身",car,new Vector3(0,.7f,0),new Vector3(2,.75f,3.8f),body);
            Box("车顶",car,new Vector3(0,1.25f,0),new Vector3(1.7f,.65f,2),C("建筑玻璃","#537889",.45f,.8f));
            foreach(float x in new[]{-1f,1f})foreach(float z in new[]{-1.1f,1.1f})
                Cylinder("车轮",car,new Vector3(x,.45f,z),.36f,.2f,C("轮胎","#2D3C40")).transform.localRotation=Quaternion.Euler(0,0,90);
        }
    }
}
