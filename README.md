# Alien Invasion

太空射击游戏，采用 WASD 移动、鼠标瞄准和左键射击。玩法依据见 [Game Design.md](Game%20Design.md)，开发与验收参考 [Game Development Guide.md](Game%20Development%20Guide.md)。

完整的实现方案、模块接口、开发阶段、资源清单与测试验收计划见 [Development Documentation.md](Development%20Documentation.md)。

开发按 P0–P9 推进：需求基线 → 启动与输入 → 基础战斗 → 普通关卡 → Boss 与胜负 → 菜单与难度 → 特殊武器 → 能量与支援 → 最终资源 → 整体验收与交付。每阶段功能、验收清单和进度状态见开发文档第 8 节；基础版本在 P5 验收通过后，再整合扩展组件。

## 当前状态

P0–P3 已实现：可运行输入和基础战斗、三类敌机、12 波普通关卡、陨石预警与每 7 秒回血。阶段验证记录见 [docs/progress.md](docs/progress.md)。Boss、菜单和扩展待后续阶段，最终美术尚未制作。

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

| 操作 | 行为 |
|---|---|
| WASD | 按屏幕方向移动 |
| 鼠标 | 移动准星，飞船始终朝向准星 |
| 按住左键 | 按当前武器的射击间隔持续射击 |
| Q | 满三格充能时激活追踪导弹，使用 5 秒 |
| E | 满三格充能时激活连锁电弧，使用 5 秒 |
| X | 满战斗能量时呼叫 7.5 秒火力支援，5 轮打击，每轮最多 3 个目标 |
| Esc | 暂停或继续 |

特殊武器使用期间仍需按住左键射击。支援期间不获得战斗能量，结束后能量清空。每 7 秒自动掉落一个等概率的回血、导弹充能或电弧充能补给，与击杀无关，Boss 战仍持续掉落。

## 资源分工

美术、图标等非代码资源由助手生成，音效由助手设计，BGM 由开发者挑选。图片与音频使用项目相对路径；制作规格见设计文档第 6.11 节。

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
