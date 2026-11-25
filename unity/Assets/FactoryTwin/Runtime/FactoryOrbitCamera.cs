using UnityEngine;
using UnityEngine.EventSystems;

namespace Zhiyin.FactoryTwin
{
    public class FactoryOrbitCamera : MonoBehaviour
    {
        public Vector3 target = new Vector3(0, 0, -25);
        public float distance = 200, yaw = -26, pitch = 28;
        public bool autoOrbit;
        public bool interior;
        private Vector3 desiredTarget;
        private float desiredDistance = 200;
        private float desiredPitch = 28;
        private float desiredYaw = -26;
        private Vector2 down;
        private bool dragged, pointerStartedInScene;
        void Start() { desiredTarget = target; desiredDistance = distance; desiredPitch = pitch; desiredYaw = yaw; }
        public void Focus(Vector3 point, bool inside)
        {
            desiredTarget = point; desiredDistance = inside ? 62 : 200; desiredPitch = inside ? 43 : 28;
            interior = inside; autoOrbit = false;
        }
        public void Home() { desiredYaw = -26; Focus(new Vector3(0,0,-25), false); }
        public void SetView(float viewYaw) { desiredYaw = viewYaw; autoOrbit = false; }
        void Update()
        {
            bool overUI = !GetComponent<Camera>().pixelRect.Contains(Input.mousePosition) || (EventSystem.current != null && EventSystem.current.IsPointerOverGameObject());
            if(Input.GetMouseButtonDown(0)){pointerStartedInScene=!overUI;down=Input.mousePosition;dragged=false;}
            if (!overUI && pointerStartedInScene && Input.GetMouseButton(0) && ((Vector2)Input.mousePosition - down).sqrMagnitude > 36)
            {
                dragged = true; autoOrbit = false;
                desiredYaw += Input.GetAxis("Mouse X") * 3.4f;
                desiredPitch = Mathf.Clamp(desiredPitch - Input.GetAxis("Mouse Y") * 2.2f, 18, 72);
            }
            if (!overUI && pointerStartedInScene && Input.GetMouseButtonUp(0) && !dragged)
            {
                RaycastHit hit;
                if (Physics.Raycast(GetComponent<Camera>().ScreenPointToRay(Input.mousePosition), out hit, 1000))
                {
                    var selectable = hit.collider.GetComponentInParent<FactorySelectable>();
                    if (selectable != null && FactoryTwinApp.Instance != null) FactoryTwinApp.Instance.SelectLine(selectable.lineIndex, selectable.isEquipment);
                }
            }
            if (!overUI)
            {
                float wheel = Input.GetAxis("Mouse ScrollWheel");
                if (Mathf.Abs(wheel) > .001f) { desiredDistance = Mathf.Clamp(desiredDistance - wheel * 90, 35, 270); autoOrbit = false; }
                if (Input.GetMouseButton(1))
                {
                    autoOrbit = false;
                    desiredTarget += Quaternion.Euler(0, desiredYaw, 0) * new Vector3(-Input.GetAxis("Mouse X"), 0, -Input.GetAxis("Mouse Y")) * distance * .008f;
                    desiredTarget.x = Mathf.Clamp(desiredTarget.x, -90, 90); desiredTarget.z = Mathf.Clamp(desiredTarget.z, -65, 65);
                }
            }
            if (autoOrbit) desiredYaw += Time.deltaTime * 3;
            float blend = 1 - Mathf.Exp(-Time.deltaTime * 5);
            target = Vector3.Lerp(target, desiredTarget, blend);
            distance = Mathf.Lerp(distance, desiredDistance, blend);
            yaw = Mathf.LerpAngle(yaw, desiredYaw, blend); pitch = Mathf.Lerp(pitch, desiredPitch, blend);
            transform.position = target + Quaternion.Euler(pitch, yaw, 0) * new Vector3(0, 0, -distance);
            transform.LookAt(target);
        }
    }
}
