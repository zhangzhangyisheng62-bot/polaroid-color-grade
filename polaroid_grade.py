#!/usr/bin/env python3
"""
polaroid-color-grade (v2.3)
===========================
将任意照片转换为 1980s-1990s Polaroid SX-70 / 600 复古 instant-film 风格。

风格要点（严格对照 7 张真实参考图校准）：
- 暗部抬起为暖棕 / 橄榄（v1 曾错误地推成蓝绿）
- 高光压缩成奶油象牙色，全图统一暖底（sepia / peach），不再冷暖分裂
- halation 光晕：亮区暖色洇散
- 饱和度降低约 20%，降清晰度 + 双半径柔焦
- 极轻的暖色粗颗粒 + 柯达 Portra 400 风格细颗粒
- 每张图 4-5 处不规则弯曲的自然小刮痕（随机游走折线，每条弯曲程度随机）
- 经典 Polaroid 暖白边框 #F8F6F1（短边 10%，底边 1.8 倍厚）
- 保持原图宽高比，不裁剪、不变形

回滚: polaroid_grade_v1.py.bak 为 v1 版本

依赖:
    pip install pillow numpy

用法:
    python polaroid_grade.py --input "原图.jpg"
    python polaroid_grade.py --input "原图.jpg" --output "out.jpg" --strength 1.0
"""
import argparse
import os
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageFilter, ImageDraw
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("请先安装: pip install pillow numpy")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 常量 / 风格参数
# ---------------------------------------------------------------------------
POLAROID_BG = (248, 246, 241)   # #F8F6F1 略中性暖白边框（v2: 稍亮稍冷于 v1 的 #F7F5F0）


def ensure_rgb(img: Image.Image) -> Image.Image:
    """统一转为 RGB，RGBA 则先合成到暖白底。"""
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, POLAROID_BG)
        bg.paste(img, mask=img.split()[3])
        return bg
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def resize_keep_ratio(img: Image.Image, size: int = 1024) -> Image.Image:
    """保持原始宽高比，按长边缩放到 size，不裁剪内容。size<=0 时保持原尺寸。"""
    w, h = img.size
    if size is None or size <= 0:
        return img
    if w >= h:
        scale = size / w
        new_size = (size, max(1, int(round(h * scale))))
    else:
        scale = size / h
        new_size = (max(1, int(round(w * scale))), size)
    return img.resize(new_size, Image.LANCZOS)


