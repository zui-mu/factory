# 质因云联

从车间感知到生产决策的智慧工厂平台。仓库包含 **1.5.0 · MySQL** 网页平台和 Unity 仿真工厂。完整演示步骤见[统一运行说明](README_统一运行说明.md)。

## 目录

```text
factory/
├─ frontend/       页面、样式、交互和背景
├─ backend/        Python接口、因果分析、联邦训练、测试和工具
│  ├─ sql/         MySQL主业务库、排班模块、节点库建表脚本
│  ├─ assets/      登录后可访问的三路监控演示视频
│  └─ fixtures/    初始化业务快照
├─ unity/          Unity 2022.3.62f3c1 仿真工程
├─ data/           本机连接配置、数据库和上传文件（首次配置生成）
├─ setup.bat       首次配置MySQL和Python依赖
├─ start.bat       电脑启动
├─ start-lan.bat   手机局域网启动
└─ run.py          前后端统一启动入口
```

前端使用原生 HTML/CSS/JavaScript，后端使用 Python + PyMySQL，数据库使用 **MySQL 8.0.16或更新版本**。MySQL表采用InnoDB、utf8mb4、外键和事务。前端与HTTP API由同一个Python服务提供。

## 在这台电脑上运行

首次运行先按部署步骤配置 Python 和 MySQL。配置完成后双击 **start.bat**，浏览器访问 **http://127.0.0.1:8765**。
专用MySQL实例运行在 **127.0.0.1:3307**；启动平台时会检查并自动启动数据库。
如果电脑另有 MySQL 服务使用 3306，项目专用实例会在独立端口管理自己的数据。

- 主业务库：`zhiyinyunlian`
- 工厂节点库：`zhiyinyunlian_factory_1`、`zhiyinyunlian_factory_2`、`zhiyinyunlian_factory_3`
- 连接配置：`data/mysql.json`，包含限定库权限的应用账号。
- 数据库实际文件：`data/mysql-local/db/`，由MySQL管理，不能直接修改。
- 本机实例管理配置：`data/mysql-local/admin.json`，供初始化、测试和停库使用。

三个节点使用独立数据库和账号，节点账号无法查询其他工厂样本；平台账号不能直接读取节点样本。联合训练通过三个本地进程的HTTP接口交换模型参数。

网页登录账号和MySQL账号是两套账号。网页登录初始密码均为 **Zyyl@2026**；已有密码保持原值。

| 网页账号 | 权限 |
| --- | --- |
| admin | 平台管理员，可切换三厂 |
| engineer | 星铸工厂质量工程师 |
| operator | 星铸工厂现场人员 |
| manager | 星铸工厂生产负责人 |
| factory_b | 云枢工厂质量工程师 |
| factory_c | 曜光工厂质量工程师 |

## 在其他电脑运行、提交源代码

1. 安装 **Python 3.9+**（加入PATH）和 **MySQL Server 8.0.16+**。项目可放在有写入权限的目录。
2. 复制项目源码，**不复制 `.venv` 和 `data`**。这两个目录包含本机环境、密码和已有业务数据。
3. 首次双击 **setup.bat**。脚本建立Python虚拟环境、安装PyMySQL，并使用已安装的MySQL程序在项目data中初始化3307实例、四个库和专用账号。不需要知道电脑原有MySQL服务的密码。
4. 双击 **start.bat**。首次启动会创建模拟业务数据和节点训练样本。

首次安装Python依赖需要网络；配置完成后，本地平台、因果分析与联邦训练均可离线使用。无须Node.js或Java。不要直接打开frontend/index.html。
MySQL安装在自定义位置时，可在运行setup.bat前设置 `ZY_MYSQLD` 为mysqld.exe完整路径。
3307已占用时，首次配置使用 `setup.bat --mysql-port 3308`。

若要使用自己管理的MySQL服务，在首次配置前用虚拟环境Python运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -B backend/tools/setup_mysql.py
```

按提示输入管理账号；脚本只创建新数据库与专用账号，拒绝覆盖同名库。已有业务库连接格式参考 `backend/config.example.json`。常规启动读取data/mysql.json，也支持ZY_MYSQL_HOST、PORT、USER、PASSWORD、DATABASE环境变量。数据库及表结构须预先建立。

## Unity 仿真工厂

在 Unity Hub 中添加 `unity/` 并使用 **2022.3.62f3c1** 打开。主场景为 `Assets/FactoryTwin/Scenes/FactoryCampus.unity`。本地导出 Windows 发布包后，可用 `unity/启动仿真工厂.bat` 启动。网页与仿真同机联动时，在 Unity 中填写 `http://127.0.0.1:8765` 和网页账号。详见 [Unity 运行说明](unity/运行说明.md)。

