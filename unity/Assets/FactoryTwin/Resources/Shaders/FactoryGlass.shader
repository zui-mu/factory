Shader "Zhiyin/UI Frosted Glass"
{
    Properties
    {
        [PerRendererData] _MainTex ("Sprite",2D) = "white" {}
        _StencilComp ("Stencil comparison",Float) = 8
        _Stencil ("Stencil ID",Float) = 0
        _StencilOp ("Stencil operation",Float) = 0
        _StencilWriteMask ("Stencil write mask",Float) = 255
        _StencilReadMask ("Stencil read mask",Float) = 255
        _ColorMask ("Color mask",Float) = 15
        [Toggle(UNITY_UI_ALPHACLIP)] _UseUIAlphaClip ("Alpha clip",Float) = 0
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "IgnoreProjector"="True" "RenderType"="Transparent" "CanUseSpriteAtlas"="True" }
        Stencil { Ref [_Stencil] Comp [_StencilComp] Pass [_StencilOp] ReadMask [_StencilReadMask] WriteMask [_StencilWriteMask] }
        Cull Off Lighting Off ZWrite Off ZTest [unity_GUIZTestMode]
        Blend SrcAlpha OneMinusSrcAlpha ColorMask [_ColorMask]
        // One shared capture per frame, reused by the eight glass surfaces.
        GrabPass { "_FactoryGlassScene" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_local _ UNITY_UI_CLIP_RECT
            #pragma multi_compile_local _ UNITY_UI_ALPHACLIP
            #include "UnityCG.cginc"
            #include "UnityUI.cginc"
            struct appdata { float4 vertex:POSITION; float4 color:COLOR; };
            struct v2f { float4 pos:SV_POSITION; float4 grab:TEXCOORD0; float4 local:TEXCOORD1; float4 color:COLOR; };
            sampler2D _FactoryGlassScene;float4 _FactoryGlassScene_TexelSize;float4 _ClipRect;
            v2f vert(appdata v)
            {
                v2f o;o.local=v.vertex;o.pos=UnityObjectToClipPos(v.vertex);o.grab=ComputeGrabScreenPos(o.pos);o.color=v.color;return o;
            }
            fixed4 frag(v2f i):SV_Target
            {
                float2 uv=i.grab.xy/i.grab.w;float2 d=_FactoryGlassScene_TexelSize.xy*4;
                float3 scene=tex2D(_FactoryGlassScene,uv).rgb*.2;
                scene+=tex2D(_FactoryGlassScene,uv+d*float2(1,0)).rgb*.12;
                scene+=tex2D(_FactoryGlassScene,uv-d*float2(1,0)).rgb*.12;
                scene+=tex2D(_FactoryGlassScene,uv+d*float2(0,1)).rgb*.12;
                scene+=tex2D(_FactoryGlassScene,uv-d*float2(0,1)).rgb*.12;
                scene+=tex2D(_FactoryGlassScene,uv+d).rgb*.08;
                scene+=tex2D(_FactoryGlassScene,uv-d).rgb*.08;
                scene+=tex2D(_FactoryGlassScene,uv+d*float2(1,-1)).rgb*.08;
                scene+=tex2D(_FactoryGlassScene,uv+d*float2(-1,1)).rgb*.08;
                scene=lerp(dot(scene,float3(.2126,.7152,.0722)),scene,.35)*float3(.80,.96,1.10);
                float3 tint=i.color.rgb;
                #ifndef UNITY_COLORSPACE_GAMMA
                    tint=GammaToLinearSpace(tint);
                #endif
                fixed4 color=fixed4(lerp(scene,tint,i.color.a),1);
                #ifdef UNITY_UI_CLIP_RECT
                    color.a*=UnityGet2DClipping(i.local.xy,_ClipRect);
                #endif
                #ifdef UNITY_UI_ALPHACLIP
                    clip(color.a-.001);
                #endif
                return color;
            }
            ENDCG
        }
    }
}
