using System;
using UnityEngine;
using UnityEngine.UI;

namespace Zhiyin.FactoryTwin
{
    public static class FactoryUI
    {
        public static Font font;
        public static readonly Color White = new Color(.91f,.97f,1);
        public static readonly Color Muted = new Color(.67f,.80f,.86f);
        public static readonly Color Cyan = new Color(.28f,.88f,.83f);
        public static readonly Color Gold = new Color(.94f,.74f,.36f);
        public static readonly Color Red = new Color(1,.43f,.40f);
        public static RectTransform Rect(string name,Transform parent,float x,float y,float w,float h)
        {
            var go=new GameObject(name,typeof(RectTransform));var r=go.GetComponent<RectTransform>();
            r.SetParent(parent,false);r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);
            r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);return r;
        }
        public static RectTransform Panel(string name,Transform parent,float x,float y,float w,float h,Color color)
        {
            var r=Rect(name,parent,x,y,w,h);r.gameObject.AddComponent<Image>().color=color;return r;
        }
        public static RectTransform GlassPanel(string name,Transform parent,float x,float y,float w,float h,bool panel=false)
        {
            var r=Rect(name,parent,x,y,w,h);r.gameObject.AddComponent<FactoryGlassGraphic>().panel=panel;
            Panel("Glass upper rim",r,0,0,w,1,new Color(.55f,.82f,.90f,.19f)).GetComponent<Image>().raycastTarget=false;
            Panel("Glass lower rim",r,0,h-1,w,1,new Color(.35f,.67f,.76f,.12f)).GetComponent<Image>().raycastTarget=false;
            Panel("Glass left rim",r,0,1,1,h-2,new Color(.45f,.76f,.85f,.12f)).GetComponent<Image>().raycastTarget=false;
            Panel("Glass right rim",r,w-1,1,1,h-2,new Color(.45f,.76f,.85f,.12f)).GetComponent<Image>().raycastTarget=false;
            return r;
        }
        public static Text Text(string name,Transform parent,string value,float x,float y,float w,float h,int size=18,Color? color=null,bool bold=false,TextAnchor align=TextAnchor.UpperLeft)
        {
            var r=Rect(name,parent,x,y,w,h);var text=r.gameObject.AddComponent<Text>();
            text.font=font;text.text=value;text.fontSize=size;text.color=color??White;text.fontStyle=bold?FontStyle.Bold:FontStyle.Normal;
            text.alignment=align;text.horizontalOverflow=HorizontalWrapMode.Wrap;text.verticalOverflow=VerticalWrapMode.Overflow;text.lineSpacing=.94f;
            text.raycastTarget=false;return text;
        }
        public static Button Button(string name,Transform parent,string caption,float x,float y,float w,float h,Action clicked,bool primary=false)
        {
            var r=Panel(name,parent,x,y,w,h,primary?new Color(.09f,.47f,.49f,.90f):new Color(.10f,.22f,.29f,.81f));
            var b=r.gameObject.AddComponent<Button>();var colors=b.colors;colors.highlightedColor=new Color(.60f,.88f,.91f);colors.pressedColor=new Color(.3f,.68f,.70f);b.colors=colors;
            Text("Caption",r,caption,6,0,w-12,h,16,primary?White:Muted,false,TextAnchor.MiddleCenter);
            b.onClick.AddListener(()=>clicked());return b;
        }
        public static InputField Input(string name,Transform parent,string placeholder,float x,float y,float w,float h,bool password=false)
        {
            var r=Panel(name,parent,x,y,w,h,new Color(.04f,.11f,.16f,.97f));
            var field=r.gameObject.AddComponent<InputField>();
            var text=Text("Value",r,"",12,0,w-24,h,18,White,false,TextAnchor.MiddleLeft);
            field.textComponent=text;var hint=Text("Placeholder",r,placeholder,12,0,w-24,h,17,Muted,false,TextAnchor.MiddleLeft);field.placeholder=hint;
            if(password)field.contentType=InputField.ContentType.Password;
            return field;
        }
        public static RectTransform Card(Transform parent,string title,string eyebrow,float x,float y,float w,float h,Color accent)
        {
            var r=GlassPanel(title,parent,x,y,w,h,w<600);
            Panel("Top accent",r,0,0,w,2,new Color(accent.r,accent.g,accent.b,.65f));
            Panel("Title rule",r,20,74,w-40,1,new Color(.23f,.41f,.48f,.35f));
            Text("Eyebrow",r,eyebrow,22,14,w-44,16,10,Muted);
            Text("Title",r,title,22,33,w-44,33,22,White,true);
            return r;
        }
        public static void Rule(Transform parent,float x,float y,float w)
        {Panel("Rule",parent,x,y,w,1,new Color(.25f,.42f,.49f,.34f));}
    }
}
