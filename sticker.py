"""Printable dive-plan sticker — pure rendering, no Streamlit imports.

Renders the planning table as a 1-bit PNG sized for an 80×50 mm label on a
203 dpi thermal printer (Niimbot B1: 8 dots/mm, ≈48 mm print head). The label
feeds with its 50 mm side across the head, so the landscape image is
640×384 px and the printer app rotates it.

Gas encoding (the printer is black and white):
  back gas  → plain text
  lean gas  → bold + underlined
  rich gas  → white bold text on a black cell
"""
from __future__ import annotations

import io
import os
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

STICKER_W = 640
STICKER_H = 384
STICKER_DPI = 203
MARGIN = 4
MIN_FONT = 11
MAX_FONT = 40

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_REGULAR = os.path.join(_FONT_DIR, "DejaVuSansCondensed.ttf")
_BOLD = os.path.join(_FONT_DIR, "DejaVuSansCondensed-Bold.ttf")
_EMOJI = os.path.join(_FONT_DIR, "NotoEmoji.ttf")

# Characters that only modify an emoji's colour/presentation — meaningless on a
# monochrome printer, and without a shaping engine they'd render as boxes.
_EMOJI_MODIFIERS = {0xFE0E, 0xFE0F, 0x200D, 0x20E3} | set(range(0x1F3FB, 0x1F400))

PLAIN, LEAN, RICH = None, "lean", "rich"


@dataclass
class Cell:
    text: str
    role: str | None = PLAIN  # PLAIN / LEAN / RICH


# ─── Gas logic ────────────────────────────────────────────────────────────────
def lost_set(lost) -> set[str]:
    """Normalise a deco_gases_lost value (False / True / 'lean' / ['lean','rich'])."""
    if lost is True:
        return {"lean", "rich"}
    if not lost:
        return set()
    if isinstance(lost, str):
        return {lost}
    return set(lost)


def gas_role_at(depth_m, lost, lean_switch, rich_switch):
    """Which deco gas is being breathed at a stop depth: 'rich', 'lean' or None (back gas).

    lean_switch / rich_switch are None when that gas isn't carried.
    """
    gone = lost_set(lost)
    zones = []
    if rich_switch is not None and "rich" not in gone:
        zones.append((rich_switch, RICH))
    if lean_switch is not None and "lean" not in gone:
        zones.append((lean_switch, LEAN))
    for sd, role in sorted(zones):
        if depth_m <= sd:
            return role
    return PLAIN


# ─── Table assembly ───────────────────────────────────────────────────────────
def build_grid(results, fmt_depth, lean_switch, rich_switch):
    """Turn scenario results into (column headers, [(row label, [Cell, ...])]).

    Each result needs: short, depth, bottom_time, deco_stops, stop_runtimes,
    total_time, deco_gases_lost. Callers pass only the scenarios to print.
    """
    headers = [r["short"] for r in results]
    rows = []
    for dd in sorted({r["depth"] for r in results}, reverse=True):
        rows.append((fmt_depth(dd), [
            Cell(str(r["bottom_time"]) if r["depth"] == dd else "") for r in results
        ]))
    stop_depths = sorted({d for r in results for d, _ in r["deco_stops"]}, reverse=True)
    for sd in stop_depths:
        cells = []
        for r in results:
            t = next((t for dp, t in r["deco_stops"] if dp == sd), None)
            if t is None:
                cells.append(Cell(""))
                continue
            rt = r["stop_runtimes"].get(sd)
            txt = f"{rt:.0f} ({t:.0f})" if rt is not None else f"({t:.0f})"
            cells.append(Cell(txt, gas_role_at(sd, r["deco_gases_lost"], lean_switch, rich_switch)))
        rows.append((fmt_depth(sd), cells))
    # Surface row: styled with the last gas breathed.
    rows.append((fmt_depth(0), [
        Cell(f"{r['total_time']:.0f}",
             gas_role_at(0, r["deco_gases_lost"], lean_switch, rich_switch)
             if r["deco_stops"] else PLAIN)
        for r in results
    ]))
    return headers, rows


# ─── Text rendering with emoji fallback ───────────────────────────────────────
@lru_cache(maxsize=None)
def _font(path: str, size: int):
    f = ImageFont.truetype(path, size)
    if path == _EMOJI:
        try:
            f.set_variation_by_axes([700])  # bold weight reads better on thermal
        except Exception:
            pass
    return f


