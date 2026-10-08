# 资源清单

美术更新日期：2026-10-08。开发者确认极简精密科幻预览后，使用内置 imagegen 重构为独立透明精灵与背景；图标和特效为 Pygame 原生绘图。音效沿用 2026-10-07 的 Python 数学合成版本。未使用外部游戏素材；未附带开发者尚未提供的 BGM。

## 图像

已确认预览保存在 `../docs/art-approved.png`；风格规范见 [art-direction.md](../docs/art-direction.md)，完整生成提示见 [art-generation.md](../docs/art-generation.md)。生成文件原样保存；Resources 根据 alpha 外接框等比适配显示画布，不依赖图集网格、不拉伸对象。母舰原图朝下，加载时统一朝上，运行时再旋转。所有碰撞仍按 settings/entities 的原有圆形范围计算。

| 文件／用途 | 原始尺寸／运行画布 | 来源／状态 |
|---|---|---|
| `images/craft/player.png` | 1295×1214／64×64 | imagegen，白色玩家机，已整合 |
| `images/craft/scout.png` | 1278×1230／48×48 | imagegen，叉形侦察机，已整合 |
| `images/craft/shooter.png` | 1312×1199／64×64 | imagegen，双炮射手机，已整合 |
| `images/craft/heavy.png` | 1312×1199／96×96 | imagegen，宽装甲重型机，已整合 |
| `images/craft/boss.png` | 1774×887／384×192 | imagegen，层叠装甲母舰；实际圆形半径仍为 60 |
| `images/craft/meteor_small.png` | 1315×1197／64×64 | imagegen，分面陨石，已整合 |
| `images/craft/meteor_large.png` | 1312×1199／96×96 | imagegen，分面陨石，已整合 |
| `images/space.png` | 1672×941／等比覆盖 1280×720 | imagegen，安静星空与左侧行星边缘 |
| 回血／导弹／电弧补给 | 各 48×48 | art.py 原生绘图，独立外形与图案 |
| Q／E／X 图标 | 各 30×30 | 同一图标规则缩放缓存，三格刻度／能量条 |
| 十字／锁定角框 | 32×32／按目标半径 | art.py、render.py 细线绘图 |
| 命中、爆炸、弹丸、尾焰、电弧、支援 | 按真实对象与计时定位 | render.py 原生绘图，不读取游戏随机源 |

工具为内置 imagegen，七个对象各生成一次透明 PNG，背景单独生成。原始输出在工具默认目录留存，项目使用上述相对路径副本。运行已使用这些文件；旧像素风 `images/sprite-atlas.png` 与 `docs/art-prompt.md` 留作历史备份，不参与当前加载。

## 声音

所有 `audio/sfx/*.wav` 为 44.1 kHz、单声道、16 位 PCM。通过 `tools/build_audio.py` 可复现；峰值设计 ≤0.32，默认音效音量 45%，每类一个独立通道限制叠加。

| 文件 | 秒 | 触发 |
|---|---:|---|
| bullet.wav | .05 | 基础子弹实际射击 |
| missile.wav | .18 | 导弹实际发射 |
| explosion.wav | .35 | 导弹命中爆炸 |
| arc.wav | .12 | 电弧实际射击，包括空击 |
| pickup.wav | .15 | 实际拾取 |
| hurt.wav | .15 | 有效玩家受击 |
| lock.wav | .10 | 支援有目标的一轮锁定 |
| support.wav | .40 | 支援有有效目标命中 |
| phase.wav | .50 | Boss 开始阶段过渡 |

`audio/music/bgm.ogg` 为可选开发者提供文件；放入后循环加载，需记录来源与使用许可。目前未提供，启动照常运行。音效与音乐音量可分别在主菜单或暂停菜单调整；音频设备无法初始化时静音运行。

## 字体与许可说明

中文优先使用运行系统的 Microsoft YaHei 常规字重，依次回退 SimHei、SimSun，再回退 Pygame 默认字体。系统索引选中 msyhl.ttc 时，若同目录存在 msyh.ttc，优先用后者。没有复制或分发系统字体文件；本机已实测中文与英文。其他系统缺少中文字库时可能不能正确显示中文，需自行提供合法安装的中文字体。

生成图片和原创图形／音效随本项目使用，来源已记录；此说明不替代任何课程或发布平台对生成内容的披露要求。原始评分材料与报告模板未修改。
