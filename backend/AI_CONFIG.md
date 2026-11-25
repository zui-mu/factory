# 可选外部模型配置

默认使用本地证据助手，无需密钥或网络。因果分析与本地联邦训练不依赖外部大模型。

需要外部模型时，在项目根目录 PowerShell 中设置以下环境变量后启动：

```powershell
$env:ZY_AI_URL='https://你的服务地址/v1/chat/completions'
$env:ZY_AI_MODEL='你的模型名称'
$env:ZY_AI_KEY='你的服务密钥'
py -3 -X utf8 -B run.py --open
```

接口需兼容 Chat Completions 协议。地址要求 HTTPS，本机测试服务可使用 localhost/127.0.0.1 的 HTTP。
在问答页明确选择使用外部模型后才会发送问题及统计证据。密钥不要写入源码或随项目提交。
实际服务可用性取决于所配置的模型服务；默认本地证据助手可独立使用。