def _is_emoji(ch: str) -> bool:
    cp = ord(ch)
    if cp >= 0x1F000:
        return True
    return cp >= 0x2190 and unicodedata.category(ch) in ("So", "Sk")


def _segments(text: str, bold: bool, size: int):
    """Split text into (substring, font) runs, routing emoji to the emoji font."""
    main = _font(_BOLD if bold else _REGULAR, size)
    emoji = _font(_EMOJI, size)
    runs: list[tuple[str, object]] = []
    for ch in text:
        if ord(ch) in _EMOJI_MODIFIERS:
            continue
        f = emoji if _is_emoji(ch) else main
        if runs and runs[-1][1] is f:
            runs[-1] = (runs[-1][0] + ch, f)
        else:
            runs.append((ch, f))
    return runs


def text_width(text: str, bold: bool, size: int) -> float:
    return sum(f.getlength(s) for s, f in _segments(text, bold, size))


def _draw_text(draw, x, cy, text, bold, size, fill, underline=False):
    """Draw text left-aligned at x, vertically centred on cy. Returns end x."""
    start = x
    for s, f in _segments(text, bold, size):
        draw.text((x, cy), s, font=f, fill=fill, anchor="lm")
        x += f.getlength(s)
    if underline and text:
        uy = cy + size * 0.46
        draw.line([(start, uy), (x, uy)], fill=fill, width=max(2, size // 12))
    return x


# ─── Layout + render ──────────────────────────────────────────────────────────
@dataclass
class TitleItem:
    text: str
    role: str | None = PLAIN
    bold: bool = False


def _cell_w(text, role, size, pad):
    return text_width(text, role is not PLAIN, size) + 2 * pad


def _measure(size, title, headers, rows):
    pad_x = max(3, size // 4)
    pad_y = max(1, size // 8)
    ascent, descent = _font(_REGULAR, size).getmetrics()
    row_h = ascent + descent + 2 * pad_y
    label_w = max(_cell_w(lbl, PLAIN, size, pad_x) for lbl, _ in rows)
    col_ws = []
    for j, h in enumerate(headers):
        w = text_width(h, True, size) + 2 * pad_x
        for _, cells in rows:
            w = max(w, _cell_w(cells[j].text, cells[j].role, size, pad_x))
        col_ws.append(w)
    gap = size * 0.6
    title_w = sum(_cell_w(t.text, t.role, size, pad_x if t.role is RICH else 0) for t in title)
    title_w += gap * max(0, len(title) - 1)
    return dict(pad_x=pad_x, row_h=row_h, label_w=label_w, col_ws=col_ws,
                title_w=title_w, gap=gap)


def render_sticker(title: list[TitleItem], headers: list[str], rows,
                   width: int = STICKER_W, height: int = STICKER_H):
    """Render the sticker. Returns (PIL 1-bit image, info dict).

    info: font_size, title_font_size, fits (bool), warnings (list of str).
    """
    avail_w = width - 2 * MARGIN
    avail_h = height - 2 * MARGIN
    n_rows = len(rows) + 2  # title + column headers + body
    warnings = []

    size, m = MIN_FONT, None
    for s in range(MAX_FONT, MIN_FONT - 1, -1):
        mm = _measure(s, title, headers, rows)
        if mm["label_w"] + sum(mm["col_ws"]) <= avail_w and mm["row_h"] * n_rows <= avail_h:
            size, m = s, mm
            break
    fits = m is not None
    if not fits:
        m = _measure(MIN_FONT, title, headers, rows)
        warnings.append(
            f"Table doesn't fit even at {MIN_FONT}px — print fewer scenarios "
            "or the sticker will be clipped."
        )

    # Title shares the row; shrink it independently if it's too wide.
    title_size = size
    while title_size > MIN_FONT and _measure(title_size, title, headers, rows)["title_w"] > avail_w:
        title_size -= 1
    tm = _measure(title_size, title, headers, rows)
    if tm["title_w"] > avail_w:
        warnings.append("Title is too long and will be clipped — shorten the plan name.")

    # Stretch to fill the label: spare width to data columns, spare height to rows.
    used_w = m["label_w"] + sum(m["col_ws"])
    extra_w = max(0, avail_w - used_w)
    col_ws = [w + extra_w / len(m["col_ws"]) for w in m["col_ws"]] if m["col_ws"] else []
    label_w = m["label_w"]
    row_h = m["row_h"] + max(0, avail_h - m["row_h"] * n_rows) / n_rows

    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"  # no anti-aliasing: thermal heads can't print grey

    # Title row
    x = MARGIN
    cy = MARGIN + row_h / 2
    for t in title:
        bold = t.bold or t.role is not PLAIN
        if t.role is RICH:
            w = text_width(t.text, True, title_size) + 2 * tm["pad_x"]
            draw.rectangle([x, MARGIN + 1, x + w, MARGIN + row_h - 1], fill=0)
            _draw_text(draw, x + tm["pad_x"], cy, t.text, True, title_size, 1)
            x += w
        else:
            x = _draw_text(draw, x, cy, t.text, bold, title_size, 0,
                           underline=t.role is LEAN)
        x += tm["gap"]

    # Grid
    top = MARGIN + row_h
    xs = [MARGIN, MARGIN + label_w]
    for w in col_ws:
        xs.append(xs[-1] + w)
    right = xs[-1]
    bottom = top + row_h * (len(rows) + 1)
    for i in range(len(rows) + 2):
        y = round(top + i * row_h)
        draw.line([(MARGIN, y), (right, y)], fill=0, width=1)
    for xv in xs:
        draw.line([(round(xv), round(top)), (round(xv), round(bottom))], fill=0, width=1)

    def _centred(text, x0, x1, cy_, bold, fill, underline=False):
        w = text_width(text, bold, size)
        _draw_text(draw, (x0 + x1 - w) / 2, cy_, text, bold, size, fill, underline)

    # Column headers
    cy = top + row_h / 2
    for j, h in enumerate(headers):
        _centred(h, xs[j + 1], xs[j + 2], cy, True, 0)

    # Body. Rich cells are filled over the grid lines so a run of them merges
    # into one solid black block.
    for i, (label, cells) in enumerate(rows):
        y0 = top + (i + 1) * row_h
        cy = y0 + row_h / 2
        _draw_text(draw, xs[0] + m["pad_x"], cy, label, False, size, 0)
        for j, c in enumerate(cells):
            x0, x1 = xs[j + 1], xs[j + 2]
            if c.role is RICH and c.text:
                draw.rectangle([round(x0), round(y0), round(x1), round(y0 + row_h)], fill=0)
                _centred(c.text, x0, x1, cy, True, 1)
            elif c.text:
                _centred(c.text, x0, x1, cy, c.role is LEAN, 0, underline=c.role is LEAN)

    return img, dict(font_size=size, title_font_size=title_size, fits=fits, warnings=warnings)


def png_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(STICKER_DPI, STICKER_DPI))
    return buf.getvalue()


# ─── Cylinder (gas mix) stickers ──────────────────────────────────────────────
# Same 80×50 mm label as the plan sticker. A deco gas gets three labels laid
# side by side on the cylinder — |NX|50%|21m| — and the back gas gets one.
HYPOXIC_PPO2 = 0.18  # minimum operating depth is printed when surface ppO2 < this
GAS_MARGIN = 10


def gas_kind_and_mix(o2: int, he: int, h2: int = 0) -> tuple[str, str]:
    """('NX', '50%'), ('TX', '18/45'), ('O2', '100%'), ('AIR', '21%'), ('HX', '2/48/50')."""
    if h2:
        return "HX", f"{o2}/{he}/{h2}"
    if he:
        return "TX", f"{o2}/{he}"
    if o2 >= 100:
        return "O2", "100%"
    if o2 == 21:
        return "AIR", "21%"
    return "NX", f"{o2}%"


def min_operating_depth(o2_frac: float, min_ppo2: float = HYPOXIC_PPO2,
                        surface_pressure: float = 1.01325) -> int:
    """Shallowest whole-metre depth where the gas reaches min_ppo2; 0 if breathable at the surface."""
    import math
    return max(0, math.ceil((min_ppo2 / o2_frac - surface_pressure) * 10))


def _ink(text, size, bold=True):
    """Ink bbox (l, t, r, b) relative to a baseline-left origin."""
    return _font(_BOLD if bold else _REGULAR, size).getbbox(text, anchor="ls")


def _fit(text, max_w, max_h, bold=True, hi=600):
    """Largest font size whose ink fits max_w × max_h."""
    lo, best = 6, 6
    while lo <= hi:
        mid = (lo + hi) // 2
        l, t, r, b = _ink(text, mid, bold)
        if r - l <= max_w and b - t <= max_h:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return best


def _put(draw, text, size, cx, cy, bold=True):
    """Draw text with its ink box centred on (cx, cy). Returns the ink box in image coords."""
    l, t, r, b = _ink(text, size, bold)
    ox, oy = cx - (l + r) / 2, cy - (t + b) / 2
    draw.text((ox, oy), text, font=_font(_BOLD if bold else _REGULAR, size), fill=0, anchor="ls")
    return ox + l, oy + t, ox + r, oy + b


def _blank(width, height):
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    return img, draw


def _caption(draw, text, x0, x1, y0, size):
    """Small left-aligned line (name · date), emoji-capable. Returns its bottom y."""
    if not text:
        return y0
    while size > MIN_FONT and text_width(text, False, size) > x1 - x0:
        size -= 1
    asc, desc = _font(_REGULAR, size).getmetrics()
    _draw_text(draw, x0, y0 + (asc + desc) / 2, text, False, size, 0)
    return y0 + asc + desc


def _name_date(name: str, date_str: str) -> str:
    return " · ".join(p for p in (name.strip(), date_str) if p)


def _mod_block(draw, depth_m, label, box):
    """'21m' as big as fits in box, with `label` small in the space above the 'm'."""
    x0, y0, x1, y1 = box
    text = f"{depth_m}m"
    size = _fit(text, x1 - x0, y1 - y0)
    l, t, r, b = _put(draw, text, size, (x0 + x1) / 2, (y0 + y1) / 2)
    # Locate the 'm' and the top of its x-height.
    digits_r = l + (_font(_BOLD, size).getlength(str(depth_m)))
    ml, mt, mr, mb = _ink("m", size)
    m_top = b - (mb - mt)
    gap = size * 0.04
    # The label lives in the empty space above the 'm' (up to the label's top
    # margin). Use one line or two stacked ("MOD" / "@ 1.6"), whichever is bigger.
    bw, bh = r - digits_r - gap, m_top - y0 - 2 * gap
    bx, by = (digits_r + gap + r) / 2, (y0 + m_top - gap) / 2
    one = _fit(label, bw, bh, hi=size)
    parts = label.split(" ", 1)
    two = min(_fit(p, bw, bh * 0.45, hi=size) for p in parts) if len(parts) == 2 else 0
    if two > one:
        _put(draw, parts[0], two, bx, by - bh * 0.25)
        _put(draw, parts[1], two, bx, by + bh * 0.25)
    else:
        _put(draw, label, one, bx, by)


def render_deco_gas_stickers(o2: int, he: int, mod_m: int, mod_ppo2: float,
                             name: str = "", date_str: str = "",
                             width: int = STICKER_W, height: int = STICKER_H):
    """Three labels for a deco cylinder: [kind, mix (+ name/date), MOD]."""
    kind, mix = gas_kind_and_mix(o2, he)
    W, H, M = width, height, GAS_MARGIN

    a, d = _blank(W, H)
    _put(d, kind, _fit(kind, W - 2 * M, H - 2 * M), W / 2, H / 2)

    b, d = _blank(W, H)
    top = _caption(d, _name_date(name, date_str), M, W - M, M, 34) + M
    _put(d, mix, _fit(mix, W - 2 * M, H - top - M), W / 2, (top + H - M) / 2)

    c, d = _blank(W, H)
    _mod_block(d, mod_m, f"MOD @ {mod_ppo2:g}", (M, M, W - M, H - M))
    return [a, b, c]


def render_back_gas_sticker(o2: int, he: int, h2: int, mod_m: int, mod_ppo2: float,
                            name: str = "", date_str: str = "",
                            width: int = STICKER_W, height: int = STICKER_H):
    """One label for the back gas: name/date, 'TX 18/45', MOD and (hypoxic) MIN."""
    kind, mix = gas_kind_and_mix(o2, he, h2)
    W, H, M = width, height, GAS_MARGIN
    img, d = _blank(W, H)
    top = _caption(d, _name_date(name, date_str), M, W - M, M, 34) + M
    avail = H - top - M
    headline = kind if kind == "AIR" else f"{kind} {mix}"
    _put(d, headline, _fit(headline, W - 2 * M, avail * 0.45), W / 2, top + avail * 0.225)
    lines = [f"MOD @ {mod_ppo2:g}  {mod_m}m"]
    min_m = min_operating_depth(o2 / 100) if o2 else 0
    if min_m:
        lines.append(f"MIN @ {HYPOXIC_PPO2:g}  {min_m}m")
    row_h = avail * 0.55 / len(lines)
    size = min(_fit(s, W - 2 * M, row_h * 0.8) for s in lines)
    for i, s in enumerate(lines):
        _put(d, s, size, W / 2, top + avail * 0.45 + row_h * (i + 0.5))
    return img
