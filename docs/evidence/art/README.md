# 美术重构验证证据

2026-10-08。目标与规范见 [../../art-direction.md](../../art-direction.md)。已确认参考为 [../../art-approved.png](../../art-approved.png)，完整生成提示为 [../../art-generation.md](../../art-generation.md)。

## 完成的检查

- tests.txt：84 项规则测试全通过；全模块语法检查通过。
- window/：真实 SDL 窗口的移动、瞄准、边界、射击、暂停与退出。
- language/、settings/、levels/：中英文文字及按钮边界、字体字形、重绑定／共享键／音量／保存、三关卡入口。
- resources/resources.png：独立透明精灵与图标；check_resources 实际载入及播放音效，音量读回与格式／峰值核对通过，实际音频后端可用。
- tutorial/check.json：英语、中文改键与错误恢复三条完整八步路线，公开注入输入，不改写进度／生命／充能。
- level-2-verified/、level-3-verified/：标准完整胜利；comparison.json 将事件与上一版本逐条对照，分别 475／555 条相同。
- failure/：关卡 3 中文自然失败，29.400 游戏秒。
- realtime/：中文教程，零重试完成；平均 58.78 FPS，计算 P95 5.425ms。

## 过程记录与限制

level-2/、level-3/ 为首次停滞运行的部分截图，没有完整 JSON，不作为通过证据。相关进程主动结束后，关卡 2 通过启用 faulthandler 的诊断重跑完成，关卡 3 独立重跑完成。偶发停滞原因尚未定位，项目以前也记录过同类现象。

所有完整流程均使用真实 Windows SDL 窗口和公开自动输入。自动结果不替代人工对美术、手感、平衡和声音的评价，原 P9 待完成项见 [../../acceptance.md](../../acceptance.md)。
