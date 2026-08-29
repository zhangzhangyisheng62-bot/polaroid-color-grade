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
- v2.4：**固定 3 条**不规则弯曲的自然刮痕（随机游走折线，每段方向随机偏转形成自然弧度，40-130 px、1 px 宽，偏白色）
- 添加经典 Polaroid 暖白边框（#F8F6F1），**宽度为短边 10%**，底部约 1.8 倍厚，边缘轻微老化发黄
- v2.4 新增**照片/白框衔接内阴影**：真实宝丽来的显影乳剂面略低于白框压边，白框内沿会在照片上投下一圈极细阴影 —— 让照片是"嵌进"相纸的，而不是平贴拼接。渗透深度**固定 30 px（与输入分辨率无关）**，光从上方来所以**上边最深、左右次之、下边最浅**，衰减经高斯羽化，边缘柔和无生硬边界，阴影偏暖棕
- **保持原图宽高比**（如 3:4 的图输出仍为 3:4 + 白框，不裁剪不变形）

纯本地处理，不调用任何 API。**当前版本 v2.4**（经 11 张实测图验证，用户确认满意）。

> **回滚**：
> - v2.3（无衔接阴影、4-5 条刮痕）保存在 `polaroid_grade_v2.3.bak`
> - v1 保存在 `polaroid_grade_v1.py.bak`
>
> 需要回到旧参数，把对应 `.bak` 复制覆盖 `polaroid_grade.py` 即可。

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

# 不要白边（只做调色，衔接阴影自动失效）
python3 "$SKILL_PATH/polaroid_grade.py" --input "原图.jpg" --no-frame

# 保留白边但去掉衔接阴影
python3 "$SKILL_PATH/polaroid_grade.py" --input "原图.jpg" --no-frame-shadow

# 加重衔接阴影
python3 "$SKILL_PATH/polaroid_grade.py" --input "原图.jpg" --frame-shadow 1.3
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
| `--frame-shadow` | 照片/白框衔接阴影强度，范围 `0.0-1.5`（`--no-frame-shadow` 直接关闭） | `1.0` |
| `--no-frame-shadow` | 不添加衔接阴影 | 不启用 |
| `--no-frame` | 不添加 Polaroid 白边（此时衔接阴影自动失效） | 不启用 |
| `--size` | 长边缩放到的像素值（短边按原比例，不改宽高比）；`0` 或负数 = 保持原图分辨率 | `0`（原图分辨率） |
| `--quality` | JPEG 质量 `1-100`，越大文件越大、细节越多 | `95` |

## 典型工作流（配合 AI 图生图）

可以先用本技能把原图调成 Polaroid 色调，再把结果作为图像生成模型的输入图（图生图），
让模型在保持风格的基础上重绘或延展画面。

```bash
# Step 1: Polaroid 调色
python3 "$SKILL_DIR/polaroid-color-grade/polaroid_grade.py" \
  --input "原图.jpg" \
  --output "polaroid_原图.jpg"

# Step 2: 把 polaroid_原图.jpg 作为你所用图像模型的输入图
```

> 提示：如果想先「稳定风格」再让 AI 发挥，可以用 `--strength 0.9 --grain 0.6` 做较克制的预处理，避免颗粒被 AI 过度放大。

## 输出示例

参考风格关键词：

-  late 1980s – early 1990s Polaroid SX-70 / 600
-  lifted warm blacks, compressed highlights
-  creamy ivory highlights, warm brown shadows, unified sepia base
-  halation glow around bright areas
-  soft indoor ambient light, melancholic nostalgia
-  subtle warm chemical grain, instant-film frame
