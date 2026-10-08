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

2026-10-07 的 40 项测试通过，日志为 evidence/final-tests.txt；2026-10-08 加入语言回归后为 45 项，设置扩展后共 56 项通过，最新日志为 evidence/settings/tests.txt。不将用例编号数量解释为课程评分分值。测试覆盖具体边界，完整计划中的人工体验仍单独登记。

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
| F05 扩展 | baseline-p5 与 P6–P7 提交、WeaponController、SupportController；后续设置与语言扩展见下文 |
| S01 模块化 | main→game/render/preferences；game→entities/weapons/waves/settings/localization/preferences；render→resources |
| S02 复用 | Enemy.create、WeaponController.switch、apply_damage/finalize_kill、moving_hit |
| S03 结构 | dataclass 状态、有限波次／支援、Boss 状态转换 |
| S04 数据 | 稳定对象 ID、各控制器局部状态、单局 reset_session |
| S05 通用性 | 统一难度、波次、资源区域与攻击配置 |
| S06 依赖 | requirements.txt，仅 pygame==2.6.1；ROOT 相对路径 |
| S07 更新 | Game.update 的小步和截止时间拆分；帧末失败优先 |
| S08 注释 | 冷却、支援半开区间、Boss 任务撤销、轨迹／屏幕回收注释 |

已实际查看原评分 PDF 两页。50% 功能／50% 结构及演示表述沿用原件，不计算逐项分数、额外组件分值或星级。原件涉及教材代码，而项目没有收到教材代码，不能声称这一项已通过。

## 2026-10-08 首版语言扩展验证（历史证据）

本节为设置扩展前的记录。最新需求已移除 F1／其他菜单的语言入口，启动改为沿用本地偏好；当前验收以下节为准。

语言切换属于开发者后续确认的界面扩展，超出 baseline-p5 基础范围，不作为评分材料规定的功能或分值。默认英语，点击任意菜单右上角语言按钮或按 F1 切换英语／简体中文；重开与回菜单保留，退出程序后下次默认英语。

| 检查 | 证据与结果 |
|---|---|
| 默认、按钮、F1、跨状态保留、战斗不变 | tests/test_language.py；全套 45 项测试通过，evidence/language/tests.txt |
| 真实窗口、中文字体、文字／按钮边界、基本输入与退出 | tools/check_language.py；Windows SDL 后端，微软雅黑字形检查通过，evidence/language/check.json |
| 双语界面排版 | evidence/language/en-*.png、zh-CN-*.png 共 16 张；已查看两种语言的说明、HUD 与母舰画面 |
| 英语完整胜利 | evidence/language/flow-en/standard-pilot-run.json；162.000 游戏秒，27400 分，109 击杀，生成 118 架普通敌机 |
| 中文完整胜利 | evidence/language/flow-zh-CN/standard-pilot-run.json；同种子下结果与全部事件日志和英语一致 |
| 中文自然失败 | evidence/language/flow-zh-CN/standard-idle-run.json；29.450 游戏秒，正常进入失败结算 |

上述完整流程使用自动输入与加速墙钟，未替代人工手感和平衡验收。窗口截图中的部分菜单和 Boss 场景用于单独检查排版；完整规则流程证据以两种语言的运行 JSON 为准。

## 2026-10-08 设置与键位扩展验证（关卡页替换前）

最新约定：语言仅在设置页手动切换；设置不含难度，每次开始或重开前选择难度。键位表格可点击右列后按任意单键绑定，共享键同时触发对应行为并柔和红色闪烁；重置功能只保留“重置键位”，保留语言和音量。偏好本地保存，首次默认英语，之后沿用。本功能属于开发者确认的界面扩展，不是新增评分条款。

