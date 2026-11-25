using UnityEngine;
using UnityEngine.UI;

namespace Zhiyin.FactoryTwin
{
    /// <summary>Subtle glass tint and rim; remains independent of all dashboard text and business logic.</summary>
    [RequireComponent(typeof(CanvasRenderer))]
    public class FactoryGlassGraphic : MaskableGraphic
    {
        public bool panel=true;
        static Material glassMaterial;
        protected override void OnEnable()
        {
            base.OnEnable();
            if(glassMaterial==null)
            {
                var shader=Resources.Load<Shader>("Shaders/FactoryGlass");
                if(shader!=null)glassMaterial=new Material(shader){name="Dashboard frosted glass",hideFlags=HideFlags.DontSave};
            }
            if(glassMaterial!=null)material=glassMaterial;
        }
        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();Rect r=rectTransform.rect;
            Color top=new Color(.05f,.17f,.25f,panel?.90f:.94f);
            Color bottom=new Color(.025f,.115f,.20f,panel?.88f:.92f);
            Quad(vh,r.xMin,r.yMin,r.xMax,r.yMax,bottom,top);
        }
        static void Quad(VertexHelper vh,float left,float bottom,float right,float top,Color lower,Color upper)
        {
            int i=vh.currentVertCount;
            vh.AddVert(new Vector3(left,bottom),lower,Vector2.zero);vh.AddVert(new Vector3(left,top),upper,Vector2.up);
            vh.AddVert(new Vector3(right,top),upper,Vector2.one);vh.AddVert(new Vector3(right,bottom),lower,Vector2.right);
            vh.AddTriangle(i,i+1,i+2);vh.AddTriangle(i,i+2,i+3);
        }
    }
}