def apply_tone_curve(arr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    Polaroid 特征曲线：
    - 黑位抬起（抬向暖灰，配合后续暖色分级）
    - 高光压缩
    - 轻微降对比，保持平滑过渡
    """
    x = np.linspace(0, 1, 256)

    black_lift = 0.05 + 0.03 * strength     # v2: 0.10 → 0.08（黑位略压暗，避免灰平）
    white_compress = 0.92 - 0.03 * strength
    mid_shift = 0.51 + 0.015 * strength

    y = np.zeros_like(x)
    shadows = x < 0.5
    highs = ~shadows

    y[shadows] = black_lift + (mid_shift - black_lift) * (2 * x[shadows]) ** 1.35
    y[highs] = mid_shift + (white_compress - mid_shift) * (1 - (2 * (1 - x[highs])) ** 1.5)

    y = np.clip(y, 0, 1)

    lut = (y * 255).astype(np.uint8)
    arr_u8 = np.clip(arr * 255, 0, 255).astype(np.uint8)
    r = np.interp(arr_u8[:, :, 0].flatten(), np.arange(256), lut).reshape(arr.shape[:2])
    g = np.interp(arr_u8[:, :, 1].flatten(), np.arange(256), lut).reshape(arr.shape[:2])
    b = np.interp(arr_u8[:, :, 2].flatten(), np.arange(256), lut).reshape(arr.shape[:2])
    return np.stack([r, g, b], axis=2) / 255.0


def apply_color_grade(arr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    v2 色彩特征（严格对照参考图）：
    - 暗部：暖棕/橄榄（R≥G>B），不再是蓝绿
    - 中调：dusty brown / faded yellow
    - 高光：奶油象牙（保持）
    - 整体统一暖底
    - 饱和度降低 ~20%（v1 为 35%）
    - 肤色保护 + 暖化
    """
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]

    shadow_mask = np.clip(1.0 - lum * 2.5, 0, 1) ** 1.2
    highlight_mask = np.clip((lum - 0.55) * 2.5, 0, 1) ** 1.2

    # v2: 暗部 → 暖深棕/橄榄（参考图实际表现）
    shadow_tint = np.zeros_like(arr)
    shadow_tint[:, :, 0] = 0.11  # R 最高
    shadow_tint[:, :, 1] = 0.09  # G 略低
    shadow_tint[:, :, 2] = 0.07  # B 最低 → 暖棕

    # 高光：奶油象牙（参考图一致，保留）
    highlight_tint = np.zeros_like(arr)
    highlight_tint[:, :, 0] = 0.95
    highlight_tint[:, :, 1] = 0.90
    highlight_tint[:, :, 2] = 0.78

    # 暗部混合：向暖棕偏移
    shadow_blend = (0.28 + 0.08 * strength) * strength
    arr = arr * (1 - shadow_blend * shadow_mask[:, :, None]) + shadow_tint * (shadow_blend * shadow_mask[:, :, None])

    # 高光混合：向奶油象牙偏移
    highlight_blend = 0.32 * strength
    arr = arr * (1 - highlight_blend * highlight_mask[:, :, None]) + highlight_tint * (highlight_blend * highlight_mask[:, :, None])

    # 中调：dusty brown / faded yellow（钟形掩膜）
    mid_mask = np.exp(-((lum - 0.5) / 0.28) ** 2)
    color_contam = np.array([0.08, 0.05, -0.02], dtype=np.float32) * strength
    arr = np.clip(arr + mid_mask[:, :, None] * color_contam, 0, 1)

    # v2: 饱和度降低 ~20%（v1: 35% 过强，参考图颜色仍鲜明）
    sat_reduce = (0.13 + 0.07 * strength)
    gray = np.mean(arr, axis=2, keepdims=True)
    arr = gray + (1 - sat_reduce) * (arr - gray)

    # v2: 降饱和后补偿暖色（v1 是补冷色，方向反了）
    warm_comp = np.array([0.015, 0.005, -0.018], dtype=np.float32) * strength
    arr = arr + (0.3 * shadow_mask + 0.7 * mid_mask)[:, :, None] * warm_comp

    # 肤色保护：暖化肤色
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    skin_mask = (
        (r > g) & (g > b) &
        (r > 0.25) & (r < 0.85) &
        (np.abs(r - g) < 0.18) &
        (np.abs(g - b) < 0.15)
    ).astype(np.float32)
    skin_warmth = np.array([0.035, 0.015, -0.025], dtype=np.float32) * strength
    arr = arr + skin_mask[:, :, None] * skin_warmth

    return np.clip(arr, 0, 1)


