Shader "Zhiyin/Leaves"
{
    Properties
    {
        _MainTex ("Leaf cluster",2D)="white" {}
        _Color ("Tint",Color)=(1,1,1,1)
        _Cutoff ("Alpha cutoff",Range(0,1))=.35
    }
    SubShader
    {
        Tags { "Queue"="AlphaTest" "RenderType"="TransparentCutout" }
        Cull Off AlphaToMask On
        CGPROGRAM
        #pragma surface surf Standard alphatest:_Cutoff addshadow fullforwardshadows
        #pragma target 3.0
        struct Input { float2 uv_MainTex;float4 color:COLOR; };
        sampler2D _MainTex;fixed4 _Color;
        void surf(Input IN,inout SurfaceOutputStandard o)
        {
            fixed4 leaf=tex2D(_MainTex,IN.uv_MainTex);
            float3 tint=IN.color.rgb*_Color.rgb;
            #ifndef UNITY_COLORSPACE_GAMMA
                tint=GammaToLinearSpace(tint);
            #endif
            o.Albedo=leaf.rgb*tint;o.Emission=o.Albedo*.13;o.Smoothness=.2;o.Occlusion=.92;o.Alpha=leaf.a;
        }
        ENDCG
    }
    FallBack "Transparent/Cutout/Diffuse"
}
