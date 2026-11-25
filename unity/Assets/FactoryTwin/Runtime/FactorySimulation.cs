using System;
using UnityEngine;

namespace Zhiyin.FactoryTwin
{
    [Serializable] public class DemoModelNode
    {
        public int id, trainCount, validationCount, testCount;
        public float[] localWeights;
        public float localF1, federatedF1, recall, falsePositiveRate;
        public bool accepted;
    }
    [Serializable] public class DemoModel
    {
        public string version, source;
        public int rounds;
        public float threshold;
        public float[] weights;
        public DemoModelNode[] nodes;
        public float Predict(float[] features, int factory)
        {
            var node = nodes[Mathf.Clamp(factory - 1, 0, nodes.Length - 1)];
            var w = node.accepted ? weights : node.localWeights;
            double z = w[0];
            for (int i = 0; i < 5; i++) z += w[i + 1] * features[i];
            return (float)(1.0 / (1.0 + Math.Exp(-Math.Max(-35, Math.Min(35, z)))));
        }
    }

    [Serializable] public class FactoryLine
    {
        public int index, deviceId, planned, completed, inspected, defects;
        public string name, equipment, batch, status = "运行", task = "暂无待办";
        public float temperature, pressure, vibration, risk, referencePrice, cycleSeconds;
        public float cycle;
        public int reviewSampleAt;
        public bool lastSamplePassed=true;
        public bool faulty, running = true, fresh = true;
        public float[] features = new float[5];
    }

    public sealed class FactorySimulation
    {
        public readonly FactoryLine[] lines = new FactoryLine[4];
        public readonly string[] factories = { "星铸工厂", "云枢工厂", "曜光工厂" };
        public readonly string[][] staff = {
            new[] { "知夏 · 工艺", "云帆 · 操作", "砺行 · 点检" },
            new[] { "清越 · 操作", "望舒 · 点检", "星禾 · 检验" },
            new[] { "言川 · 装配", "初霁 · 操作", "沐晨 · 检验" },
            new[] { "明澈 · 检验", "景行 · 操作", "予安 · 点检" }
        };
        public DemoModel model;
        public int factory = 1;
        public bool playing = true;
        public string lastEvent = "演示产线已就绪 · 点击厂房可进入车间";
        public string eventTime = "";
        private System.Random random;
        private float clock;
        public FactorySimulation()
        {
            var resource = Resources.Load<TextAsset>("DemoModels");
            if (resource != null) model = JsonUtility.FromJson<DemoModel>(resource.text);
            Reset(1);
        }
        public void Reset(int factoryId)
        {
            factory = factoryId;
            random = new System.Random(735 + factoryId);
            string[] names = { "成型一线", "加工二线", "装配三线", "检测四线" };
            string[] devices = { "精密注塑单元", "数控加工中心", "自动装配单元", "在线检测单元" };
            for (int i = 0; i < 4; i++)
            {
                lines[i] = new FactoryLine {
                    index = i, deviceId = (factoryId - 1) * 4 + i + 1,
                    name = names[i], equipment = devices[i],
                    planned = 2400 - i * 200, completed = 680 - i * 85 + factoryId * 29,
                    inspected = 120 + i * 20, defects = 2 + i,
                    batch = "ZY-" + DateTime.Now.ToString("MMdd") + "-" + factoryId + (i + 1) + "01",
                    temperature = 76 + i * 3, pressure = 5.2f + i * .25f, vibration = .65f + i * .1f,
                    cycleSeconds = 5 + i * 2, referencePrice = 120 + i * 35
                };
                lines[i].features[3] = i % 2;
                lines[i].features[4] = i > 1 ? 1 : 0;
                Predict(lines[i]);
            }
            Event("已切换至" + factories[factoryId - 1] + " · 独立演示数据");
        }
        private void Predict(FactoryLine line)
        {
            line.features[0] = line.temperature > 90 ? 1 : 0;
            line.features[1] = line.pressure > 8 ? 1 : 0;
            line.features[2] = line.vibration > 3 ? 1 : 0;
            line.risk = model == null ? 0 : model.Predict(line.features, factory);
        }
        public void Tick(float dt)
        {
            if (!playing) return;
            clock += dt;
            foreach (var line in lines)
            {
                float target = line.faulty ? 98 : 76 + line.index * 3;
                line.temperature = Mathf.MoveTowards(line.temperature, target, dt * 1.8f);
                line.pressure = (line.running ? 5.2f + line.index * .25f : .5f) + Mathf.Sin(clock * .64f + line.index) * .16f;
                line.vibration = (line.running ? .65f + line.index * .1f : .12f) + Mathf.Sin(clock * 1.4f + line.index) * .045f;
                if (line.faulty && line.temperature >= 90 && line.running)
                {
                    line.running = false; line.status = "参数预警"; line.task = "待派单";
                    Event(line.name + "温度越限 · 已停止演示生产，请安排检查");
                }
                Predict(line);
                if (!line.running || line.completed >= line.planned) continue;
                line.cycle += dt;
                if (line.cycle >= line.cycleSeconds)
                {
                    line.cycle -= line.cycleSeconds;
                    line.completed++;
                    if (line.completed % 5 == 0)
                    {
                        line.inspected++;
                        float defectRate = line.faulty ? .22f : .018f + line.index * .003f;
                        line.lastSamplePassed=random.NextDouble()>=defectRate;
                        if (!line.lastSamplePassed) line.defects++;
                    }
                    if (line.completed >= line.planned) { line.running = false; line.status = "已完成"; }
                }
            }
        }
        public void Fault(int index)
        {
            var l = lines[index]; l.faulty = true;
            Event(l.name + "已触发温控故障 · 温度逐步升高");
        }
        public bool Recover(int index)
        {
            var l = lines[index];
            if (l.faulty) { l.faulty = false; l.status = l.running?"运行":"降温观察"; Event(l.name + (l.running?"温控恢复 · 未达到停产条件":"开始降温，请在稳定后确认复产")); return false; }
            if (l.temperature > 76 + l.index * 3 + 1.5f) { Event("温度尚未稳定，请继续观察"); return false; }
            if(l.completed>=l.planned){Event("该工单已完成，无需复产");return false;}
            if(l.running){Event("产线正在运行，无需重复复产");return false;}
            if(l.task!="处理中"){Event("请先安排检查，再确认复产");return false;}
            l.running = true; l.status = "运行"; l.task = "待复检";l.reviewSampleAt=l.inspected;
            Event(l.name + "演示复产 · 处置任务待复检"); return true;
        }
        public bool Review(int index)
        {
            var l=lines[index];
            if(l.task!="待复检"||!l.running||l.faulty){Event("当前尚不满足复检条件");return false;}
            if(l.inspected<=l.reviewSampleAt||!l.lastSamplePassed){Event("请等待复产后新的合格抽检记录，再确认关闭");return false;}
            l.task="已关闭";Event(l.name+"复产后抽检合格，演示检查任务已关闭");return true;
        }
        public void Dispatch(int index)
        {
            var l = lines[index]; l.task = "处理中";
            Event("已安排" + staff[index][2].Split('·')[0].Trim() + "检查" + l.equipment + " · 本地演示任务");
        }
        public void Event(string message) { lastEvent = message; eventTime = DateTime.Now.ToString("HH:mm:ss"); }
        public float ProductionValue { get { float value = 0; foreach (var l in lines) value += l.completed * l.referencePrice; return value; } }
        public int TotalDefects { get { int n = 0; foreach (var l in lines) n += l.defects; return n; } }
    }

}
