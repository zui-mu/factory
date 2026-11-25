using System;
using System.Collections.Generic;
using UnityEngine;

namespace Zhiyin.FactoryTwin
{
    /// <summary>Original mesh trees with cutout leaf clusters. Shared by campus and landscape.</summary>
    public static class FactoryVegetationBuilder
    {
        public static Mesh Crown, Leaves, SlenderCrown, SlenderLeaves, Stem;
        public static Texture2D LeafTexture;
        public static Material CoreMaterial, LeafMaterial, StemMaterial;

        public static void Prepare()
        {
            LeafTexture=CreateLeafTexture();
            CoreMaterial=new Material(Shader.Find("Zhiyin/Vegetation")){name="树林 · 细叶冠层"};
            CoreMaterial.SetColor("_Color",Color.white);
            LeafMaterial=new Material(Shader.Find("Zhiyin/Leaves")){name="树林 · 透光枝叶",mainTexture=LeafTexture};
            LeafMaterial.SetColor("_Color",Color.white);LeafMaterial.SetFloat("_Cutoff",.35f);
            StemMaterial=new Material(Shader.Find("Standard")){name="树林 · 木质树干",color=new Color(.34f,.30f,.23f)};
            foreach(var m in new[]{CoreMaterial,LeafMaterial,StemMaterial})m.enableInstancing=true;
            MakeCanopy(false,out Crown,out Leaves);MakeCanopy(true,out SlenderCrown,out SlenderLeaves);
            Stem=MakeStem();
        }

        public static void Tree(Transform parent,Vector3 position,float height,int seed,bool slender=false)
        {
            if(Crown==null)Prepare();
            var random=new System.Random(seed);float width=height*(slender?.32f:.69f);
            var root=new GameObject("园区景观树").transform;root.SetParent(parent,false);root.localPosition=position;
            root.localRotation=Quaternion.Euler(0,random.Next(360),0);
            var core=MeshPart("细叶树冠",root,slender?SlenderCrown:Crown,CoreMaterial);
            var leaves=MeshPart("枝叶簇",root,slender?SlenderLeaves:Leaves,LeafMaterial);
            core.transform.localScale=leaves.transform.localScale=new Vector3(width,height,width);
            var stem=MeshPart("树干分枝",root,Stem,StemMaterial);stem.transform.localScale=new Vector3(width,height,width);
        }

        static GameObject MeshPart(string name,Transform parent,Mesh mesh,Material material)
        {
            var go=new GameObject(name,typeof(MeshFilter),typeof(MeshRenderer));go.transform.SetParent(parent,false);
            go.GetComponent<MeshFilter>().sharedMesh=mesh;go.GetComponent<Renderer>().sharedMaterial=material;return go;
        }

        static Mesh MakeStem()
        {
            var vertices=new List<Vector3>();var triangles=new List<int>();
            Branch(vertices,triangles,Vector3.zero,new Vector3(0,.82f,0),.038f,.010f);
            for(int i=0;i<5;i++)
            {
                float angle=i*2.4f;Vector3 tip=new Vector3(Mathf.Cos(angle)*.31f,.64f+i*.035f,Mathf.Sin(angle)*.31f);
                Branch(vertices,triangles,new Vector3(0,.35f+i*.07f,0),tip,.018f,.004f);
            }
            var mesh=new Mesh{name="VegetationStem",vertices=vertices.ToArray(),triangles=triangles.ToArray()};mesh.RecalculateNormals();return mesh;
        }

        static void Branch(List<Vector3> v,List<int> t,Vector3 a,Vector3 b,float ra,float rb)
        {
            Vector3 direction=(b-a).normalized;Vector3 right=Vector3.Cross(direction,Vector3.forward).normalized;
            Vector3 up=Vector3.Cross(direction,right);int start=v.Count;
            for(int j=0;j<2;j++)for(int i=0;i<6;i++)
            {
                float angle=i*Mathf.PI/3;v.Add((j==0?a:b)+(right*Mathf.Cos(angle)+up*Mathf.Sin(angle))*(j==0?ra:rb));
            }
            for(int i=0;i<6;i++){int next=(i+1)%6;t.AddRange(new[]{start+i,start+next,start+6+i,start+next,start+6+next,start+6+i});}
        }