def add_halation(arr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    v2 新增：亮区暖色洇散（halation）。
    Polaroid 乳剂层的典型特征：高光周围有柔和暖色光晕。
    - 提取亮区（lum > 0.62）
    - 大半径高斯模糊
    - 以暖色 screen 混合，低透明度
    """
    img_pil = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), mode="RGB")
    lum = np.mean(arr, axis=2)

    # 亮区掩膜
    glow_mask = np.clip((lum - 0.62) / 0.25, 0, 1) ** 1.3

    # 大半径模糊做洇散（显式转 float，避免 numpy 标量问题）
    radius = float(6 + 8 * strength)
    blurred = img_pil.filter(ImageFilter.GaussianBlur(radius=radius))
    blurred_arr = np.array(blurred, dtype=np.float32) / 255.0

    # 洇散色：暖（奶油-橙之间）
    halo_tint = np.array([1.0, 0.88, 0.70], dtype=np.float32)

    # screen 混合: result = 1-(1-a)*(1-b)，只作用于亮区
    screen = 1 - (1 - arr) * (1 - halo_tint[None, None, :])
    amount = 0.16 * strength
    arr = arr * (1 - amount * glow_mask[:, :, None]) + screen * (amount * glow_mask[:, :, None])
    return np.clip(arr, 0, 1)


def reduce_clarity(arr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    v2 增强柔焦：更接近参考图的梦幻散景感。
    - 高斯半径加大，混合比提高
    - 保留中间调细节（低频模糊只在亮暗两端少一些）
    """
    img_pil = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), mode="RGB")

    # 双半径：细柔焦 + 稍粗漫射（注意：必须显式转 float，numpy 标量会让 PIL 报错）
    radius_fine = float(1.0 + 0.8 * strength)
    radius_glow = float(2.5 + 1.5 * strength)

    blurred_fine = img_pil.filter(ImageFilter.GaussianBlur(radius=radius_fine))
    blurred_glow = img_pil.filter(ImageFilter.GaussianBlur(radius=radius_glow))
    fine_arr = np.array(blurred_fine, dtype=np.float32) / 255.0
    glow_arr = np.array(blurred_glow, dtype=np.float32) / 255.0

    # v2: 混合比提高
    blend_fine = 0.30 + 0.10 * strength
    blend_glow = 0.10 + 0.06 * strength
    arr = arr * (1 - blend_fine) + fine_arr * blend_fine
    arr = arr * (1 - blend_glow) + glow_arr * blend_glow

    return np.clip(arr, 0, 1)


