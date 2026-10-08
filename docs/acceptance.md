# 最终验收与证据索引

日期：2026-10-07。环境：Windows 11 10.0.26200，Python 3.13.9，pygame 2.6.1。P0–P8 本地阶段提交见 docs/progress.md 与 git log；基础恢复点为 baseline-p5。P9 工程检查进行中，人工试玩、平衡和最终报告／演示尚未全部完成，候选包不标为最终交付通过。

## 规则测试

命令：`.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`。

| 用例 | 对应测试文件与证据 | 当前结果 |
|---|---|---|
| U01 移动与接触 | test_rules.py、test_boss.py、check_window.py | 通过 |
| U02 轨迹碰撞 | test_rules.py，包含相对运动、射程、屏幕外出生 | 通过 |
| U03 共用冷却 | test_rules.py、test_special_weapons.py | 通过 |
| U04 定时补给 | test_waves.py、test_special_weapons.py | 通过 |
| U05 导弹／5 秒替换 | test_special_weapons.py | 通过 |
| U06 电弧 | test_special_weapons.py | 通过 |
| U07 实际能量／一次计分 | test_support.py、test_rules.py | 通过 |
| U08 五轮／替补／Boss 比例 | test_support.py | 通过 |
| U09 波次与陨石 | test_waves.py，全难度 118 架自然离场与上限 | 通过 |
| U10 Boss 与胜负 | test_boss.py，包含两种顺序与跨小步双亡 | 通过 |
| U11 暂停与重开 | test_rules.py、test_boss.py、test_menu_difficulty.py、test_support.py | 通过已列自动场景 |
| U12 难度 | test_menu_difficulty.py、test_waves.py | 通过 |

目前 40 项测试通过，日志为 evidence/final-tests.txt；不将用例编号数量解释为课程评分分值。测试覆盖具体边界，完整计划中的人工体验仍单独登记。

## 窗口与完整规则运行

| 用例 | 实际证据 | 状态与限制 |
|---|---|---|
| M01 启动、菜单、退出 | check_window.py，p5-menu/setup.png，computer-use 正式菜单检查 | 启动／菜单／退出通过 |
| M02 移动、瞄准、射击、HUD | check_window.py，p2-window/paused.png，规则测试 | 自动窗口检查通过；人工手感待反馈 |
| M03 伤害、推开、掩护 | test_rules.py、test_boss.py、完整自动输入运行 | 规则／运行通过；手动操作录像待补 |
| M04 普通关卡、Boss | 三难度 *-pilot-run.json 与 waves/rest/boss_*.png | 无跳波、无无敌的完整真实规则运行通过 |
| M05 补给 | *-pilot-run.json 的 drop/pickup，随机分支与生命周期测试 | 自动规则／运行通过 |
| M06 Q/E/X | *-pilot-arc/missile/support.png 与激活／支援事件 | 正常充能、按键和完整运行通过 |
| M07 暂停、失焦、退出 | check_window.py、暂停与清理测试 | 已覆盖规则通过；全部特效的人工暂停演示待补 |
| M08 胜负与重开 | 三难度 pilot（胜利）、idle（自然失败） JSON，重开测试 | 自动真实规则流程通过；人工完整局待反馈 |
| M09 难度差异 | 同波次截图、实际移动／发弹测试、三难度完整运行 | 工程证据通过；初次玩家体验待反馈 |
| M10 资源、字体、声音、静音 | p8-resources.png，check_resources.py 的 WAV 峰值与两种音频后端结果 | 加载／显示／播放／静音通过；试听舒适度待反馈 |

自动输入工具默认按 1/60 秒推进游戏时间并抽帧渲染，墙钟加速，JSON 明确标注。`--realtime` 每帧绘制并按真实墙钟推进，用于本设备性能测量。它们都不替代人工体验，不以精确自动瞄准的时长声称 4–6 分钟目标达成。

最终三难度（种子 5）自动胜利：简单 157.900 秒／114 击杀，标准 162.000 秒／109 击杀，困难 165.550 秒／101 击杀、剩余 59 生命；均生成 118 架普通敌机。自然失败分别 58.683／29.450／22.233 秒。最终实时标准胜利记录为 163.847 游戏秒，163.922 墙钟秒，9326 帧，平均 56.89 FPS；包含自动输入决策开销，95% 帧的计算与绘制时间 ≤3.207 ms。60 FPS 是目标，本设备此测量未达到精确 60；未扩大为所有设备的性能保证。详细环境与事件见 evidence/realtime/standard-pilot-run.json。

新环境复现：在 tmp/repro-venv 使用 Python 3.13 新建 venv，仅按 requirements.txt 安装 pygame 2.6.1；40 项测试和真实窗口输入检查均通过。可移植包由 tools/build_release.py 生成并验证 CRC，不包含开发机虚拟环境；候选包解压到 tmp/package-check 后，使用新环境运行其中的 tools/check_window.py，真实窗口输入和退出检查通过。所有原始 PDF、报告模板与表单保留。

## 结构与功能证据

| 指南目标 | 源码／说明 |
|---|---|
| F01 启动 | main.py、README.md、新环境窗口检查 |
| F02 对象 | render.py、精灵图集、p1-window 与最终波次／Boss 截图 |
| F03 交互 | Game.handle_events、InputState、窗口检查、Q/E/X 激活记录 |
| F04 难度 | settings.DIFFICULTIES、Enemy.create、同波次和测试 |
| F05 扩展 | baseline-p5 与 P6–P7 提交、WeaponController、SupportController |
| S01 模块化 | main→game/render；game→entities/weapons/waves/settings；render→resources |
| S02 复用 | Enemy.create、WeaponController.switch、apply_damage/finalize_kill、moving_hit |
| S03 结构 | dataclass 状态、有限波次／支援、Boss 状态转换 |
| S04 数据 | 稳定对象 ID、各控制器局部状态、单局 reset_session |
| S05 通用性 | 统一难度、波次、资源区域与攻击配置 |
| S06 依赖 | requirements.txt，仅 pygame==2.6.1；ROOT 相对路径 |
| S07 更新 | Game.update 的小步和截止时间拆分；帧末失败优先 |
| S08 注释 | 冷却、支援半开区间、Boss 任务撤销、轨迹／屏幕回收注释 |

已实际查看原评分 PDF 两页。50% 功能／50% 结构及演示表述沿用原件，不计算逐项分数、额外组件分值或星级。原件涉及教材代码，而项目没有收到教材代码，不能声称这一项已通过。

## 待完成项目

- 人工标准局的 4–6 分钟和平衡反馈；三难度初次玩家体验。
- 音量与频繁同时效果的主观试听。
- 完整操作演示录像和最终评价 Word 报告；Markdown 内容已在 evaluation-report.md，原模板不改。
- P9 最终验收通过后才创建完成该阶段的本地提交；当前候选成果不替代发布门槛。
