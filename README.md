# Alien Invasion

太空射击游戏，采用 WASD 移动、鼠标瞄准和左键射击。玩法依据见 [Game Design.md](Game%20Design.md)，开发与验收参考 [Game Development Guide.md](Game%20Development%20Guide.md)。

完整的实现方案、模块接口、开发阶段、资源清单与测试验收计划见 [Development Documentation.md](Development%20Documentation.md)。

开发按 P0–P9 推进：需求基线 → 启动与输入 → 基础战斗 → 普通关卡 → Boss 与胜负 → 菜单与难度 → 特殊武器 → 能量与支援 → 最终资源 → 整体验收与交付。每阶段功能、验收清单和进度状态见开发文档第 8 节；基础版本在 P5 验收通过后，再整合扩展组件。

## 当前状态

P0–P8 已实现：完整基础版本（Git 标签 `baseline-p5`）、Q/E/X 扩展、最终透明精灵与 9 种音效。阶段记录见 [docs/progress.md](docs/progress.md)。整体验收、人工平衡评价与交付整理属于 P9。

P9 工程检查已覆盖 40 项测试、新环境安装、三难度完整自动胜负和实时运行；人工平衡、试听和报告／演示尚待完成，未标为完整交付。实际证据与限制见 [docs/acceptance.md](docs/acceptance.md)。

2026-10-08 新增统一设置页、键位重绑定与双语界面；共 56 项测试通过，真实窗口与完整自动流程检查见验收索引。

随后将出击准备页替换为三关卡选择页。关卡 2 保留原有 12 波与母舰战斗；关卡 3 的普通敌机合计增加约 20%（118 → 142 架），Boss 血量增加 40%。关卡 1 暂时保留原内容，教程设计审阅后再实现。原三入口证据见 `docs/evidence/levels/`，最新关卡 3 数值与流程验证见 `docs/evidence/level-3-balance/`。

## 依赖安装

在 Windows 安装 Python 3.13.x 后，在项目根目录的 PowerShell 中执行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

直接使用虚拟环境解释器，无需修改 PowerShell 执行策略。

## 启动方式

