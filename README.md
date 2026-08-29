# polaroid-color-grade

把任意照片一键调成 **1980s–1990s Polaroid SX-70 / 600 复古拍立得**风格。
纯本地 Pillow + numpy 实现，不调用任何 API、不联网、不需 GPU。

![python](https://img.shields.io/badge/python-3.8%2B-blue) ![pillow](https://img.shields.io/badge/pillow-%3E%3D9.0-orange) ![license](https://img.shields.io/badge/license-MIT-green)

## 效果特征

| 环节 | 处理 |
| --- | --- |
| 暗部 | 抬起成**暖棕 / 橄榄**（不是常见的冷蓝绿） |
| 高光 | 压缩为**奶油象牙色** |
| 整体 | 统一**暖底**（sepia / peach），中调 dusty brown / faded yellow |
| 氛围 | halation 光晕（亮区暖色洇散）+ 双半径柔焦 + 轻微降清晰度 |
| 色彩 | 饱和度降低约 20% |
| 质感 | 极轻暖色粗颗粒 + 柯达 Portra 400 风格细颗粒 |
| 缺陷 | **3 条**不规则弯曲的偏白色细刮痕（线宽/长度/柔化随分辨率等比缩放，适度可见） |
| 相纸 | 经典 Polaroid 暖白边框 `#F8F6F1`，短边 10% 宽，底边 1.8 倍厚，边缘轻微老化发黄 |
| 衔接 | **照片/白框衔接内阴影**：乳剂面略低于白框，内沿投下极细暖色阴影，固定 30px 渗透深度（与分辨率无关），上深下浅、边缘柔和 |
| 构图 | **保持原图宽高比**，不裁剪不变形 |

风格参数是严格对照 7 张真实老拍立得照片逐项校准出来的，不是凭感觉调的曲线。

### 关于衔接阴影

真实宝丽来的显影乳剂面比四周白框的压边**略低一点**，白框内沿会在照片上投下一圈极细阴影。
没有这层阴影，照片看起来就像直接"贴"在白框上，有明显的拼接感。

实现上按到四边的距离生成阴影强度图再叠回照片：

- **渗透深度固定 30 px**（绝对像素）——任意分辨率的输入，阴影的宽度与浓淡完全一致
- **方向性**：光从上方来 → 上边权重 `1.00` > 左右 `0.55` > 下边 `0.22`
- 衰减指数 `1.7` + 高斯羽化，边缘柔和无生硬边界；四角叠加值封顶，不出现暗块
- **暖色阴影**（蓝通道压得最多），与整体暖底一致，不发灰发脏

实测衰减曲线（边缘 → 向内）：

| 距边缘 px | 1 | 3 | 5 | 8 | 11 | 15 | 20 | 25 | 30 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 压暗 | 19.3% | 18.4% | 17.0% | 14.1% | 11.3% | 7.4% | 3.9% | 1.5% | 0% |

## 效果对比

![before-after](examples/before-after.jpg)

> 左：原图；右：Polaroid 调色后。保留原图宽高比，暗部变暖棕、高光压成奶油色，并添加暖白相纸边框。

### 照片与白框的衔接阴影

![frame-shadow-detail](examples/frame-shadow-detail.jpg)

> 左上角衔接处放大。照片边缘有一条极细的暖色暗部并平滑向内衰减——没有它，照片看起来就是直接"贴"在白框上的。

## 安装

```bash
git clone https://github.com/zhangzhangyisheng62-bot/polaroid-color-grade.git
cd polaroid-color-grade
pip install -r requirements.txt
```

依赖只有两个：`Pillow>=9.0`、`numpy>=1.21`。

## 命令行用法

```bash
# 基础用法，输出到 ~/Downloads/Polaroid/<原名>_polaroid.jpg
python polaroid_grade.py --input "原图.jpg"

# 指定输出路径
python polaroid_grade.py --input "原图.jpg" --output "宝丽来.jpg"

# 调整效果强度与颗粒
python polaroid_grade.py --input "原图.jpg" --strength 1.2 --grain 0.8

# 只调色，不要白边（衔接阴影自动失效）
python polaroid_grade.py --input "原图.jpg" --no-frame

# 保留白边，但去掉衔接阴影
python polaroid_grade.py --input "原图.jpg" --no-frame-shadow

# 加重衔接阴影
python polaroid_grade.py --input "原图.jpg" --frame-shadow 1.3

# 输出大图（长边 2048）
python polaroid_grade.py --input "原图.jpg" --size 2048
```

### 参数

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `--input` / `-i` | 输入图片路径 | 必填 |
| `--output` / `-o` | 输出路径 | `~/Downloads/Polaroid/<name>_polaroid.jpg` |
| `--strength` / `-s` | 整体效果强度 `0.0–1.5` | `1.0` |
| `--grain` / `-g` | 化学颗粒强度 `0.0–1.5` | `1.0` |
| `--scratches` | 划痕强度 `0.0–1.5` | `1.0` |
| `--no-scratches` | 不加划痕 | 关闭 |
| `--frame-shadow` | 照片/白框衔接阴影强度 `0.0–1.5` | `1.0` |
| `--no-frame-shadow` | 不加衔接阴影 | 关闭 |
| `--no-frame` | 不加 Polaroid 白边（此时衔接阴影自动失效） | 关闭 |
| `--size` | 长边缩放像素值（按比例缩放，不改宽高比）；`0` 或负数 = 保持原图分辨率 | `0`（原图分辨率） |
| `--quality` | JPEG 质量 1-100，越大文件越大、细节越多 | `95` |

## 作为 Python 库调用

```python
from polaroid_grade import process

process(
    "原图.jpg",
    "宝丽来.jpg",
    strength=1.0,
    grain=1.0,
    scratches=1.0,
    add_frame=True,
    size=0,           # 保持原图分辨率；0 或负数 = 不缩放
    frame_shadow=1.0, # 照片/白框衔接阴影强度
)
```

内部每一步也都是独立函数，可以单独组合使用：

```python
from PIL import Image
import numpy as np
from polaroid_grade import (
    apply_tone_curve, apply_color_grade, add_halation,
    reduce_clarity, add_grain, add_scratches,
    add_vignette_and_age, add_paper_texture, add_polaroid_frame,
    add_inner_edge_shadow,
)

arr = np.asarray(Image.open("原图.jpg").convert("RGB"), dtype=np.float32) / 255.0
arr = apply_tone_curve(arr, strength=1.0)
arr = apply_color_grade(arr, strength=1.0)
arr = add_halation(arr, strength=1.0)
arr = reduce_clarity(arr, strength=1.0)
arr = add_grain(arr, strength=1.0)
arr = add_scratches(arr, strength=1.0)
# 衔接阴影必须在「加白框之前」作用于照片区
arr = add_inner_edge_shadow(arr, strength=1.0)
arr = add_vignette_and_age(arr, strength=1.0)
```

## 作为 AI Agent Skill 使用

仓库里的 `SKILL.md` 是给 AI Agent（WorkBuddy / Claude Code 等）读的技能描述。
把整个目录放进 Agent 的 skills 目录即可被调用：

```bash
# WorkBuddy
cp -r polaroid-color-grade ~/.workbuddy/skills/

# Claude Code
cp -r polaroid-color-grade ~/.claude/skills/
```

## 处理流程

```
原图 → 保持比例缩放 → 色调曲线（抬黑位 / 压高光）→ split-tone 调色
    → halation 光晕 → 降清晰度 → 粗颗粒 + Portra 400 细颗粒
    → 划痕 → 衔接内阴影 → 暗角与做旧 → 相纸纹理 → Polaroid 白边 → 输出
```

## 常见问题

**暗部不够暖？**
`--strength` 调高（1.2–1.4）。如果原图暗部本身严重偏蓝，暖化会被部分抵消，可先把原图稍微提亮。

**画面太"脏"？**
`--grain 0.5` 降低颗粒，`--scratches 0` 或 `--no-scratches` 去掉划痕。

**不想要照片与白框之间的阴影？**
`--no-frame-shadow`（或 `--frame-shadow 0`）。想要更明显的立体感就调高，例如 `--frame-shadow 1.3`。

**小图上的阴影会不会太宽？**
不会。渗透深度是**固定 30 像素**，与输入分辨率无关，所以任意尺寸的照片阴影宽度和浓淡都一致（极小图另有安全上限，避免阴影吃掉画面）。

**想保留原图分辨率？**
`--size 0` 会跳过缩放（按原尺寸处理，大图会明显变慢）。

## 许可

MIT License，详见 [LICENSE](LICENSE)。
