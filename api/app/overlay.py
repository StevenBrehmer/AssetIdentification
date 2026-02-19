import os
from PIL import Image, ImageDraw, ImageFont

def render_overlay(image_path: str, detections: list[dict], out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Default font (works in slim images)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for d in detections:
        x1, y1, x2, y2 = d["bbox_xyxy"]
        label = d["label"]
        conf = d.get("confidence", 0.0)

        # Rectangle
        draw.rectangle([x1, y1, x2, y2], width=3)

        # Label background + text
        text = f"{label} {conf:.2f}"
        
        if font:
            # Pillow >=10: prefer textbbox
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        else:
            tw, th = (len(text) * 6, 12)

        
        tx1, ty1 = x1, max(0, y1 - th - 6)
        tx2, ty2 = x1 + tw + 6, y1

        draw.rectangle([tx1, ty1, tx2, ty2], fill=(0, 0, 0))
        draw.text((tx1 + 3, ty1 + 3), text, fill=(255, 255, 255), font=font)

    img.save(out_path, quality=92)
    return out_path
