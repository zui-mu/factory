using UnityEngine;
namespace Zhiyin.FactoryTwin
{
    public class FactoryMachineMotion : MonoBehaviour
    {
        public Transform actuator;
        public int lineIndex;
        public bool conveyor;
        Vector3 origin;
        void Start() { if (actuator != null) origin = actuator.localPosition; }
        void Update()
        {
            var app = FactoryTwinApp.Instance;
            if (app == null || (!app.Connected && !app.simulation.playing) || !app.simulation.lines[lineIndex].running || actuator == null) return;
            actuator.localPosition = origin + (conveyor ? Vector3.right * Mathf.Repeat(Time.time * 1.8f, 7) : Vector3.up * Mathf.Sin(Time.time * 2) * .55f);
        }
    }
}
