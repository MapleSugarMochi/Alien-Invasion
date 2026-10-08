# 关卡 1 教程实现证据

日期：2026-10-08。环境：Windows 11，Python 3.13.9，pygame 2.6.1，真实 SDL `windows` 后端。检查使用隔离偏好，不改玩家保存的设置。自动输入与人工手感验收分开。

## 最终验证

| 文件／目录 | 内容与结果 |
|---|---|
| `tests.txt` | 84 项 unittest 全部通过，其中 20 项教程规则与公开输入完整流程测试 |
| `window/check.json` | 英语完整教程、中文方向键 + M/N/B/P 改键教程、英语错误恢复路线；全部完成 1–8 步。最终实战均为 9／2／1 共 12 架，无 Boss |
| `window/*-run.json` | 完整步骤、真实拾取／命中／能量／激活／支援日志。公开输入流程不直接写生命、充能、能量或任务完成状态 |
| `window/*.png` | 八步、Q/E、支援、第二波、完成页、暂停设置与错误恢复画面；工具检测文本边界和教学面板截断 |
| `window/idle-check.json` | 14 个中英文独立渲染场景，验证 15 秒提醒与 30 秒方向／范围辅助无截断。仅为排版设置提示计时，区别于不写进度的完整公开输入路线 |
| `realtime-final/standard-pilot-run.json` | 中文实时完整教程：70.757 游戏秒，77.402 墙钟秒，4678 帧，平均 60.44 FPS，计算耗时 P95 6.049ms，零重试，全部八步完成 |
| `comparison.json` | 关卡 2 的 475 条 events 和关卡 3 的 555 条 events，均与教程改动前完整记录逐条相同；战斗结果相同 |
| `level-2-regression/standard-pilot-run.json` | 中文标准难度：162.000 秒、27400 分、109 击杀、118 架、Boss 2400，完整胜利 |
| `level-3-regression/standard-pilot-run.json` | 英语标准难度：182.850 秒、31900 分、131 击杀、142 架、Boss 3360，完整胜利 |
| `levels/check.json` | 三入口、中英文、教程固定难度、正式难度、移动射击、暂停设置、重开返回和退出通过 |
| `base/`、`language/`、`settings/` | 原基础操作窗口、双语排版、设置／保存／重复键位回归通过；普通战斗检查显式使用关卡 2 |

错误路线依次故意击碎陨石、漏拾回血补给至过期、导弹激活后不射击、电弧在范围外射击、综合实战主动碰撞至死亡。四次当前步骤重试后继续完成；过期补给重新投放，无需重试。失败实战的日志保留，最后一次第八步开始后的数量才是成功两波的数量。

## 早期检查与限制

`flow-en/` 和 `realtime/` 保存最终停火／提示修订前的早期运行，作为过程记录，不用于替代上述最终验证。两个正式关卡初次回归在反复覆盖同名 PNG 时写入失败，未计为通过；`play_check.py` 改为阶段截图附加帧号后完整重跑，结果为目录内最新 JSON 和带帧号截图。不带帧号的阶段截图是初次失败的残留，保留以说明过程，不作为完整运行证明。只能确认此次重跑通过，不能由此断言 Windows 文件占用的具体来源。

84 项测试及语法检查均通过；基础窗口检查最初仍以数字键 1 验证简单正式难度，已修正为数字键 2 后完整通过。评分原件、报告模板与依赖未修改。

自动玩家熟悉任务且持续执行操作，约 70 游戏秒不代表新手首次学习时长。3–5 分钟仍为人工目标；实际手感、理解程度、平衡和试听尚待人工验收。

## 复现

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m compileall -q main.py game.py entities.py render.py settings.py localization.py preferences.py tutorial.py waves.py weapons.py geometry.py resources.py tests tools
.\.venv\Scripts\python.exe tools/check_tutorial.py --output docs/evidence/tutorial/window
.\.venv\Scripts\python.exe tools/play_check.py --level 1 --language zh-CN --realtime --output docs/evidence/tutorial/realtime-final
.\.venv\Scripts\python.exe tools/play_check.py --level 2 --language zh-CN --output docs/evidence/tutorial/level-2-regression
.\.venv\Scripts\python.exe tools/play_check.py --level 3 --output docs/evidence/tutorial/level-3-regression
```
