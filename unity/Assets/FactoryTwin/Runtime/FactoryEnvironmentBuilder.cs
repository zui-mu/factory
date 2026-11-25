using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Zhiyin.FactoryTwin
{
    /// <summary>Editable landscape meshes. Environment stays outside the selectable campus.</summary>
    public static class FactoryEnvironmentBuilder
    {
        static Material Surface(string name, string hex, float metallic = 0, float smoothness = .3f)
        {
            Color color; ColorUtility.TryParseHtmlString(hex, out color);
            var material = new Material(Shader.Find("Standard")) { name = name, color = color };
            material.SetFloat("_Metallic", metallic); material.SetFloat("_Glossiness", smoothness);
            material.enableInstancing = true;
            return material;
        }

        static GameObject MeshObject(string name, Transform parent, Mesh mesh, Material material, bool shadow = true)
        {
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(parent, false); go.GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = go.GetComponent<MeshRenderer>(); renderer.sharedMaterial = material;
            renderer.shadowCastingMode = shadow ? ShadowCastingMode.On : ShadowCastingMode.Off;
            renderer.receiveShadows = shadow;
            return go;
        }

        static float LakeRadius(float x, float z)
        {
            float a = (x - 238) / 137, b = (z - 26) / 205;
            return Mathf.Sqrt(a * a + b * b);
        }

        public static float Height(float x, float z)
        {
            float near = Mathf.Max(Mathf.Abs(x) / 94, Mathf.Abs(z) / 73);
            float plain = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(1, 2.9f, near));
            float low = -1.45f + (Mathf.PerlinNoise(x * .006f + 31, z * .006f + 18) - .5f) * 5;
            float mountainDistance = Mathf.Sqrt(x * x + (z + 35) * (z + 35));
            float mountains = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(310, 590, mountainDistance));
            float ridge = Mathf.PerlinNoise(x * .0037f + 4, z * .0037f + 22);
            float detail = Mathf.PerlinNoise(x * .012f + 8, z * .012f + 17);
            float height = Mathf.Lerp(-.28f, low, plain) + mountains * (24 + ridge * 135 + detail * 25);
            // Low foothills enter the existing elevated camera view; higher ridges remain behind them.
            float north = Mathf.SmoothStep(0,1,Mathf.InverseLerp(80,160,z));
            float foothill = Mathf.Exp(-Mathf.Pow((z-195)/165,2)-Mathf.Pow(x/430,2));
            height += north*foothill*(10+Mathf.PerlinNoise(x*.014f+11,z*.012f+7)*40);
            float west = Mathf.SmoothStep(0,1,Mathf.InverseLerp(105,250,-x));
            height += west*Mathf.Exp(-Mathf.Pow((x+260)/190,2)-Mathf.Pow((z-110)/270,2))*24;
            float industrial=Mathf.Max(Mathf.Abs((x+35)/126),Mathf.Abs((z-153)/96));
            if(industrial<1.45f)height=Mathf.Lerp(-.28f,height,Mathf.SmoothStep(0,1,Mathf.InverseLerp(1,1.45f,industrial)));
            float lake = LakeRadius(x, z);
            if (lake < 1.06f) height = Mathf.Lerp(-2.3f, height, Mathf.SmoothStep(0, 1, Mathf.InverseLerp(.95f, 1.06f, lake)));
            return height;
        }

        public static GameObject Build()
        {
            var root = new GameObject("生态景观 · 远山树林与湖泊");
            var groundMaterial = new Material(Shader.Find("Zhiyin/Landscape")) { name = "山林地表 · 顶点色" };
            // Small tiles keep editable meshes within 16-bit limits and allow ordinary frustum culling.
            const int resolution = 45;
            for (int tz = -2; tz < 2; tz++) for (int tx = -2; tx < 2; tx++)
            {
                float left = tx * 450, bottom = tz * 450;
                var vertices = new Vector3[(resolution + 1) * (resolution + 1)];
                var colors = new Color[vertices.Length]; var triangles = new int[resolution * resolution * 6];
                for (int z = 0; z <= resolution; z++) for (int x = 0; x <= resolution; x++)
                {
                    float px = left + x * 10, pz = bottom + z * 10;
                    float h = Height(px, pz); int i = z * (resolution + 1) + x;
                    vertices[i] = new Vector3(px, h, pz);
                    float variation = Mathf.PerlinNoise(px * .014f + 10, pz * .014f + 10);
                    Color green = Color.Lerp(new Color(.22f,.33f,.19f), new Color(.40f,.48f,.27f), variation);
                    float far = Mathf.Clamp01((Mathf.Sqrt(px * px + pz * pz) - 300) / 500);
                    colors[i] = Color.Lerp(green, new Color(.34f,.47f,.48f), far * .65f);
                    float shore = LakeRadius(px,pz);
                    if (shore > .95f && shore < 1.1f) colors[i] = new Color(.65f,.68f,.53f);
                    if (x < resolution && z < resolution)
                    {
                        int q = (z * resolution + x) * 6;
                        triangles[q] = i; triangles[q+1] = i+resolution+1; triangles[q+2] = i+1;
                        triangles[q+3] = i+1; triangles[q+4] = i+resolution+1; triangles[q+5] = i+resolution+2;
                    }
                }
                var mesh = new Mesh { name = "Landscape_"+tx+"_"+tz, vertices = vertices, colors = colors, triangles = triangles };
                mesh.RecalculateNormals(); mesh.RecalculateBounds();
                MeshObject("山林地形 " + tx + " / " + tz, root.transform, mesh, groundMaterial);
            }

            BuildLake(root.transform);
            BuildForest(root.transform);
            BuildPromenade(root.transform);
            BuildIndustrialContext(root.transform);
            return root;
        }

        static void BuildLake(Transform parent)
        {
            const int segments = 160;
            var vertices = new Vector3[segments+1]; var triangles = new int[segments*3];
            vertices[0] = new Vector3(238,-.45f,26);
            for(int i=0;i<segments;i++)
            {
                float a = i * Mathf.PI * 2 / segments;
                float shape = .995f + Mathf.Sin(a*3+.4f)*.008f + Mathf.Sin(a*7)*.004f;
                vertices[i+1] = new Vector3(238+Mathf.Cos(a)*137*shape,-.45f,26+Mathf.Sin(a)*205*shape);
                triangles[i*3]=0;triangles[i*3+1]=(i+1)%segments+1;triangles[i*3+2]=i+1;
            }
            var mesh = new Mesh { name="EcologicalLake",vertices=vertices,triangles=triangles };
            mesh.RecalculateNormals();mesh.RecalculateBounds();
            var material = new Material(Shader.Find("Zhiyin/Lake")) { name="湖水 · 天光与细波" };
            material.SetColor("_DeepColor",new Color(.07f,.20f,.26f));
            material.SetColor("_SkyColor",new Color(.43f,.65f,.74f));
            MeshObject("生态湖 · 动态水面",parent,mesh,material,false);
        }

        // Trees are combined by colour, avoiding hundreds of individual forest draw calls.
        static void BuildForest(Transform parent)
        {
            if(FactoryVegetationBuilder.Crown==null)FactoryVegetationBuilder.Prepare();
            var random = new System.Random(1042);
            var crowns = new List<CombineInstance>[5];
            var leaves = new List<CombineInstance>[5];
            for(int k=0;k<crowns.Length;k++){crowns[k]=new List<CombineInstance>();leaves[k]=new List<CombineInstance>();}
            var trunks = new List<CombineInstance>();
            for(int z=-345;z<=440;z+=12)for(int x=-380;x<=440;x+=12)
            {
                float px=x+(float)random.NextDouble()*10, pz=z+(float)random.NextDouble()*10;
                if(Mathf.Abs(px)<100&&Mathf.Abs(pz)<83)continue;
                if(px>-170&&px<87&&pz>62&&pz<255)continue;
                if(LakeRadius(px,pz)<1.13f)continue;
                if(pz>-153&&pz<-126&&px>-118&&px<112)continue;
                if(px>47&&px<69&&pz>-160&&pz<-57)continue;
                float distance = Mathf.Sqrt(px*px+pz*pz);
                if(distance>505)continue;
                if(distance>300&&random.NextDouble()<.55)continue;
                float cluster = Mathf.PerlinNoise(px*.015f+22,pz*.015f+14);
                if(cluster<.30f || (distance<175 && random.NextDouble()<.09))continue;
                bool slender=random.NextDouble()<.32;float height=10+(float)random.NextDouble()*6;
                float width=height*(slender?.32f:.69f);
                var center=new Vector3(px,Height(px,pz),pz);
                int palette=random.Next(5);
                Matrix4x4 transform=Matrix4x4.TRS(center,Quaternion.Euler(0,random.Next(360),0),new Vector3(width,height,width));
                crowns[palette].Add(new CombineInstance{mesh=slender?FactoryVegetationBuilder.SlenderCrown:FactoryVegetationBuilder.Crown,transform=transform});
                if(distance<320)leaves[palette].Add(new CombineInstance{mesh=slender?FactoryVegetationBuilder.SlenderLeaves:FactoryVegetationBuilder.Leaves,transform=transform});
                trunks.Add(new CombineInstance{mesh=FactoryVegetationBuilder.Stem,transform=transform});
            }
            for(int i=0;i<crowns.Length;i++)
            {
                var core=new Material(FactoryVegetationBuilder.CoreMaterial){name="林带绿 "+i};
                core.SetColor("_Color",Color.Lerp(new Color(.78f,.89f,.69f),Color.white,i/4f));
                Combine("林带树冠 "+i,parent,crowns[i],core);
                Combine("林带透光枝叶 "+i,parent,leaves[i],FactoryVegetationBuilder.LeafMaterial);
            }
            Combine("林带树干",parent,trunks,FactoryVegetationBuilder.StemMaterial);
        }

        static void Combine(string name,Transform parent,List<CombineInstance> source,Material material)
        {
            var mesh = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
            mesh.CombineMeshes(source.ToArray(),true,true);mesh.RecalculateBounds();
            MeshObject(name,parent,mesh,material);
        }

        static void BuildPromenade(Transform parent)
        {
            var material=Surface("园外步道","#B9C0B7");
            var road=Surface("接驳道路","#35434B");
            Block("园区入口接驳路",parent,new Vector3(58,-.03f,-101),new Vector3(8,.15f,88),road);
            Block("园外公共道路",parent,new Vector3(-5,-.08f,-143),new Vector3(214,.18f,13),road);
            var marking=Surface("园外道路标线","#DDE3DA");
            for(int k=-20;k<=19;k++)Block("园外虚线",parent,new Vector3(k*5,.025f,-143),new Vector3(2.5f,.012f,.15f),marking);
            Block("西侧林荫步道",parent,new Vector3(-91,-.03f,0),new Vector3(2.5f,.12f,144),material);
            Block("湖岸慢行步道",parent,new Vector3(93,-.03f,0),new Vector3(2.5f,.12f,144),material);
            Block("南侧绿道",parent,new Vector3(0,-.03f,-69),new Vector3(184,.12f,2.5f),material);
        }

        static void BuildIndustrialContext(Transform parent)
        {
            var root=new GameObject("参考风格 · 配套工业园").transform;root.SetParent(parent,false);
            var pavement=Surface("工业园广场","#9BA9AB",0,.25f);var road=Surface("工业园道路","#35434B",.03f,.28f);
            var facade=Surface("配套厂房白墙","#CBD6DD",.15f,.45f);var roof=Surface("配套蓝色屋顶","#3B84AF",.28f,.5f);
            roof.shader=Shader.Find("Zhiyin/Industrial Surface");roof.SetFloat("_RibScale",2.4f);roof.SetFloat("_RibStrength",.14f);
            var window=Surface("配套厂房玻璃","#3A5B70",.35f,.8f);var edge=Surface("配套建筑铝","#AABFCB",.5f,.55f);
            Block("后区硬质场地",root,new Vector3(-38,-.18f,153),new Vector3(226,.18f,174),pavement);
            foreach(float z in new[]{77f,151f,225f})Block("后区横向道路",root,new Vector3(-38,-.04f,z),new Vector3(226,.12f,10),road);
            foreach(float x in new[]{-146f,-73f,0f,73f})Block("后区纵向道路",root,new Vector3(x,-.04f,151),new Vector3(8,.12f,156),road);
            var marker=Surface("后区道路标线","#DDE3DA");
            foreach(float z in new[]{77f,151f,225f})for(int k=-28;k<13;k++)Block("后区道路虚线",root,new Vector3(k*5,.025f,z),new Vector3(2.3f,.015f,.13f),marker);
            for(int row=0;row<2;row++)for(int column=0;column<3;column++)
            {
                Vector3 center=new Vector3(-110+column*73,0,112+row*74);
                var hall=new GameObject("配套蓝顶厂房 "+row+"-"+column).transform;hall.SetParent(root,false);hall.localPosition=center;
                Block("配套厂房主体",hall,new Vector3(0,3.4f,0),new Vector3(50,6.8f,35),facade);
                Block("蓝色金属屋面",hall,new Vector3(0,7.03f,0),new Vector3(51,.30f,36),roof);
                for(int i=0;i<10;i++)
                {
                    Block("侧窗",hall,new Vector3(-22+i*4.9f,4.9f,-17.57f),new Vector3(2.8f,1.3f,.12f),window);
                    Block("蓝顶采光带",hall,new Vector3(-22+i*4.9f,7.24f,0),new Vector3(.55f,.09f,30),edge);
                    Block("辅助厂房立面竖缝",hall,new Vector3(-22+i*4.9f,3.2f,-17.61f),new Vector3(.09f,6,.04f),edge);
                }
                Block("配套厂房装卸门",hall,new Vector3(0,2.35f,-17.58f),new Vector3(5,4.7f,.15f),window);
                for(int k=0;k<5;k++)FactoryVegetationBuilder.Tree(root,center+new Vector3(-24+k*12,0,-25),7.5f,row*103+column*17+k);
            }
            // Distant industrial blocks provide depth rather than a bare terrain background.
            var random=new System.Random(903);var city=Surface("远处建筑","#8EA7B4",.1f,.3f);
            for(int row=0;row<2;row++)for(int i=0;i<11;i++)
            {
                float x=-360+i*64,z=320+row*95;float h=12+random.Next(14),width=38+random.Next(17),depth=26+random.Next(17);
                float ground=Height(x,z);
                var block=new GameObject("远景工业建筑 "+row+"-"+i).transform;block.SetParent(root,false);block.localPosition=new Vector3(x,ground,z);
                Block("远景建筑主体",block,new Vector3(0,h*.5f,0),new Vector3(width,h,depth),city);
                Block("远景建筑屋面",block,new Vector3(0,h+.15f,0),new Vector3(width+.5f,.3f,depth+.5f),roof);
                foreach(float side in new[]{-1f,1f})for(float level=3;level<h-1;level+=3.5f)
                    Block("远景建筑窗带",block,new Vector3(0,level,side*(depth*.5f+.08f)),new Vector3(width-2,1.7f,.08f),window);
                for(float column=-width*.5f+1;column<width*.5f;column+=6)
                    Block("远景建筑竖框",block,new Vector3(column,h*.5f,-depth*.5f-.15f),new Vector3(.2f,h,.08f),edge);
            }
        }

        static void Block(string name,Transform parent,Vector3 position,Vector3 size,Material material)
        {
            BlockObject(name,parent,position,size,material);
        }
        static GameObject BlockObject(string name,Transform parent,Vector3 position,Vector3 size,Material material)
        {
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=name;go.transform.SetParent(parent,false);
            go.transform.localPosition=position;go.transform.localScale=size;go.GetComponent<Renderer>().sharedMaterial=material;
            Object.DestroyImmediate(go.GetComponent<Collider>());
            return go;
        }
    }
}
