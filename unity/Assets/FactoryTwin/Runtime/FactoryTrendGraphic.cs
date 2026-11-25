using UnityEngine;
using UnityEngine.UI;
namespace Zhiyin.FactoryTwin
{
    public class FactoryTrendGraphic : MaskableGraphic
    {
        public float[] points=new float[0];
        public Color lineColor=new Color(.27f,.86f,.80f);
        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();Rect r=rectTransform.rect;
            for(int i=0;i<4;i++)Line(vh,new Vector2(r.xMin,r.yMin+i*r.height/3),new Vector2(r.xMax,r.yMin+i*r.height/3),.5f,new Color(.35f,.51f,.57f,.2f));
            if(points==null||points.Length<2)return;
            float min=float.MaxValue,max=float.MinValue;foreach(float value in points){min=Mathf.Min(min,value);max=Mathf.Max(max,value);}
            if(max-min<.001f)max=min+1;
            Vector2 previous=Vector2.zero;
            for(int i=0;i<points.Length;i++)
            {
                Vector2 p=new Vector2(r.xMin+i*r.width/(points.Length-1),r.yMin+10+(points[i]-min)/(max-min)*(r.height-20));
                if(i>0)
                {
                    int n=vh.currentVertCount;Color fill=new Color(lineColor.r,lineColor.g,lineColor.b,.10f);
                    vh.AddVert(new Vector3(previous.x,r.yMin),fill,Vector2.zero);vh.AddVert(new Vector3(p.x,r.yMin),fill,Vector2.zero);
                    vh.AddVert(p,fill,Vector2.zero);vh.AddVert(previous,fill,Vector2.zero);vh.AddTriangle(n,n+1,n+2);vh.AddTriangle(n,n+2,n+3);
                    Line(vh,previous,p,2,lineColor);
                }
                previous=p;
            }
        }
        public void Set(float[] values){points=values;SetVerticesDirty();}
        public static void Line(VertexHelper vh,Vector2 a,Vector2 b,float width,Color color)
        {
            var normal=new Vector2(-(b-a).y,(b-a).x).normalized*width/2;int n=vh.currentVertCount;
            vh.AddVert(a-normal,color,Vector2.zero);vh.AddVert(a+normal,color,Vector2.zero);vh.AddVert(b+normal,color,Vector2.zero);vh.AddVert(b-normal,color,Vector2.zero);
            vh.AddTriangle(n,n+1,n+2);vh.AddTriangle(n,n+2,n+3);
        }
    }
}