在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe main.py
```

入口和资源使用程序目录解析，也可从其他目录使用入口的完整路径启动。

## 操作

| 行为 | 默认键位／操作 |
|---|---|
| 向上移动 | W |
| 向下移动 | S |
| 向左移动 | A |
| 向右移动 | D |
| 追踪导弹 | Q |
| 连锁电弧 | E |
| 火力支援 | X |
| 暂停／继续 | Esc |
| 瞄准 | 鼠标移动（固定） |
| 射击 | 按住鼠标左键（固定） |

主菜单的开始按钮／Enter 进入“关卡”页面，提供关卡 1、2、3。先点击下方的简单／标准／困难选择本局难度，再点击关卡卡片直接进入战斗；数字键 1／2／3 直接进入对应关卡，Enter 进入当前关卡（首次为关卡 1），Esc 返回主菜单。结算 R／重开按钮先返回关卡页，可重新选择关卡与难度。本局开始后不能修改难度，三个关卡均可直接进入。

关卡 2 的敌机数量为侦察 62／射手 36／重型 20（共 118），Boss 简单／标准／困难生命为 1920／2400／3000。关卡 3 为侦察 75／射手 43／重型 24（共 142）；118 × 1.2 = 141.6，取整为 142，实际增加约 20.34%。关卡 3 的 Boss 生命为 2688／3360／4200；12 波、生成间隔、路线、场内数量上限、补给与技能机制沿用现有规则。关卡 1 教程尚未实现，当前仍运行原有战斗。

每 7 秒生成一份回血／导弹／电弧等概率补给，满容量不消耗。Q/E 使用期间仍需按住左键，松开不停止 5 秒计时。X 满能量启动五轮支援，每轮最多三目标，Boss 每次扣最大生命 10%；支援期间不回能，结束清零。失焦自动暂停，恢复焦点不自动继续，继续后需重新按下左键。

主菜单、暂停菜单可进入设置页。设置页左侧为行为／键位两列表格：点击键盘操作右侧单元格后，按下任意一个键盘键立即绑定（包括 Esc、F1 和修饰键）；点击其他位置取消等待。鼠标瞄准与左键射击固定。HUD 和暂停提示会同步显示当前键位。

允许重复键位：所有冲突单元格以高透明度淡红色缓慢闪烁，四秒一轮；共享键会触发所有对应行为，仍遵守充能、能量、特殊武器互斥及暂停规则。相反移动方向共享键时互相抵消。

语言只能在设置页点击 English／简体中文切换，F1 和其他页面没有语言切换入口。音效与现有音乐音量均使用可拖动滑块，范围 0–100%，即时生效。设置页仅提供“重置键位”，只恢复上表的默认键位，保留语言和音量。从暂停进入设置时战斗保持冻结，返回后仍暂停。

首次启动默认英语。语言、键位和音量自动保存到程序目录的 `user_settings.json`，开始、重开、回菜单和下次启动均沿用；难度不保存到该文件。缺失或损坏的字段回退默认值；无法保存时设置页显示提醒，本次修改仍在当前运行内生效。检查工具使用隔离偏好，不改玩家的设置文件。

## 资源分工

美术、图标等非代码资源由助手生成，音效由助手设计，BGM 由开发者挑选。图片与音频使用项目相对路径；制作规格见设计文档第 6.11 节。

素材来源与规格见 [assets/manifest.md](assets/manifest.md)，使用内置 imagegen 制作图集和原创代码合成音效。设置页可分别调整音效与音乐音量。BGM 未提供，游戏无音乐正常运行；可选文件为 `assets/audio/music/bgm.ogg`，请同时记录来源和许可。音频设备不可用时静音运行。Windows 中文字体按系统安装情况加载，不分发系统字体。

## 验证

已执行真实 SDL 窗口的显示、输入和退出检查：

```powershell
.\.venv\Scripts\python.exe tools/check_window.py
```

本检查在真实窗口验证移动、射击、受伤、暂停与 QUIT，保存阶段截图。规则测试命令：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

自动输入流程检查（真实规则，无跳波或无敌；墙钟加速，不能替代人工手感评价）：

```powershell
.\.venv\Scripts\python.exe tools/play_check.py
```

会在 `docs/evidence/` 保存运行事件与截图。

三关卡入口、双语排版与真实窗口操作检查，以及指定关卡的完整流程：

```powershell
.\.venv\Scripts\python.exe tools/check_levels.py
.\.venv\Scripts\python.exe tools/play_check.py --level 2 --output docs/evidence/levels/flow-level-2
```

`--level` 支持 1／2／3，默认 1；使用不同输出目录分别保存关卡证据。`check_window.py`、`check_settings.py`、`check_language.py` 也支持 `--output` 指定证据目录。

设置与双语窗口检查（键位表格、改键、重复键、柔和闪烁、滑块、重置、保存与字体）：

```powershell
.\.venv\Scripts\python.exe tools/check_settings.py
.\.venv\Scripts\python.exe tools/check_language.py
```

截图和结果保存到 `docs/evidence/settings/`。自动流程工具也支持 `--language en` 或 `--language zh-CN`，建议分别指定输出目录以保留两种语言的证据：

```powershell
.\.venv\Scripts\python.exe tools/play_check.py --language zh-CN --output docs/evidence/settings/flow-zh-CN
```

资源与音效检查：

```powershell
.\.venv\Scripts\python.exe tools/check_resources.py
```

同波次难度对照与实时性能检查：

```powershell
.\.venv\Scripts\python.exe tools/compare_difficulty.py
.\.venv\Scripts\python.exe tools/play_check.py --realtime --output docs/evidence/realtime
```

## 候选交付包

```powershell
.\.venv\Scripts\python.exe tools/build_release.py
```

生成 `dist/Alien-Invasion-candidate.zip` 与 SHA256，包含源码、依赖、资源、测试、说明和证据；解压后按本文创建 Python 3.13 环境启动，不含本机 `.venv`。候选包用于审核，不表示 P9 人工验收已通过。