| 检查 | 证据与结果 |
|---|---|
| 键位捕获、共享动作、独立重置、滑块、冻结与保存 | tests/test_settings.py、test_language.py；全套 56 项通过，evidence/settings/tests.txt |
| 真实窗口操作与冲突提示 | tools/check_settings.py；evidence/settings/check.json 与 *.png，红色缓慢变化、表格和按钮无溢出 |
| 设置页语言选择、无 F1 切换、字体及双语排版 | tools/check_language.py；evidence/settings/language/check.json 与 16 张截图 |
| 基础输入、对象显示、退出及资源 | check_window.py、check_resources.py 通过，当前截图见 evidence/settings/base/；本次音频设备不可用，静音回退正常 |
| 音效／音乐滑块传到播放通道 | SDL dummy 音频后端，check_resources.py 通道音量读回检查通过，evidence/settings/audio-channel-check.txt；不能替代真实试听 |
| 三难度完整自动胜利 | evidence/settings/flow-en/*-pilot-run.json；简单 157.900／标准 162.000／困难 165.550 游戏秒，均生成 118 架普通敌机 |
| 标准中文完整自动胜利与失败 | evidence/settings/flow-zh-CN/*-run.json；胜利 162.000 游戏秒，事件日志与英语一致；自然失败 29.450 游戏秒 |

已实际查看中英文设置页、键位等待、冲突提示、出击准备和 HUD 截图。设置检查中的部分画面用于单独验证控件；完整战斗以运行 JSON 为准。自动输入与虚拟音频后端不替代人工手感、平衡与试听。

## 2026-10-08 三关卡页面验证（独立数值调整前）

按开发者要求，删除开始游戏后的出击准备页，替换为“关卡”页面，提供关卡 1、2、3。点击卡片或按数字键直接进入，底部保留本局难度，Esc／返回按钮回到主菜单；Enter 进入当前关卡。重开、再战与失败重试都返回关卡页。三个关卡全部开放，暂时共用当前 12 波、补给、敌人与母舰规则，独立内容按要求尚未制作。关卡选择属于后续界面扩展，不改变 baseline-p5 基础范围。

| 检查 | 证据与结果 |
|---|---|
| 规则与流程回归 | 全套 62 项 unittest 通过；新增 test_levels.py 覆盖三入口／三难度／双语、键盘重复、重开清理、设置保留、跨状态保护与同种子内容一致 |
| 语法检查 | compileall 对入口、规则、显示、配置、偏好、全部 tests 与 tools 通过 |
| 三入口、输入、暂停、重开与返回 | tools/check_levels.py；evidence/levels/check.json，Windows 真实 SDL 窗口通过，8 张截图；关卡页不绘制键位表 |
| 中英文画面 | evidence/levels/en-levels.png、zh-CN-levels.png；已实际查看，标题、三张卡片、难度与返回入口清楚，无文字溢出 |
| 双语／设置／基础窗口回归 | check_language.py、check_settings.py、check_window.py 全部通过；证据分别位于 evidence/levels/language/、settings/、base/ |
| 三关卡完整自动胜利 | evidence/levels/flow-level-1/、flow-level-2/、flow-level-3/standard-pilot-run.json；标准难度、种子 5，全部 162.000 游戏秒、27400 分、109 击杀、118 架普通敌机；关卡 2 使用中文 |
| 内容一致与正常失败 | evidence/levels/flow-comparison.json：三个关卡的战斗事件完全一致（开局日志保留各自编号）；关卡 3 自然失败为 29.450 游戏秒，生命归零进入失败结算 |

关卡窗口检查使用实际 Windows SDL 窗口与程序输入事件；完整战斗使用公开输入与加速墙钟，无跳波或无敌。这些检查不替代人工手感、平衡与试听，既有 P9 待完成项目保留。

## 2026-10-08 关卡 3 数值调整验证（教程实现前）

关卡 3 普通敌机共 142 架（侦察 75／射手 43／重型 24），较原 118 架增加约 20.34%，为 20% 后按整数总量取整；Boss 血量提高 40%，三难度为 2688／3360／4200。关卡 2 保留原内容；当时关卡 1 教程仅设计待审，不属于该轮运行成果；教程最新验证见下节。

| 检查 | 证据与结果 |
|---|---|
| 自动规则回归 | 全套 64 项通过；evidence/level-3-balance/tests.txt；覆盖换关隔离、12 波参数传播、三难度自然离场和数量上限、Boss 阶段比例与支援取整 |
| 语法与基础真实窗口 | 全模块 compileall 通过；check_window.py 使用 Windows SDL 后端，显示、移动、瞄准、边界和退出通过，截图见 evidence/level-3-balance/base/ |
| 关卡 3 三难度完整胜利 | easy/、standard-verified/、hard/ 中 *-pilot-run.json；均完成 12 波并生成 75／43／24 架；Boss 最大生命 2688／3360／4200；用时 181.650／182.850／192.133 游戏秒 |
| 关卡 2 完整对照 | level-2-regression/standard-pilot-run.json 与修改前 levels/flow-level-2/ 的全部 events 相同，仍为 162.000 秒、27400 分、109 击杀、118 架与 Boss 2400 |
| 自然失败 | failure/standard-idle-run.json；关卡 3 标准难度 29.400 秒生命归零，正常失败 |
| 汇总与画面 | evidence/level-3-balance/comparison.json 对数量、12 波结束、最大生命和原关卡 2 事件进行断言；已查看标准 Boss HUD（3340/3360）及中文困难结算，无新增画面溢出 |

本次工具曾一次写 PNG 失败，另一次重跑窗口停滞被主动结束；未计为通过，随后完整重跑通过，偶发原因未定位。只引用完成的运行记录。完整战斗使用真实 Windows SDL 窗口、公开自动输入和加速墙钟，不替代人工手感／平衡／试听。原评分材料与模板保留，未增补评分条款。

## 2026-10-08 关卡 1 教程实现验证（当前）

开发者确认后实现八步教程，移动说明可直接继续，不设目标圈；末尾为两波 12 架，无 Boss。教学仅调整场景投放、固定训练难度与检查点，实际伤害、补给、充能、能量、5 秒武器和 7.5 秒五轮支援复用现有规则；普通关卡不创建教学控制器。完整说明见 [教程设计与实现](level-1-tutorial-design.md)。

| 检查 | 证据与结果 |
|---|---|
| 规则与语法 | `evidence/tutorial/tests.txt`：84 项全通过；全模块 compileall 通过。20 项教程测试覆盖任务来源、停火 0.4 秒、三次有效躲避、过期与满容量、真实技能效果、完整计时、暂停过渡、清场和切关 |
| 完整教程与改键 | `evidence/tutorial/window/check.json`：英语、中文方向键 + M/N/B/P 两条完整公开输入路线均完成 1–8；真实拾取三格、实际攻击攒能，最终战斗 9／2／1 架，无 Boss |
| 错误恢复 | 同目录英语错误路线：击碎陨石、过期补给、导弹空放、范围外电弧、综合实战死亡；四次当前步骤重试后完成，过期补给补投。成功段数量按最后一个第八步检查点计算 |
| 暂停与排版 | 各路线均验证导弹计时中失焦、设置、暂停冻结；继续时清空旧输入。真实窗口检查教学面板与文字边界；已查看移动页、中文改键电弧页和完成页 |
| 实时运行 | `evidence/tutorial/realtime-final/standard-pilot-run.json`：中文，70.757 游戏秒、77.402 墙钟秒、4678 帧，平均 60.44 FPS，计算 P95 6.049ms；零重试完成八步 |
| 正式关卡回归 | `evidence/tutorial/comparison.json`：关卡 2 的 475 条 events 与关卡 3 的 555 条 events 分别与教程实现前逐条相同，战斗结果一致；118／142 架和 Boss 2400／3360 保持 |
| 原界面与输入 | `levels/`、`base/`、`language/`、`settings/`：三入口、中英文、普通输入、设置／保存／重复键位与正常退出通过；普通战斗工具显式使用关卡 2 |

初次正式关卡回归因同名 PNG 写入失败未计通过；工具改为每次阶段截图使用独立文件后重跑通过。基础窗口脚本的旧数字键 1 难度断言也已改为正式关卡 2 后通过。过程记录与最终证据的区分见 [教程证据索引](evidence/tutorial/README.md)。无尚未解决的工程检查失败；自动输入不替代人工新手体验，3–5 分钟学习目标、手感、平衡及试听仍待验证，未标记 P9 完整完成。

## 待完成项目

- 人工标准局的 4–6 分钟和平衡反馈；三难度初次玩家体验。
- 教程首次学习的理解程度、3–5 分钟目标与人工手感。
- 音量与频繁同时效果的主观试听。
- 完整操作演示录像和最终评价 Word 报告；Markdown 内容已在 evaluation-report.md，原模板不改。
- P9 最终验收通过后才创建完成该阶段的本地提交；当前候选成果不替代发布门槛。
