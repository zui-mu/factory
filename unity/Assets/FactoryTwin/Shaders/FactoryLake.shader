Shader "Zhiyin/Lake"
{
    Properties
    {
        _DeepColor ("Water",Color) = (.12,.35,.43,1)
        _SkyColor ("Sky reflection",Color) = (.64,.81,.84,1)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry+5" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "UnityCG.cginc"
            struct appdata { float4 vertex:POSITION; };
            struct v2f { float4 pos:SV_POSITION; float3 world:TEXCOORD0; UNITY_FOG_COORDS(1) };
            float4 _DeepColor,_SkyColor;
            v2f vert(appdata v)
            {
                v2f o;o.pos=UnityObjectToClipPos(v.vertex);o.world=mul(unity_ObjectToWorld,v.vertex).xyz;
                UNITY_TRANSFER_FOG(o,o.pos);return o;
            }
            fixed4 frag(v2f i):SV_Target
            {
                float2 p=i.world.xz;
                float wave=sin(p.x*.19+p.y*.23+_Time.y*.45)*sin(p.y*.28-p.x*.11-_Time.y*.32);
                float fine=sin(p.x*1.7+p.y*.9+_Time.y*.72)*sin(p.y*1.1-p.x*.7-_Time.y*.48);
                float3 normal=normalize(float3(wave*.028+fine*.011,1,wave*.025));
                float3 view=normalize(_WorldSpaceCameraPos-i.world);
                float fresnel=pow(1-saturate(dot(normal,view)),3);
                float3 color=lerp(_DeepColor.rgb,_SkyColor.rgb,.21+fresnel*.6);
                float glint=pow(saturate(dot(reflect(-view,normal),normalize(float3(-.3,.8,-.35)))),96);
                color+=wave*.016+fine*.006+glint*.16;
                fixed4 result=fixed4(color,1);UNITY_APPLY_FOG(i.fogCoord,result);return result;
            }
            ENDCG
        }
    }
}
