# 极简精密科幻美术生成记录

2026-10-08。使用内置 imagegen，未使用 CLI 或外部素材库。开发者确认的是 `exec-f709c0ac-41ab-44b5-98c8-0b183b76522d.png`，项目内副本为 [art-approved.png](art-approved.png)，包含层叠装甲的宽母舰。后续简化母舰的概念稿未采用。

## 正式透明精灵

以下共用提示与每个对象的后缀合并，分别调用一次内置 imagegen。参考图均为已确认预览，`transparent_background=true`。原始生成 PNG 原样复制进 `assets/images/craft/`；加载时根据 alpha 外接框等比适配，未重新绘制生成素材。

共用提示：

```text
Use case: background-extraction. Asset type: production transparent PNG sprite for the existing 2D top-down space shooter Alien Invasion. The supplied image is the USER-APPROVED art style and exact spacecraft design reference. Extract and faithfully recreate ONLY the requested single object on a genuinely transparent background. ONE object, centered with at least 10 percent transparent padding on every edge. Strict orthographic top-down view, original ship nose facing UP. Match the reference's matte graphite slate planar armor, carefully drawn subtle beveled edges and shading, precision sci-fi proportions, minimal low-saturation accent slits. Smooth polished 2D illustration, not pixel art, not glossy CGI. No scene, no text, no UI, no drop shadow, no ground, no grid, no other assets, no border. Do not add micro-details, jewels or neon glow. Do not include an engine flame: the game draws animated engine exhaust. Preserve a complete unclipped silhouette. Requested object:
```

### player.png

```text
the SMALL WHITE PLAYER FIGHTER in the bottom strip at far left. Pale ceramic-white arrowhead twin wings, narrow graphite central fuselage, one tiny cyan engine inset. Faithfully preserve the reference design, compact and elegant. Nose UP.
```

### scout.png

```text
the SMALL DARK SCOUT in the bottom strip, second from the left. A dark graphite crescent/fork shape, two swept pointed side claws and one narrow soft-coral central light slit. Faithfully preserve the reference design. Nose UP.
```

### shooter.png

```text
the DARK TWIN-BARREL GUNSHIP in the bottom strip, third from left. Narrow rectangular slate-gray craft with two long parallel cannons, compact center and two short side wings, one small coral center light. Faithfully preserve the reference design. Nose UP.
```

### heavy.png

```text
the BROAD DARK ARMORED HEAVY in the bottom strip, fourth from left. Wide diamond/kite graphite hull made of a few large plates, pointed nose, broad short side armor, one vertical muted-coral center slit. Faithfully preserve the reference design. Nose UP.
```

### boss.png

```text
the LARGE COMPLEX WIDE MOTHERSHIP in the bottom strip center and in the upper-center gameplay scene. IMPORTANT: retain this user's selected MORE COMPLEX layered armored carrier design, NOT a simplified two-wing plane. Broad symmetrical graphite carrier with central pointed spear fuselage, overlapping swept slate armor plates, angular stepped wings, a thin long coral reactor slit and two small coral wing insets. Preserve the reference silhouette and major armor layering, eliminate only illegible microtexture. WIDE 2:1 aspect object, fully in frame with padding, use a landscape canvas. Nose UP.
```

### meteor_small.png

```text
one SMALL FACETED DARK GRAY ASTEROID like the left rock in the gameplay reference. Compact asymmetric rock with five to eight large visible shaded facets, low contrast textured dark slate surfaces, lighter edges for visibility, no bright glow. Single rock on transparency.
```

### meteor_large.png

```text
one LARGE FACETED DARK GRAY ASTEROID like the right rock in the gameplay reference. Rugged asymmetric broad rock with large dark slate shaded facets and a little rocky surface texture, illuminated subtle cool-gray top edges. No fragments, no bright glow. Single rock on transparency.
```

## 背景

输出 `assets/images/space.png`，参考同一预览，`transparent_background=false`，使用完整提示：

```text
Use case: precise-object-edit. Asset type: production BACKGROUND ONLY for a 1280x720 2D top-down sci-fi shooter, 16:9 landscape. The user-approved reference image specifies the visual style. Recreate just its quiet dark space BACKGROUND from the top gameplay scene, removing ALL spacecraft, meteors, projectiles, HUD, text, icons, crosshair, effects, dividing line and bottom asset strip. Keep the calm almost-black navy #0B1118, soft deep slate atmospheric falloff, a distant large shadowed planet edge cropped at the FAR UPPER LEFT (occupying no more than the leftmost quarter), delicate faint cool-gray rim, very subtle hazy texture. Most of the scene must be uninterrupted very dark space, with only a handful of extremely dim stars; additional sparse small stars are drawn at runtime. No bright nebula, no blue bloom, no brilliant sun, no large foreground rocks, no grid, no perspective, no new objects. Match the reference's premium minimal restrained mood. This is a clean usable empty scenery layer. Landscape 16:9 composition.
```

## 原生绘图资源

`art.py` 统一色板、图标比例、线宽和锁定角标；`render.py` 绘制弹丸、尾焰、命中、连锁电弧、支援飞行、HUD、菜单和教程。简单图形使用 Pygame 原生绘图，以保持可编辑性和实际目标位置精度。图标先以三倍尺寸绘制再缩小，避免小尺寸斜线锯齿。

## 历史版本

旧像素风图集及其提示保存在 Git 历史（P8 提交 `b2ea1f9`）。当前运行与候选包使用独立精灵和原生图标。
