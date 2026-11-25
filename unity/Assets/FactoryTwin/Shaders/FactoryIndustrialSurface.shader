Shader "Zhiyin/Industrial Surface"
{
    Properties
    {
        _Color ("Surface colour",Color)=(.85,.88,.9,1)
        _Metallic ("Metallic",Range(0,1))=.2
        _Glossiness ("Smoothness",Range(0,1))=.45
        _RibStrength ("Rib strength",Float)=.05
        _RibScale ("Ribs per metre",Float)=3.4
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0
        struct Input { float3 worldPos;float3 worldNormal; };
        fixed4 _Color;half _Metallic,_Glossiness;float _RibScale,_RibStrength;
        void surf(Input IN,inout SurfaceOutputStandard o)
        {
            float nx=abs(IN.worldNormal.x),ny=abs(IN.worldNormal.y);
            float along=nx>.5?IN.worldPos.z:IN.worldPos.x;
            float rib=pow(.5+.5*sin(along*_RibScale*6.283),8);
            float micro=frac(sin(dot(floor(IN.worldPos*24),float3(12.98,78.23,41.37)))*43758.54);
            o.Albedo=_Color.rgb*(1-rib*_RibStrength)*(1+micro*.025);
            o.Metallic=_Metallic;o.Smoothness=_Glossiness;o.Alpha=1;
        }
        ENDCG
    }
    FallBack "Standard"
}
