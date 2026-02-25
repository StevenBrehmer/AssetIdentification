import os
from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int) -> ImageFont.ImageFont:
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    if not os.path.exists(path):
        raise RuntimeError(f"Font file missing: {path}")

    return ImageFont.truetype(path, size)


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def render_overlay(image_path: str, detections: list[dict], out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # --- sane, "normal" sizing ---
    # Typical iPhone 4032px wide => ~28–32px font
    # Typical 1920px wide => ~18–22px font
    base = int(img.width / 140)  # gentle scaling
    font_size = _clamp(base, 14, 34)
    font = _load_font(font_size)

    line_w = _clamp(int(img.width / 800), 2, 6)   # 4032 -> 5, 1920 -> 2
    pad = _clamp(int(font_size * 0.35), 4, 10)    # label padding

    # Styling
    box_outline = (255, 255, 255)  # white box
    label_bg = (0, 0, 0)           # black background
    label_fg = (255, 255, 255)     # white text

    for d in detections:
        x1, y1, x2, y2 = d["bbox_xyxy"]
        label = str(d.get("label", "object"))
        conf = float(d.get("confidence", 0.0))

        # bounding box
        draw.rectangle([x1, y1, x2, y2], outline=box_outline, width=line_w)

        # label text
        text = f"{label} {conf:.2f}"

        # measure
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # place above top-left; if not enough room, place below
        tx1 = int(x1)
        ty1 = int(y1) - th - (2 * pad)
        if ty1 < 0:
            ty1 = int(y1) + 1  # just below box
        tx2 = tx1 + tw + (2 * pad)
        ty2 = ty1 + th + (2 * pad)

        # clamp horizontally inside image
        if tx2 > img.width:
            shift = tx2 - img.width
            tx1 = max(0, tx1 - shift)
            tx2 = tx1 + tw + (2 * pad)

        # clamp vertically inside image
        if ty2 > img.height:
            ty2 = img.height
            ty1 = max(0, ty2 - (th + (2 * pad)))

        # background + text
        draw.rectangle([tx1, ty1, tx2, ty2], fill=label_bg)
        draw.text((tx1 + pad, ty1 + pad), text, fill=label_fg, font=font)

    img.save(out_path, quality=92)
    return out_path