using UnityEngine;

namespace Zhiyin.FactoryTwin
{
    /// <summary>Extends the same view behind glass cards without changing the interactive viewport.</summary>
    [DefaultExecutionOrder(1000)]
    public class FactoryBackdropCamera : MonoBehaviour
    {
        public Camera source;
        Camera backdrop;
        void Awake(){backdrop=GetComponent<Camera>();}
        void LateUpdate()
        {
            if(source==null)return;
            transform.SetPositionAndRotation(source.transform.position,source.transform.rotation);
            backdrop.nearClipPlane=source.nearClipPlane;backdrop.farClipPlane=source.farClipPlane;
            // Expand the central projection to full screen. Pixel positions remain continuous at its edges.
            Rect pixels=source.pixelRect;
            Rect rect=new Rect(pixels.x/Screen.width,pixels.y/Screen.height,pixels.width/Screen.width,pixels.height/Screen.height);
            Matrix4x4 projection=source.projectionMatrix;
            projection.SetRow(0,projection.GetRow(0)*rect.width+projection.GetRow(3)*(2*rect.x+rect.width-1));
            projection.SetRow(1,projection.GetRow(1)*rect.height+projection.GetRow(3)*(2*rect.y+rect.height-1));
            backdrop.projectionMatrix=projection;
        }
    }
}
