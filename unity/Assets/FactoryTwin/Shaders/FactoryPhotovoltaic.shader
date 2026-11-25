Shader "Zhiyin/Photovoltaic"
{
    Properties
    {
        _Color ("Silicon blue",Color) = (.09,.20,.32,1)
        _Metallic ("Metallic",Range(0,1)) = .45
        _Glossiness ("Smoothness",Range(0,1)) = .75
        _MainTex ("UV",2D) = "white" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0
        struct Input { float2 uv_MainTex; };
        fixed4 _Color;half _Metallic,_Glossiness;
        void surf(Input IN,inout SurfaceOutputStandard o)
        {
            float2 uv=IN.uv_MainTex;
            float2 grid=abs(frac(uv*float2(6,10))-.5);
            float cell=1-smoothstep(.465,.5,max(grid.x,grid.y));
            float edge=step(.014,uv.x)*step(.014,uv.y)*step(uv.x,.986)*step(uv.y,.986);
            o.Albedo=lerp(float3(.38,.48,.57),lerp(_Color.rgb*1.22,_Color.rgb,cell),edge);
            o.Metallic=_Metallic;o.Smoothness=_Glossiness;o.Alpha=1;
        }
        ENDCG
    }
    FallBack "Standard"
}
