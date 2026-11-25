Shader "Zhiyin/Vegetation"
{
    Properties { _Color ("Tint",Color)=(1,1,1,1) }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0
        struct Input { float4 color:COLOR;float3 worldPos; };
        fixed4 _Color;
        float noise(float3 p){return frac(sin(dot(p,float3(12.9898,78.233,45.543)))*43758.5453);}
        void surf(Input IN,inout SurfaceOutputStandard o)
        {
            float n=noise(floor(IN.worldPos*7));
            float3 color=IN.color.rgb*_Color.rgb*(.66+n*.52);
            #ifndef UNITY_COLORSPACE_GAMMA
                color=GammaToLinearSpace(color);
            #endif
            o.Albedo=color;o.Smoothness=.17;o.Metallic=0;o.Occlusion=.8;o.Alpha=1;
        }
        ENDCG
    }
    FallBack "Diffuse"
}