        static void MakeCanopy(bool slender,out Mesh core,out Mesh leaf)
        {
            var random=new System.Random(slender?1906:1905);
            var v=new List<Vector3>();var t=new List<int>();var colors=new List<Color>();
            int lobes=slender?9:8;
            for(int l=0;l<lobes;l++)
            {
                float a=l*2.4f;
                Vector3 center=slender?new Vector3(Mathf.Cos(a)*.16f,.43f+l*.060f,Mathf.Sin(a)*.16f)
                    :new Vector3(Mathf.Cos(a)*.22f,.60f+l*.025f,Mathf.Sin(a)*.22f);
                Vector3 scale=slender?new Vector3(.48f,.25f,.48f):new Vector3(.53f,.30f,.53f);
                int start=v.Count;const int rings=6,segments=11;
                for(int y=0;y<=rings;y++)for(int x=0;x<=segments;x++)
                {
                    float theta=x*Mathf.PI*2/segments,phi=y*Mathf.PI/rings;
                    float r=.5f*(1+Mathf.Sin(theta*5+phi*3+l)*.16f+Mathf.Sin(theta*9-phi*4)*.065f);
                    Vector3 n=new Vector3(Mathf.Sin(phi)*Mathf.Cos(theta),Mathf.Cos(phi),Mathf.Sin(phi)*Mathf.Sin(theta));
                    v.Add(center+Vector3.Scale(n,scale)*r);
                    float green=.76f+(float)random.NextDouble()*.35f;colors.Add(new Color(.32f*green,.50f*green,.21f*green));
                    if(y<rings&&x<segments)
                    {
                        int k=start+y*(segments+1)+x;
                        t.AddRange(new[]{k,k+1,k+segments+1,k+1,k+segments+2,k+segments+1});
                    }
                }
            }
            core=new Mesh{name=slender?"VegetationSlenderCore":"VegetationBroadCore",vertices=v.ToArray(),colors=colors.ToArray(),triangles=t.ToArray()};core.RecalculateNormals();
            v.Clear();t.Clear();colors.Clear();var uv=new List<Vector2>();
            int cards=slender?38:48;
            for(int i=0;i<cards;i++)
            {
                float angle=i*2.39996f;float y=(float)random.NextDouble();float radius=.24f+Mathf.Sin(y*Mathf.PI)*.18f;
                Vector3 center=new Vector3(Mathf.Cos(angle)*radius,.48f+y*.45f,Mathf.Sin(angle)*radius);
                Vector3 normal=new Vector3(Mathf.Cos(angle),.4f+Mathf.Sin(y*Mathf.PI)*.8f,Mathf.Sin(angle)).normalized;
                if(i%5==0)normal=Vector3.up;
                Vector3 right=Vector3.Cross(normal,Vector3.forward).normalized;if(right.sqrMagnitude<.1f)right=Vector3.right;
                Vector3 up=Vector3.Cross(normal,right);float size=.16f+(float)random.NextDouble()*.13f;int start=v.Count;
                v.Add(center-right*size-up*size*.55f);v.Add(center-right*size+up*size*.55f);
                v.Add(center+right*size+up*size*.55f);v.Add(center+right*size-up*size*.55f);
                uv.AddRange(new[]{Vector2.zero,Vector2.up,Vector2.one,Vector2.right});
                float shade=.77f+(float)random.NextDouble()*.28f;
                for(int k=0;k<4;k++)colors.Add(new Color(.64f*shade,.79f*shade,.45f*shade));
                t.AddRange(new[]{start,start+1,start+2,start,start+2,start+3});
            }
            leaf=new Mesh{name=slender?"VegetationSlenderLeaves":"VegetationBroadLeaves",vertices=v.ToArray(),colors=colors.ToArray(),uv=uv.ToArray(),triangles=t.ToArray()};leaf.RecalculateNormals();
        }

        static Texture2D CreateLeafTexture()
        {
            const int size=192;var pixels=new Color[size*size];var random=new System.Random(1802);
            for(int leaf=0;leaf<94;leaf++)
            {
                float angle=(float)random.NextDouble()*Mathf.PI*2,radius=Mathf.Sqrt((float)random.NextDouble())*.39f;
                float cx=.5f+Mathf.Cos(angle)*radius,cy=.5f+Mathf.Sin(angle)*radius;
                float rot=(float)random.NextDouble()*Mathf.PI,rx=.022f+(float)random.NextDouble()*.026f,ry=rx*1.8f;
                float shade=.60f+(float)random.NextDouble()*.42f;
                int extent=Mathf.CeilToInt(ry*size);
                for(int y=Mathf.Max(0,(int)(cy*size)-extent);y<Mathf.Min(size,(int)(cy*size)+extent+1);y++)
                    for(int x=Mathf.Max(0,(int)(cx*size)-extent);x<Mathf.Min(size,(int)(cx*size)+extent+1);x++)
                    {
                        float dx=x/(float)size-cx,dy=y/(float)size-cy;
                        float px=(dx*Mathf.Cos(rot)+dy*Mathf.Sin(rot))/rx,py=(-dx*Mathf.Sin(rot)+dy*Mathf.Cos(rot))/ry;
                        float d=px*px+py*py;if(d>1)continue;
                        float vein=Mathf.Abs(px)<.07f?1.16f:1;float light=(1-d*.25f)*shade*vein;
                        pixels[y*size+x]=new Color(.35f*light,.59f*light,.17f*light,Mathf.Clamp01((1-d)*12));
                    }
            }
            var texture=new Texture2D(size,size,TextureFormat.RGBA32,true){name="OriginalLeafClusters",wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Trilinear,anisoLevel=2};
            texture.SetPixels(pixels);texture.Apply();return texture;
        }
    }
}