def _resize_float_noise(noise: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
    """把 float32 噪声图安全地缩放到目标尺寸。"""
    lo, hi = noise.min(), noise.max()
    if hi - lo < 1e-9:
        return np.zeros((target_h, target_w), dtype=np.float32)
    u8 = ((noise - lo) / (hi - lo) * 255).astype(np.uint8)
    resized = np.array(Image.fromarray(u8, mode="L").resize((target_w, target_h), Image.BILINEAR), dtype=np.float32)
    return resized / 255.0 * (hi - lo) + lo


def add_grain(arr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    v2 颗粒（严格对照参考图）+ v2.1 柯达 400 细颗粒：
    - 大/中颗粒：极细、暖色调（黄棕微粒）
    - v2.1 新增细颗粒层：柯达 Portra 400 风格，细密均匀轻微
      （全分辨率 + 0.5px 柔化，有胶片感无数字白斑）
    - 中调为主（v1 是暗部最重，与参考相反）
    - 分布不均程度减半
    """
    h, w, _ = arr.shape
    rng = np.random.default_rng()

    lum = np.mean(arr, axis=2)
    # v2: 钟形曲线，中调颗粒最明显，暗部干净
    mid_boost = np.exp(-((lum - 0.45) / 0.30) ** 2) * 0.7 + 0.3

    # 多层噪声模拟有机颗粒（v2: 去掉 h×w 全分辨率层）
    grain = np.zeros((h, w), dtype=np.float32)

    # 大颗粒（低频）
    coarse = rng.normal(0, 1, (max(1, h // 4), max(1, w // 4))).astype(np.float32)
    grain += _resize_float_noise(coarse, w, h) * 0.55

    # 中颗粒
    medium = rng.normal(0, 1, (max(1, h // 2), max(1, w // 2))).astype(np.float32)
    grain += _resize_float_noise(medium, w, h) * 0.45

    # v2.1 新增：柯达 400（Portra 400）风格细颗粒层
    # 细密、均匀、轻微：全分辨率噪声 + 0.5px 高斯柔化
    # → 紧致有机微粒，有胶片感但不产生数字单像素"白斑"
    # 注意：细颗粒有独立幅度（不与大/中颗粒共用 amp），
    # 否则会被二次衰减到不可见。
    fine = rng.normal(0, 1, (h, w)).astype(np.float32)
    fine_u8 = np.clip(fine * 40 + 128, 0, 255).astype(np.uint8)
    fine_soft = np.array(
        Image.fromarray(fine_u8, mode="L").filter(ImageFilter.GaussianBlur(radius=0.5)),
        dtype=np.float32,
    )
    fine = (fine_soft - 128.0) / 40.0  # 恢复 ~N(0,1) 尺度
    # 柔化会降低 std，重新归一化到单位标准差
    fine_std = float(fine.std())
    if fine_std > 1e-9:
        fine = fine / fine_std

    # 分布不均：v2 减半（sigma 0.25→0.12）
    uneven = rng.normal(1.0, 0.12, (max(1, h // 8), max(1, w // 8))).astype(np.float32)
    grain *= _resize_float_noise(uneven, w, h)
    grain *= mid_boost

    # v2: 大/中颗粒幅度 0.016 → 0.006（约 -62%）
    amp = (0.004 + 0.003 * strength)
    grain = grain * amp

    # v2.1: 细颗粒独立幅度（柯达 400 可感知水平）
    # 亮度加权比大/中颗粒更平缓（柯达细颗粒较均匀，中调略强）
    fine_weight = mid_boost * 0.5 + 0.5
    amp_fine = (0.0035 + 0.0045 * strength) * 1.10  # v2.2: 细颗粒 +10%
    fine = fine * amp_fine * fine_weight

    # v2: 暖色颗粒（R>G>B），参考图颗粒是黄棕不是冷白
    # 细颗粒色差更小（接近中性暖）
    color_grain = (
        np.stack([grain * 1.00, grain * 0.92, grain * 0.80], axis=2)
        + np.stack([fine * 1.00, fine * 0.96, fine * 0.90], axis=2)
    )

    return np.clip(arr + color_grain, 0, 1)


def add_scratches(arr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    自然小刮痕（v2.3 修复：等比还原旧版"刮痕↔图片"相对关系，大图依旧轻微）：
    - 线宽：旧版 1px / 1024 长边 → 按 max(w,h)/1024 等比（约 5px）
    - 长度：旧版 40-130px / 1024 → 等比为短边的 4%-13%
    - 透明度：0.20-0.38（适度可见，呈偏白色细痕；之前 0.06-0.14 过淡）
    - 每张图 4-5 条，全部不规则弯曲
    """
    h, w, _ = arr.shape
    rng = np.random.default_rng()

    # 分辨率缩放：以 1024 长边为基准，等比还原旧版相对尺寸
    scale = max(w, h) / 1024.0
    lw = max(1, int(round(scale)))              # 线宽等比（旧版 1px/1024）
    blur_r = max(0.4, 0.4 * scale)              # 柔化随分辨率
    base = min(w, h)

    n_scratches = int(rng.integers(4, 6))       # 4-5 条
    canvas = np.zeros((h, w), dtype=np.float32)

    for _ in range(n_scratches):
        x = float(rng.uniform(w * 0.08, w * 0.92))
        y = float(rng.uniform(h * 0.08, h * 0.92))
        angle = float(rng.uniform(0, 2 * np.pi))
        # 长度：旧版 40-130px / 1024 ≈ 短边 4%-13%
        total_len = float(rng.uniform(0.04, 0.13) * base)
        n_seg = int(rng.integers(8, 16))
        step = total_len / n_seg
        # 每条弯曲强度不同：有的平缓，有的明显卷曲
        curl = float(rng.uniform(0.25, 0.85))
        points = [(x, y)]
        for _ in range(n_seg):
            angle += float(rng.uniform(-curl, curl))
            x += np.cos(angle) * step
            y += np.sin(angle) * step
            if not (0 <= x < w and 0 <= y < h):
                break
            points.append((x, y))
        if len(points) < 3:
            continue

        p = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(p)
        d.line(points, fill=255, width=lw, joint="curve")
        a = np.array(p, dtype=np.float32) / 255.0

        # 透明度适度调高，使刮痕呈偏白色细痕（之前 0.06-0.14 过淡）
        opacity = float(rng.uniform(0.20, 0.38)) * strength
        canvas = np.maximum(canvas, a * opacity)

    canvas_pil = Image.fromarray((canvas * 255).astype(np.uint8), mode="L")
    canvas_pil = canvas_pil.filter(ImageFilter.GaussianBlur(radius=blur_r))
    canvas = np.array(canvas_pil, dtype=np.float32) / 255.0

    arr = arr.copy()
    arr[:, :, 0] = np.clip(arr[:, :, 0] + canvas * 0.95, 0, 1)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + canvas * 0.95, 0, 1)
    arr[:, :, 2] = np.clip(arr[:, :, 2] + canvas * 0.95, 0, 1)
    return arr


def add_vignette_and_age(arr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    v2: 暗角 12% → 5%（参考图几乎察觉不到）；老化色罩保留。
    """
    h, w, _ = arr.shape
    y, x = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    dist = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2)
    vignette = 1 - 0.05 * strength * np.clip(dist ** 1.8, 0, 1)
    arr = arr * vignette[:, :, None]

    # 极淡暖黄老照片色罩（避开最深暗部）
    lum = np.mean(arr, axis=2)
    warm_mask = np.clip((lum - 0.15) / 0.5, 0, 1)
    age_tint = np.array([0.02, 0.01, -0.015], dtype=np.float32) * strength
    arr = np.clip(arr + warm_mask[:, :, None] * age_tint, 0, 1)

    return arr


def add_paper_texture(frame: Image.Image, strength: float = 0.5) -> Image.Image:
    """
    v2 相纸白边处理：
    - 纸纹减半
    - 四角/边缘轻微发黄（模拟相纸老化，参考图特征）
    """
    w, h = frame.size
    rng = np.random.default_rng(seed=42)
    noise = rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32)
    noise = _resize_float_noise(noise, w, h)

    # v2: 纹理幅度 2.4 → 1.5
    amp = 2.5 * strength
    noise_rgb = np.stack([noise, noise, noise], axis=2) * amp

    # v2: 边缘老化发黄（径向掩膜，越靠边越黄）
    y, x = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    dist = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2)
    edge_mask = np.clip((dist - 0.55) / 0.45, 0, 1) ** 1.5
    # 相纸白边区才有（照片区会被覆盖？不会——本函数作用于整张含照片）
    # 只在边缘极轻微发黄，避免污染照片主体
    yellow_tint = np.zeros((h, w, 3), dtype=np.float32)
    yellow_tint[:, :, 0] = 6 * edge_mask    # R 略增
    yellow_tint[:, :, 1] = 3 * edge_mask    # G 微增
    yellow_tint[:, :, 2] = -4 * edge_mask   # B 略减 → 发黄

    arr = np.array(frame).astype(np.float32) + noise_rgb + yellow_tint
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def add_polaroid_frame(img: Image.Image, bottom_ratio: float = 1.8) -> Image.Image:
    """
    v2 Polaroid 边框：
    - 边框宽度 8% → 10%（对齐参考图）
    - 去掉照片/相纸交界的灰描边（参考图没有）
    - 底边 1.8 倍保持
    """
    photo_w, photo_h = img.size
    border = int(min(photo_w, photo_h) * 0.10)   # v2: 0.08 → 0.10
    top = left = right = border
    bottom = int(border * bottom_ratio)

    new_w = photo_w + left + right
    new_h = photo_h + top + bottom

    frame = Image.new("RGB", (new_w, new_h), POLAROID_BG)
    frame.paste(img, (left, top))

    # v2: 去掉灰描边，改为极细的暖色投影线（0.5px 感，比 v1 更轻）
    draw = ImageDraw.Draw(frame)
    draw.rectangle([left - 1, top - 1, left + photo_w, top + photo_h],
                   outline=(238, 236, 230), width=1)

    frame = add_paper_texture(frame, strength=0.5)
    return frame


def process(input_path: str, output_path: str, strength: float = 1.0,
            add_frame: bool = True, grain: float = 1.0, scratches: float = 1.0,
            size: int = 0, quality: int = 95) -> str:
    """完整处理流程。"""
    img = Image.open(input_path)
    img = ensure_rgb(img)
    img = resize_keep_ratio(img, size=size)

    arr = np.array(img).astype(np.float32) / 255.0

    # 1. 色调曲线
    arr = apply_tone_curve(arr, strength=strength)

    # 2. 色彩分级（v2: 统一暖底，暗部暖棕）
    arr = apply_color_grade(arr, strength=strength)

    # 3. 柔焦 / 漫射（v2: 增强）
    arr = reduce_clarity(arr, strength=strength)

    # 4. halation 光晕（v2: 新增）
    arr = add_halation(arr, strength=strength)

    # 5. 暗角与老化（v2: 暗角减半）
    arr = add_vignette_and_age(arr, strength=strength)

    # 6. 颗粒（v2: 大幅减弱 + 暖色）
    arr = add_grain(arr, strength=grain)

    # 7. 轻微白色划痕（v2: 减半）
    if scratches > 0:
        arr = add_scratches(arr, strength=scratches)

    # 转回 PIL
    processed = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), mode="RGB")

    # 8. 添加相框（v2: 10% 宽）
    if add_frame:
        processed = add_polaroid_frame(processed, bottom_ratio=1.8)

    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    processed.save(output_path, "JPEG", quality=quality, optimize=True)
    return output_path


def main():
    ap = argparse.ArgumentParser(
        description="将照片转换为 80-90 年代 Polaroid 复古 instant-film 风格 (v2.3)"
    )
    ap.add_argument("--input", "-i", required=True, help="输入图片路径")
    ap.add_argument("--output", "-o", default=None, help="输出图片路径（默认 ~/Downloads/Polaroid/<name>_polaroid.jpg）")
    ap.add_argument("--strength", "-s", type=float, default=1.0,
                    help="整体效果强度 0.0-1.5（默认 1.0）")
    ap.add_argument("--grain", "-g", type=float, default=1.0,
                    help="颗粒强度 0.0-1.5（默认 1.0）")
    ap.add_argument("--scratches", type=float, default=1.0,
                    help="白色划痕强度 0.0-1.5（默认 1.0，0 表示不添加）")
    ap.add_argument("--no-scratches", action="store_true",
                    help="不添加白色划痕")
    ap.add_argument("--no-frame", action="store_true",
                    help="不添加 Polaroid 白边")
    ap.add_argument("--size", type=int, default=0,
                    help="长边缩放到的像素值（默认 0 = 保持原图分辨率；>0 则缩放到该值）")
    ap.add_argument("--quality", type=int, default=95,
                    help="JPEG 质量 1-100（默认 95；>=95 时关闭色度子采样以保留细节）")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"错误：找不到输入文件 {args.input}")
        sys.exit(1)

    if args.output is None:
        out_dir = os.path.expanduser("~/Downloads/Polaroid")
        base = Path(args.input).stem
        args.output = os.path.join(out_dir, f"{base}_polaroid.jpg")

    scratches = 0.0 if args.no_scratches else np.clip(args.scratches, 0.0, 1.5)

    print(f"[Polaroid v2.3] 处理: {args.input}")
    print(f"  强度={args.strength}, 颗粒={args.grain}, 划痕={scratches}, 相框={'否' if args.no_frame else '是'}")

    result = process(
        args.input,
        args.output,
        strength=np.clip(args.strength, 0.0, 1.5),
        grain=np.clip(args.grain, 0.0, 1.5),
        scratches=scratches,
        add_frame=not args.no_frame,
        size=args.size,
        quality=int(np.clip(args.quality, 1, 100)),
    )

    print(f"[完成] 输出: {result}")


if __name__ == "__main__":
    main()
