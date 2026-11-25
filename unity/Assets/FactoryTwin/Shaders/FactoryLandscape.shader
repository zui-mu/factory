Shader "Zhiyin/Landscape"
{
    Properties { _Color ("Tint",Color) = (1,1,1,1) }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0
        struct Input { float4 color : COLOR;float3 worldPos; };
        fixed4 _Color;
        void surf(Input IN,inout SurfaceOutputStandard o)
        {
            float3 albedo=IN.color.rgb;
            #ifndef UNITY_COLORSPACE_GAMMA
                albedo=GammaToLinearSpace(albedo);
            #endif
            float micro=frac(sin(dot(floor(IN.worldPos.xz*19),float2(12.9898,78.233)))*43758.5453);
            float patch=.92+.08*sin(IN.worldPos.x*.44+sin(IN.worldPos.z*.52));
            o.Albedo=albedo*_Color.rgb*(.94+micro*.12)*patch;o.Metallic=0;o.Smoothness=.10;o.Alpha=1;
        }
        ENDCG
    }
    FallBack "Diffuse"
}
