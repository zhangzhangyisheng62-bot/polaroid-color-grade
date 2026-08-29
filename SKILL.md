---
name: polaroid-color-grade
description: 将任意照片转换为 1980s-1990s Polaroid SX-70 / 600 复古 instant-film 风格。纯本地 Pillow+numpy 处理，支持色调曲线、色彩偏移、柔焦、化学颗粒与经典白边相纸。
---

# polaroid-color-grade

把上传的照片变成「从旧家庭相册里翻出来的宝丽来」：

- 暗部抬升为**暖棕 / 橄榄**（v2 修正：对照 7 张参考图，实际暗部是暖色不是蓝绿）
- 高光压缩成奶油象牙色
- 整体**统一暖底**（sepia/peach 质感），中调带 dusty brown / faded yellow
- 整体饱和度降低约 20%（v2：从 35% 下调，颜色仍鲜明）
- 降低清晰度 + 双半径柔焦漫射，梦幻怀旧感
- **halation 光晕**（v2 新增）：亮区暖色洇散
- 极轻微暖色有机颗粒（v2：幅度降约 60%，去掉单像素白噪声，中调为主）
- 柯达 Portra 400 风格**细颗粒层**（v2.1 新增，v2.2 增强 10%）：全分辨率噪声 + 0.5px 柔化，细密均匀、可感知不脏（独立幅度，平坦区约 ±2.3/255 灰阶）
- 少量自然轻微的白色小划痕（v2：3-6 条直线，10-80 px，1 px 宽，低透明度）
- v2.3 新增 **2-3 条不规则弯曲刮痕**：随机游走折线（每段方向随机偏转形成自然弧度，40-130 px、1 px 宽），与直线划痕叠加
- 添加经典 Polaroid 暖白边框（#F8F6F1），**宽度为短边 10%**，底部约 1.8 倍厚，边缘轻微老化发黄
- **保持原图宽高比**（如 3:4 的图输出仍为 3:4 + 白框，不裁剪不变形）

纯本地处理，不调用任何 API。**当前版本 v2.3**（经 11 张实测图验证，用户确认满意）。

> **回滚**：各历史版本（v1 → v2 → v2.3）都保留在 git 历史里，`git log` 即可回退。

## 依赖

```bash
pip install pillow numpy
```

## 用法

```bash
# 基础用法（输出到 ~/Downloads/Polaroid/<原名>_polaroid.jpg）
python3 "$SKILL_PATH/polaroid_grade.py" --input "原图.jpg"

# 指定输出路径
python3 "$SKILL_PATH/polaroid_grade.py" --input "原图.jpg" --output "宝丽来.jpg"

# 调整效果强度与颗粒
python3 "$SKILL_PATH/polaroid_grade.py" --input "原图.jpg" --strength 1.2 --grain 0.8

# 不要白边（只做调色）
python3 "$SKILL_PATH/polaroid_grade.py" --input "原图.jpg" --no-frame
```

## 参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `--input` | 输入图片路径 | 必填 |
| `--output` | 输出图片路径 | `~/Downloads/Polaroid/<原名>_polaroid.jpg` |
| `--strength` | 整体效果强度，范围 `0.0-1.5` | `1.0` |
| `--grain` | 化学颗粒强度，范围 `0.0-1.5` | `1.0` |
| `--scratches` | 白色划痕强度，范围 `0.0-1.5`（`--no-scratches` 直接关闭） | `1.0` |
| `--no-scratches` | 不添加白色划痕 | 不启用 |
| `--no-frame` | 不添加 Polaroid 白边 | 不启用 |
| `--size` | 长边缩放到的像素值（短边按原比例），不改原图宽高比；填 `0` 或负数按原尺寸处理 | `1024` |

## 输出示例

参考风格关键词：

-  late 1980s – early 1990s Polaroid SX-70 / 600
-  lifted warm blacks, compressed highlights
-  creamy ivory highlights, warm brown shadows, unified sepia base
-  halation glow around bright areas
-  soft indoor ambient light, melancholic nostalgia
-  subtle warm chemical grain, instant-film frame