## 手机访问

手机与电脑连接同一Wi-Fi或路由器。先停止8765端口原平台服务，再双击 **start-lan.bat**，打开启动窗口显示的电脑局域网地址，例如 `http://192.168.5.175:8765`。
手机访问平台的8765端口；MySQL的3307端口只监听本机，不需要对手机开放。
遇到防火墙提示，允许Python在自己的可信网络通信。电脑换网后请核对实际联网网卡IPv4地址。

## 演示与停止

### 人员与排班

登录后打开左侧 **人员与排班**。管理员可切换三厂；`manager` 负责星铸工厂的员工、班次、排班和请假审批；质量工程师可查看本厂班表及技能信息；`operator` 只看自己的员工档案、班表和请假申请。请假详细原因只对本人和管理人员展示。

推荐体验流程：

1. 用 `admin` 或 `manager` 登录，维护员工的工号、岗位、班组、技能和绑定账号。
2. 在“班次设置”设定开始、结束时间，再“发布排班”，选择日期、产线、所需技能、人数和人员。
3. 提交请假并审批，班表会显示受影响班次的缺员人数。在“调整 / 替班”中取消原人员、选择替班人员并填写说明。
4. 在因果诊断或异常检查中派单，优先显示当班、技能匹配、同产线且待办较少的人员。非当班或技能待核验时需填写调度说明；正在批准请假期间或停用人员不可派单。调度依据保存在工单时间线中。

跨日班次按开始日期归属；排班时间重叠、批准请假冲突、技能不符合会阻止保存。相邻班次休息不足 11 小时会提醒负责人核对，这只是平台提示阈值。人数不足可先发布并显示缺员；请假与班次部分重叠时，保守地按整班不可用提示补员。取消及调整有审计记录，多人同时修改使用版本检查。

“排班当班”根据班表、当前时间与批准请假计算，**不等于考勤或实际到岗**。班次模板修改只影响后续新增排班，已发布班表保留原时间。时间采用工厂当地北京时间（运行电脑和手机请使用 UTC+8 时区）。

首次升级自动新增 5 张 `staff_` 前缀的 MySQL 表，不清空原业务数据。每厂初始化 6 个演示员工、早晚两个班次以及起始 7 天内工作日的模拟班表；工号以 `DEMO-` 开头。初始班表不会随日期自动续排，后续由负责人维护。未绑定登录账号的员工可以参与排班；接收平台工单需要绑定本厂已有登录账号。

建表脚本位于 `backend/sql/workforce.sql`。历史数据可从另行保管的 SQL 备份恢复。常规首次部署使用 `setup.bat` 和 `start.bat` 即可，无需手动导入完整 SQL。

### 生产与算法演示

生产监控页点击“启动演示产线”，预热后观察报工、耗料与检测，可触发短停、换料、温控故障；温控恢复稳定后点击“确认复产”。退出登录不会自动停止后台演示。
因果问答默认使用本地证据助手；可选外部模型配置见 `backend/AI_CONFIG.md`。
三路监控视频是录制素材，动态工况和算法样本为模拟数据，当前未连接真实工厂设备。

平台启动窗口按Ctrl+C停止网页服务。MySQL实例保持后台运行。如需停库，先停平台，再在根目录执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m backend.local_mysql --stop
```

下次运行start.bat会自动启动MySQL。不要在MySQL运行时移动项目目录或删除data/mysql-local。

## 测试、迁移与备份

双击 `backend/run-tests.bat`。测试在独立的 `zyyl_test_随机编号` 库中执行并清理，不使用平台业务库；若连接自行管理的MySQL服务，先设置ZY_MYSQL_TEST_CONFIG指向可创建测试库的管理连接JSON文件。

旧SQLite数据的一次性迁移工具是 `backend/tools/migrate_sqlite.py`。目标必须为空库；保留原编号、密码、业务记录和训练模型，并逐行核对。运行期间平台只使用MySQL，SQLite模块仅用于读取旧数据来源。

暂停演示、训练和业务写入后，在根目录运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -B backend/tools/backup.py
```

输出为 `data/backups/zyyl-mysql-时间.zip`，含主库与三节点库的标准SQL、上传照片和SHA-256校验文件。恢复时将四份SQL分别导入对应的空MySQL库，将uploads恢复至data/uploads，并配置匹配的账号。不要用直接复制正在运行的MySQL数据目录代替备份。
源码和数据库备份分开保管；不要把含数据库密码的data配置提交到比赛源码中。来源说明见backend/SOURCES.md。
