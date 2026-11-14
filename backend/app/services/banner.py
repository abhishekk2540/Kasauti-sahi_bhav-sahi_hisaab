"""Daily rate banner (PNG) with shop branding (US-03). Needs a TTF font (fonts-dejavu-core in Docker)."""
import io
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import DISCLAIMER

W = H = 1080
_BUNDLED = str(Path(__file__).resolve().parent.parent / "assets" / "fonts" / "DejaVuSans-Bold.ttf")
_FONT_PATHS = [
    _BUNDLED,
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
]


def _font(size: int) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, bool]:
    for p in _FONT_PATHS:
        try:
            return ImageFont.truetype(p, size), True
        except OSError:
            continue
    return ImageFont.load_default(size=size), False  # may lack the rupee glyph


def inr_group(n: float) -> str:
    """Indian digit grouping: 1234567 -> 12,34,567."""
    s = str(int(round(n)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


def render_banner(shop_name: str, rates: dict[str, tuple[float, str]], on: date,
                  logo: bytes | None = None, phone: str | None = None) -> bytes:
    """rates: {"gold": (price, "10g"), "silver": (price, "kg")} (selling price, margin already applied)."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):  # vertical gradient, deep maroon -> dark
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(96 - 56 * t), int(18 - 8 * t), int(32 - 14 * t)))

    gold, cream = (232, 190, 92), (250, 243, 224)
    f_title, ok = _font(64)
    f_sub, _ = _font(34)
    f_label, _ = _font(46)
    f_price, _ = _font(96)
    f_small, _ = _font(24)
    rupee = "₹" if ok else "Rs."

    y = 60
    if logo:
        try:
            lg = Image.open(io.BytesIO(logo)).convert("RGBA")
            lg.thumbnail((170, 170))
            img.paste(lg, ((W - lg.width) // 2, y), lg)
            y += lg.height + 20
        except Exception:
            pass  # bad logo should never break the banner
    for line in _wrap(d, shop_name, f_title, W - 120)[:2]:
        d.text((W / 2, y), line, font=f_title, fill=gold, anchor="mt")
        y += 76
    d.text((W / 2, y + 8), f"Aaj ka Bhav  |  {on.strftime('%d %b %Y')}", font=f_sub, fill=cream, anchor="mt")

    cards = [("GOLD 24K", "gold", "10g"), ("SILVER", "silver", "kg")]
    top = max(y + 90, 420)
    for i, (label, metal, unit) in enumerate(cards):
        cy = top + i * 240
        d.rounded_rectangle([70, cy, W - 70, cy + 210], radius=28, outline=gold, width=3, fill=(40, 8, 16))
        d.text((110, cy + 28), f"{label}  /  {unit}", font=f_label, fill=gold)
        price = rates.get(metal)
        txt = f"{rupee} {inr_group(price[0])}" if price else "--"
        d.text((110, cy + 95), txt, font=f_price, fill=cream)

    foot_y = H - 70
    if phone:
        d.text((W / 2, foot_y - 48), f"Call: {phone}", font=f_sub, fill=cream, anchor="mt")
    for line in _wrap(d, DISCLAIMER, f_small, W - 140)[:2]:
        d.text((W / 2, foot_y), line, font=f_small, fill=(200, 190, 170), anchor="mt")
        foot_y += 30

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
