using System;
using System.Globalization;
using UnityEngine;
using UnityEngine.Scripting;
using UnityEngine.UI;

namespace Zhiyin.FactoryTwin
{
    public sealed class FactoryWebPresentation : MonoBehaviour
    {
        public const int LineIndex = 2;

        [Serializable]
        sealed class Snapshot
        {
            public bool valid, running;
            public int runId, deviceId, orderId, completed, quantity;
            public string deviceCode, orderCode, batch, phase, status;
            public float temperature, pressure, vibration;
        }

        FactoryLine line;
        Text stateText, batchText, readingsText;

        internal void Initialize(FactorySimulation simulation)
        {
            simulation.playing = false;
            foreach (var station in simulation.lines)
            {
                station.fresh = false;
                station.running = false;
                station.status = "等待平台数据";
            }
            line = simulation.lines[LineIndex];

            var canvas = new GameObject("Workshop data", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler));
            canvas.GetComponent<Canvas>().renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvas.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1280, 720);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.Expand;

            var panel = FactoryUI.Panel("Workshop status", canvas.transform, 18, 18, 598, 106, new Color(.025f, .075f, .11f, .92f));
            stateText = FactoryUI.Text("Status", panel, "", 14, 9, 570, 29, 20, FactoryUI.White, true);
            batchText = FactoryUI.Text("Batch", panel, "", 14, 41, 570, 23, 15, FactoryUI.Muted);
            readingsText = FactoryUI.Text("Readings", panel, "", 14, 70, 570, 23, 15, FactoryUI.Muted);
            stateText.supportRichText = batchText.supportRichText = readingsText.supportRichText = false;
            Display(null);
        }

        [Preserve]
        public void ApplySnapshot(string json)
        {
            Snapshot snapshot = null;
            if (!string.IsNullOrWhiteSpace(json))
            {
                try { snapshot = JsonUtility.FromJson<Snapshot>(json); }
                catch (ArgumentException) { /* A malformed message clears the display. */ }
            }
            Display(IsCurrentStation(snapshot) ? snapshot : null);
        }

        static bool IsCurrentStation(Snapshot state)
        {
            return state != null && state.valid && state.deviceId == 3 && state.deviceCode == "EQ-03"
                && state.runId > 0 && state.orderId > 0 && state.quantity > 0
                && state.completed >= 0 && state.completed <= state.quantity
                && !string.IsNullOrWhiteSpace(state.orderCode) && !string.IsNullOrWhiteSpace(state.batch)
                && !string.IsNullOrWhiteSpace(state.phase) && !string.IsNullOrWhiteSpace(state.status)
                && float.IsFinite(state.temperature) && float.IsFinite(state.pressure) && float.IsFinite(state.vibration);
        }

        void Display(Snapshot state)
        {
            if (state == null)
            {
                line.fresh = line.faulty = line.running = false;
                line.batch = "";
                line.status = "等待平台数据";
                line.completed = line.planned = 0;
                line.temperature = line.pressure = line.vibration = 0;
                stateText.color = FactoryUI.Muted;
                stateText.text = "装配三线 · 等待平台数据";
                batchText.text = readingsText.text = "";
                return;
            }

            line.fresh = true;
            line.running = state.running;
            line.faulty = state.phase == "fault" || state.status.Contains("预警");
            line.status = state.status;
            line.batch = state.batch;
            line.completed = state.completed;
            line.planned = state.quantity;
            line.temperature = state.temperature;
            line.pressure = state.pressure;
            line.vibration = state.vibration;
            stateText.color = line.faulty ? FactoryUI.Red : line.running ? FactoryUI.Cyan : FactoryUI.White;
            stateText.text = $"装配三线 · {state.deviceCode} · {state.status}";
            batchText.text = $"批次 {state.batch}   ·   报工 {state.completed} / {state.quantity} 件";
            readingsText.text = string.Format(CultureInfo.InvariantCulture,
                "温度 {0:F1} ℃   ·   压力 {1:F2} MPa   ·   振动 {2:F2} mm/s",
                state.temperature, state.pressure, state.vibration);
        }
    }
}
