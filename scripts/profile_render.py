"""Profile README 区块与 Mansus Winter Bento 矢量磁贴渲染器。

只做一件事：把「配置 + 抓取到的仓库/PR 数据」渲染成主页所需的深浅双色 SVG 磁贴与 GFM 区块。
不联网、不直接读写磁盘，因此可由单元测试直接验证且严格幂等。
"""

from __future__ import annotations

import html
import re

CJK_SPACE = re.compile(r"\s+(?=[，。、；：！？）」』】…])|(?<=[（「『【])\s+")

FONT_SANS = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei UI', "
    "'PingFang SC', 'Noto Sans CJK SC', system-ui, sans-serif"
)
FONT_CJK = (
    "'Microsoft YaHei UI', 'PingFang SC', 'Noto Sans CJK SC', "
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
)
FONT_MONO = (
    "ui-monospace, 'JetBrains Mono', 'Cascadia Mono', SFMono-Regular, "
    "Consolas, 'Liberation Mono', monospace"
)
FONT_SERIF = (
    "'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, 'Times New Roman', serif"
)

ASPECT_CYCLE = ("winter", "knock", "lantern", "winter", "knock", "lantern")

ASPECT_THEMES = {
    "winter": {
        "dark": {
            "dot": "#95c8d2",
            "halo": "#6faab7",
            "glow": "#95c8d2",
            "top_line": "#95c8d2",
            "pill_bg": "#0b1b22",
            "pill_border": "#366370",
            "pill_text": "#d6f2f7",
        },
        "light": {
            "dot": "#175e73",
            "halo": "#298099",
            "glow": "#389ab5",
            "top_line": "#1a687f",
            "pill_bg": "#eaf5f8",
            "pill_border": "#8abbc9",
            "pill_text": "#0f4859",
        },
    },
    "lantern": {
        "dark": {
            "dot": "#d8c66b",
            "halo": "#b8a34b",
            "glow": "#d8c66b",
            "top_line": "#d8c66b",
            "pill_bg": "#1d190c",
            "pill_border": "#635526",
            "pill_text": "#efe09e",
        },
        "light": {
            "dot": "#8a6814",
            "halo": "#b58d28",
            "glow": "#c99f36",
            "top_line": "#967218",
            "pill_bg": "#faf5e6",
            "pill_border": "#d4be7a",
            "pill_text": "#664b08",
        },
    },
    "knock": {
        "dark": {
            "dot": "#a466d9",
            "halo": "#8a4bc2",
            "glow": "#9c55d4",
            "top_line": "#a466d9",
            "pill_bg": "#190f26",
            "pill_border": "#553475",
            "pill_text": "#e4d1f7",
        },
        "light": {
            "dot": "#632c99",
            "halo": "#7e42ba",
            "glow": "#8b5cf6",
            "top_line": "#6b32a3",
            "pill_bg": "#f4eefb",
            "pill_border": "#bfa5e3",
            "pill_text": "#4c1d7a",
        },
    },
}

SURFACE = {
    "dark": {
        "bg_top": "#0b1118",
        "bg_bot": "#06090e",
        "border": "#1d2935",
        "deco_line": "#95c8d2",
        "deco_op": "0.13",
        "divider": "#17222c",
        "title": "#edf5f8",
        "body": "#aebdc7",
        "muted": "#70828f",
        "chip_bg": "#0f1720",
        "chip_border": "#22303d",
        "chip_text": "#93a5b3",
        "section_title": "#e4eff3",
        "section_sub": "#6d808d",
        "section_line": "#1c2833",
        "pr_purple": "#a978e0",
        "pr_pill_bg": "#171024",
        "pr_pill_border": "#48306b",
    },
    "light": {
        "bg_top": "#fcfcfd",
        "bg_bot": "#f2f5f7",
        "border": "#c7d3dc",
        "deco_line": "#4d6e7d",
        "deco_op": "0.17",
        "divider": "#dfe6ec",
        "title": "#101c24",
        "body": "#364652",
        "muted": "#5c707d",
        "chip_bg": "#eaf0f4",
        "chip_border": "#cbd6df",
        "chip_text": "#415461",
        "section_title": "#101c24",
        "section_sub": "#586b78",
        "section_line": "#ced9e1",
        "pr_purple": "#632c99",
        "pr_pill_bg": "#f3edfb",
        "pr_pill_border": "#c3aae6",
    },
}


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def clean(text: str, view: str) -> str:
    """中文视图下收敛 YAML 折行带来的标点旁多余空格；英文原样返回。"""
    return CJK_SPACE.sub("", text) if view == "zh" else text


def slugify(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")


def format_stars(stars: int) -> str:
    if stars >= 1000:
        return f"{(stars // 100) / 10:.1f}k"
    return str(stars)


def to_roman(num: int) -> str:
    if num <= 0:
        return "0"
    table = (
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    out = []
    rem = num
    for val, sym in table:
        while rem >= val:
            out.append(sym)
            rem -= val
    return "".join(out)


def primary_language(data: dict) -> dict | None:
    langs = data.get("languages") or []
    return langs[0] if langs else None


def approx_text_width(text: str, font_size: float, letter_spacing: float = 0.0) -> float:
    w = 0.0
    for ch in text:
        if ord(ch) > 127:
            w += font_size * 1.03
        elif ch in "iIl1|.,:;'! ":
            w += font_size * 0.38
        elif ch in "MW@#%":
            w += font_size * 0.78
        else:
            w += font_size * 0.62
    if len(text) > 1 and letter_spacing > 0:
        w += (len(text) - 1) * letter_spacing
    return w


def wrap_two_lines(text: str, view: str, max_px: float, font_size: float) -> list[str]:
    """将单段描述在 max_px 宽度内折成至多两行，供未手写 lines_zh/en 的新增条目使用。"""
    text = clean(text.strip(), view)
    if not text:
        return ["", ""]
    if approx_text_width(text, font_size) <= max_px:
        return [text, ""]

    if view == "zh":
        acc = ""
        for idx, ch in enumerate(text):
            if approx_text_width(acc + ch, font_size) > max_px:
                rest = text[idx:].lstrip()
                while approx_text_width(rest, font_size) > max_px and len(rest) > 1:
                    rest = rest[:-2].rstrip("，、； ") + "…"
                return [acc, rest]
            acc += ch
        return [acc, ""]

    words = text.split()
    line1: list[str] = []
    idx = 0
    while idx < len(words):
        cand = " ".join(line1 + [words[idx]])
        if line1 and approx_text_width(cand, font_size) > max_px:
            break
        line1.append(words[idx])
        idx += 1
    rest = " ".join(words[idx:])
    while approx_text_width(rest, font_size) > max_px and " " in rest:
        rest = rest.rsplit(" ", 1)[0] + "…"
    return [" ".join(line1), rest]


def chamfer_rect_path(x: float, y: float, w: float, h: float, c: float) -> str:
    x2, y2 = x + w, y + h
    return (
        f"M {x + c:.1f} {y:.1f} "
        f"L {x2 - c:.1f} {y:.1f} "
        f"L {x2:.1f} {y + c:.1f} "
        f"L {x2:.1f} {y2 - c:.1f} "
        f"L {x2 - c:.1f} {y2:.1f} "
        f"L {x + c:.1f} {y2:.1f} "
        f"L {x:.1f} {y2 - c:.1f} "
        f"L {x:.1f} {y + c:.1f} Z"
    )


def art_deco_inner_frame(
    w: int, h: int, line_color: str, line_op: str, accent_color: str, accent_op: str = "0.34"
) -> str:
    inset_x, inset_y = 5.0, 5.5
    iw, ih = w - 10.0, h - 11.0
    c = 6.5
    frame_d = chamfer_rect_path(inset_x, inset_y, iw, ih, c)
    x2, y2 = inset_x + iw, inset_y + ih
    return (
        f'<path d="{frame_d}" stroke="{line_color}" stroke-opacity="{line_op}" stroke-width="0.8" fill="none"/>'
        f'<path d="M {inset_x:.1f} {inset_y + c + 7:.1f} L {inset_x:.1f} {inset_y + c:.1f} L {inset_x + c:.1f} {inset_y:.1f} L {inset_x + c + 9:.1f} {inset_y:.1f}" '
        f'stroke="{accent_color}" stroke-opacity="{accent_op}" stroke-width="0.95" fill="none"/>'
        f'<path d="M {x2:.1f} {y2 - c - 7:.1f} L {x2:.1f} {y2 - c:.1f} L {x2 - c:.1f} {y2:.1f} L {x2 - c - 9:.1f} {y2:.1f}" '
        f'stroke="{accent_color}" stroke-opacity="{accent_op}" stroke-width="0.95" fill="none"/>'
    )


def mansus_diamond_stud(
    cx: float, cy: float, color: str, halo: str, mode: str, scale: float = 1.0
) -> str:
    r_out = 6.2 * scale
    r_in = 3.1 * scale
    k = 1.05 * scale
    op = "0.32" if mode == "dark" else "0.28"
    return (
        f'<g transform="translate({cx:.1f}, {cy:.1f})">'
        f'<path d="M 0 {-r_out:.1f} L {r_out:.1f} 0 L 0 {r_out:.1f} L {-r_out:.1f} 0 Z" stroke="{halo}" stroke-opacity="{op}" stroke-width="0.85" fill="{halo}" fill-opacity="0.08"/>'
        f'<path d="M 0 {-r_in:.1f} L {k:.2f} {-k:.2f} L {r_in:.1f} 0 L {k:.2f} {k:.2f} L 0 {r_in:.1f} L {-k:.2f} {k:.2f} L {-r_in:.1f} 0 L {-k:.2f} {-k:.2f} Z" fill="{color}"/>'
        f"</g>"
    )


def winter_four_cross(cx: float, cy: float, arm: float, color: str, opacity: str = "0.9") -> str:
    w = arm * 0.28
    top = arm * 1.08
    bot = arm * 1.18
    side = arm * 0.96
    return (
        f'<path d="M {cx:.2f} {cy - top:.2f} '
        f'L {cx + w:.2f} {cy - w:.2f} '
        f'L {cx + side:.2f} {cy:.2f} '
        f'L {cx + w:.2f} {cy + w:.2f} '
        f'L {cx:.2f} {cy + bot:.2f} '
        f'L {cx - w:.2f} {cy + w:.2f} '
        f'L {cx - side:.2f} {cy:.2f} '
        f'L {cx - w:.2f} {cy - w:.2f} Z" '
        f'fill="{color}" fill-opacity="{opacity}"/>'
    )


def vector_ne_arrow(x: float, y: float, color: str, size: float = 6.5, sw: float = 1.35) -> str:
    return (
        f'<g transform="translate({x:.1f}, {y:.1f})" stroke="{color}" '
        f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" fill="none">'
        f'<line x1="0" y1="{size:.1f}" x2="{size:.1f}" y2="0"/>'
        f'<polyline points="{size * 0.28:.1f},0 {size:.1f},0 {size:.1f},{size * 0.72:.1f}"/>'
        f"</g>"
    )


def make_section_header(
    mode: str, zh_title: str, en_title: str, right_meta: str, accent: str
) -> str:
    w, h = 836, 30
    s = SURFACE[mode]
    a = ASPECT_THEMES[accent][mode]
    zh_w = approx_text_width(zh_title, 13.5, 0.0)
    en_x = int(24 + zh_w + 11)
    en_w = approx_text_width(en_title, 10.6, 1.8)
    left_end = int(en_x + en_w + 18)
    right_w = approx_text_width(right_meta, 11.2, 1.8)
    right_start = int(832 - right_w - 22)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" role="img" aria-label="{esc(zh_title)} · {esc(en_title)}">
  {mansus_diamond_stud(9.5, 15.0, a['dot'], a['halo'], mode, 0.92)}
  <text x="24" y="19.5" fill="{s['section_title']}" font-family="{FONT_CJK}" font-size="13.5" font-weight="700">{esc(zh_title)}</text>
  <text x="{en_x}" y="19" fill="{s['section_sub']}" font-family="{FONT_MONO}" font-size="10.6" font-weight="600" letter-spacing="1.8">{esc(en_title)}</text>

  <!-- Art Deco Hairline Rule with Hollow Diamond Finials -->
  <path d="M {left_end - 3} 15 L {left_end} 12.2 L {left_end + 3} 15 L {left_end} 17.8 Z" stroke="{a['dot']}" stroke-opacity="0.55" stroke-width="0.9" fill="none"/>
  <line x1="{left_end + 5}" y1="15" x2="{right_start - 5}" y2="15" stroke="{s['section_line']}" stroke-width="1"/>
  <path d="M {right_start - 3} 15 L {right_start} 12.2 L {right_start + 3} 15 L {right_start} 17.8 Z" stroke="{s['section_sub']}" stroke-opacity="0.45" stroke-width="0.9" fill="none"/>

  <text x="832" y="19" fill="{s['section_sub']}" font-family="{FONT_SERIF}" font-size="10.8" font-weight="600" letter-spacing="1.5" text-anchor="end">{esc(right_meta)}</text>
</svg>
"""


def card_aspect_watermark(aspect: str, color: str, w: int = 414) -> str:
    dx = w - 414
    if aspect == "winter":
        return (
            f'<path d="M {366 + dx} 96 L {366 + dx} 34 A 20 20 0 0 1 {406 + dx} 34 L {406 + dx} 96" stroke="{color}" stroke-width="0.9" fill="none"/>'
            f'<line x1="{386 + dx}" y1="54" x2="{386 + dx}" y2="96" stroke="{color}" stroke-width="1.1"/>'
            + winter_four_cross(386 + dx, 33, 3.4, color, "0.95")
            + winter_four_cross(379 + dx, 41, 2.8, color, "0.85")
            + winter_four_cross(393 + dx, 41, 2.8, color, "0.85")
        )
    if aspect == "lantern":
        return (
            f'<path d="M {386 + dx} 12 L {408 + dx} 34 L {386 + dx} 56 L {364 + dx} 34 Z" stroke="{color}" stroke-width="0.9" fill="none"/>'
            f'<path d="M {386 + dx} 21 L {399 + dx} 34 L {386 + dx} 47 L {373 + dx} 34 Z" stroke="{color}" stroke-width="0.8" fill="none"/>'
            f'<line x1="{386 + dx}" y1="4" x2="{386 + dx}" y2="76" stroke="{color}" stroke-width="0.8"/>'
            f'<line x1="{354 + dx}" y1="34" x2="{414 + dx}" y2="34" stroke="{color}" stroke-width="0.8"/>'
        )
    return (
        f'<path d="M {368 + dx} 88 L {386 + dx} 16 L {404 + dx} 88" stroke="{color}" stroke-width="0.9" fill="none"/>'
        f'<path d="M {375 + dx} 88 L {386 + dx} 38 L {397 + dx} 88" stroke="{color}" stroke-width="0.8" fill="none"/>'
        f'<circle cx="{386 + dx}" cy="30" r="5.5" stroke="{color}" stroke-width="0.9" fill="none"/>'
        f'<line x1="{386 + dx}" y1="35.5" x2="{386 + dx}" y2="68" stroke="{color}" stroke-width="0.9"/>'
    )


def resolve_work_Lines(project: dict, view: str, width: int) -> list[str]:
    explicit = project.get(f"lines_{view}")
    if explicit and len(explicit) >= 1:
        l1 = explicit[0]
        l2 = explicit[1] if len(explicit) > 1 else ""
        return [l1, l2]
    desc = project.get(f"desc_{view}") or project.get("desc_zh") or ""
    font_size = 12.5 if view == "zh" else 12.2
    return wrap_two_lines(desc, view, width - 44, font_size)


def make_work_card(
    project: dict,
    data: dict,
    mode: str,
    view: str = "zh",
    aspect_fallback: str = "winter",
    width: int = 414,
) -> str:
    w, h = width, 154
    s = SURFACE[mode]
    aspect = project.get("aspect") or aspect_fallback
    if aspect not in ASPECT_THEMES:
        aspect = "winter"
    a = ASPECT_THEMES[aspect][mode]

    slug = project.get("slug") or slugify(project["repo"].split("/")[-1])
    title = project.get(f"title_{view}") or project.get("title_zh") or project["repo"].split("/")[-1]
    lines = resolve_work_Lines(project, view, w)
    body_font = FONT_CJK if view == "zh" else FONT_SANS
    body_size = "12.5" if view == "zh" else "12.2"
    l1_x = "15.2" if lines[0].startswith("《") else "21"

    stars_str = format_stars(int(data.get("stars", 0)))
    star_label = f"★ {stars_str}"
    star_w = int(approx_text_width(star_label, 11.4) + 22)
    star_x = w - 22 - star_w
    star_plaque = chamfer_rect_path(star_x, 18.5, star_w, 22, 4.5)

    # Stack plaques
    lang_obj = primary_language(data)
    lang_name = project.get("language") or (lang_obj["name"] if lang_obj else "Code")
    lang_color = project.get("language_color") or (
        lang_obj.get("color") if lang_obj and lang_obj.get("color") else "#70828f"
    )
    badge_mode = project.get("badge", "release")
    if badge_mode == "release":
        tag2 = data.get("tag") or project.get("tag2") or ""
    elif badge_mode == "static":
        tag2 = project.get("tag2") or project.get("badge_message") or ""
    else:
        tag2 = ""
    tag3 = project.get("tag3") or ""

    chips_svg = []
    cx = 21
    c1_w = int(approx_text_width(lang_name, 11.1) + 26)
    c1_d = chamfer_rect_path(cx, 117.5, c1_w, 21, 3.5)
    chips_svg.append(
        f'<path d="{c1_d}" fill="{s["chip_bg"]}" stroke="{s["chip_border"]}" stroke-width="0.9"/>'
        f'<path d="M {cx + 10.5:.1f} 125.3 L {cx + 13.2:.1f} 128.0 L {cx + 10.5:.1f} 130.7 L {cx + 7.8:.1f} 128.0 Z" fill="{esc(lang_color)}"/>'
        f'<text x="{cx + 18.5}" y="132" fill="{s["chip_text"]}" font-family="{FONT_MONO}" font-size="10.9" font-weight="500">{esc(lang_name)}</text>'
    )
    cx += c1_w + 7

    for extra_tag in (tag2, tag3):
        if not extra_tag:
            continue
        cw = int(approx_text_width(extra_tag, 10.8) + 16)
        if cx + cw > w - 44:
            break
        cd = chamfer_rect_path(cx, 117.5, cw, 21, 3.5)
        chips_svg.append(
            f'<path d="{cd}" fill="{s["chip_bg"]}" stroke="{s["chip_border"]}" stroke-width="0.9"/>'
            f'<text x="{cx + cw / 2:.1f}" y="132" fill="{s["chip_text"]}" font-family="{FONT_MONO}" font-size="10.7" font-weight="500" text-anchor="middle">{esc(extra_tag)}</text>'
        )
        cx += cw + 7

    uid = f"wk-{slug}-{mode}-{view}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" role="img" aria-labelledby="{uid}-t">
  <title id="{uid}-t">{esc(title)} (★ {esc(stars_str)})</title>
  <defs>
    <linearGradient id="{uid}-bg" x1="0" y1="1" x2="{w}" y2="153" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{s['bg_top']}"/>
      <stop offset="100%" stop-color="{s['bg_bot']}"/>
    </linearGradient>
    <radialGradient id="{uid}-glow" cx="92%" cy="10%" r="52%">
      <stop offset="0%" stop-color="{a['glow']}" stop-opacity="{'0.085' if mode == 'dark' else '0.055'}"/>
      <stop offset="100%" stop-color="{a['glow']}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="{uid}-top" x1="16" y1="1" x2="210" y2="1" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{a['top_line']}" stop-opacity="0.72"/>
      <stop offset="100%" stop-color="{a['top_line']}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="{uid}-clip">
      <rect x="0.5" y="1" width="{w - 1}" height="152" rx="8.5"/>
    </clipPath>
  </defs>

  <rect x="0.5" y="1" width="{w - 1}" height="152" rx="8.5" fill="url(#{uid}-bg)" stroke="{s['border']}"/>
  <rect x="1" y="1.5" width="{w - 2}" height="151" rx="8" fill="url(#{uid}-glow)"/>
  {art_deco_inner_frame(w, h, s['deco_line'], s['deco_op'], a['dot'], '0.32')}
  <line x1="16" y1="1" x2="210" y2="1" stroke="url(#{uid}-top)" stroke-width="1.4"/>

  <!-- Whisper-faint Mansus Tarot Aspect Geometry -->
  <g clip-path="url(#{uid}-clip)" opacity="{'0.06' if mode == 'dark' else '0.055'}">
    {card_aspect_watermark(aspect, a['dot'], w)}
  </g>

  <!-- Title + Mansus 4-Point Diamond Stud + Chamfered Octagonal Star Plaque -->
  {mansus_diamond_stud(26.0, 29.5, a['dot'], a['halo'], mode, 0.95)}
  <text x="40" y="35" fill="{s['title']}" font-family="{FONT_SANS}" font-size="16" font-weight="700" letter-spacing="-0.2">{esc(title)}</text>

  <path d="{star_plaque}" fill="{a['pill_bg']}" stroke="{a['pill_border']}" stroke-width="0.9"/>
  <text x="{star_x + star_w / 2:.1f}" y="33.5" fill="{a['pill_text']}" font-family="{FONT_MONO}" font-size="11.2" font-weight="600" text-anchor="middle">{esc(star_label)}</text>

  <!-- Description (2 crisp lines) -->
  <text x="{l1_x}" y="64" fill="{s['body']}" font-family="{body_font}" font-size="{body_size}" font-weight="400">{esc(lines[0])}</text>
  <text x="21" y="86.5" fill="{s['body']}" font-family="{body_font}" font-size="{body_size}" font-weight="400">{esc(lines[1])}</text>

  <!-- Hairline Divider + Chamfered Stack Plaques + Arrow -->
  <line x1="21" y1="106.5" x2="{w - 21}" y2="106.5" stroke="{s['divider']}" stroke-width="1"/>
  {''.join(chips_svg)}

  {vector_ne_arrow(w - 32, 123.5, s['muted'], 8.8, 1.45)}
</svg>
"""


def resolve_upstream_lines(entry: dict, prs: list[dict], view: str, width: int) -> list[str]:
    explicit = entry.get(f"lines_{view}")
    if explicit and len(explicit) >= 1:
        l1 = explicit[0]
        l2 = explicit[1] if len(explicit) > 1 else ""
        return [l1, l2]
    summary = entry.get(f"takeaway_{view}") or ""
    if not summary and prs:
        summary = prs[0].get("title", "")
    font_size = 11.8 if view == "zh" else 11.5
    return wrap_two_lines(summary, view, width - 34, font_size)


def make_upstream_card(entry: dict, width: int, mode: str, view: str = "zh") -> str:
    w, h = width, 124
    s = SURFACE[mode]
    full_repo = entry["repo"]
    owner, repo_name = full_repo.split("/", 1)
    slug = entry.get("slug") or slugify(repo_name)
    prs = entry.get("_prs") or []
    stars_str = format_stars(int((entry.get("_data") or {}).get("stars", 0)))

    lines = resolve_upstream_lines(entry, prs, view, w)
    body_font = FONT_CJK if view == "zh" else FONT_SANS
    body_size = "11.8" if view == "zh" else "11.5"

    star_label = f"★ {stars_str}"
    star_w = int(approx_text_width(star_label, 10.5) + 18)
    star_x = w - 17 - star_w
    star_d = chamfer_rect_path(star_x, 14.0, star_w, 19, 3.8)

    pr_nums = " · ".join(f"#{p['number']}" for p in prs)
    pr_label = f"Merged {pr_nums}" if pr_nums else "Merged PR"
    pr_w = int(approx_text_width(pr_label, 10.4) + 18)
    pr_d = chamfer_rect_path(17, 94.5, pr_w, 19, 3.8)

    uid = f"up-{slug}-{mode}-{view}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" role="img" aria-labelledby="{uid}-t">
  <title id="{uid}-t">{esc(owner)}/{esc(repo_name)} ({esc(pr_label)})</title>
  <defs>
    <linearGradient id="{uid}-bg" x1="0" y1="1" x2="{w}" y2="{h - 1}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{s['bg_top']}"/>
      <stop offset="100%" stop-color="{s['bg_bot']}"/>
    </linearGradient>
  </defs>

  <rect x="0.5" y="1" width="{w - 1}" height="{h - 2}" rx="8.5" fill="url(#{uid}-bg)" stroke="{s['border']}"/>
  {art_deco_inner_frame(w, h, s['deco_line'], s['deco_op'], s['pr_purple'], '0.28')}

  <!-- Git Merge Icon + Owner + Chamfered Star Plaque -->
  <g transform="translate(17, 16)" stroke="{s['pr_purple']}" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <circle cx="3" cy="3" r="2.1"/>
    <circle cx="3" cy="11" r="2.1"/>
    <circle cx="11" cy="9" r="2.1"/>
    <line x1="3" y1="5.1" x2="3" y2="8.9"/>
    <path d="M5 3.5 C8 3.5, 11 5, 11 6.8"/>
  </g>
  <text x="35" y="26" fill="{s['muted']}" font-family="{FONT_MONO}" font-size="10.7" font-weight="500">{esc(owner)} /</text>

  <path d="{star_d}" fill="{s['chip_bg']}" stroke="{s['chip_border']}" stroke-width="0.9"/>
  <text x="{star_x + star_w / 2:.1f}" y="27" fill="{s['chip_text']}" font-family="{FONT_MONO}" font-size="10.3" font-weight="600" text-anchor="middle">{esc(star_label)}</text>

  <!-- Repo Title -->
  <text x="17" y="46" fill="{s['title']}" font-family="{FONT_SANS}" font-size="14.1" font-weight="700" letter-spacing="-0.2">{esc(repo_name)}</text>

  <!-- 2-Line Summary -->
  <text x="17" y="66.5" fill="{s['body']}" font-family="{body_font}" font-size="{body_size}">{esc(lines[0])}</text>
  <text x="17" y="84.5" fill="{s['body']}" font-family="{body_font}" font-size="{body_size}">{esc(lines[1])}</text>

  <!-- Chamfered Merged PR Plaque -->
  <path d="{pr_d}" fill="{s['pr_pill_bg']}" stroke="{s['pr_pill_border']}" stroke-width="0.9"/>
  <text x="{17 + pr_w / 2:.1f}" y="107.5" fill="{s['pr_purple']}" font-family="{FONT_MONO}" font-size="10.3" font-weight="600" text-anchor="middle">{esc(pr_label)}</text>

  {vector_ne_arrow(w - 25, 100, s['muted'], 7.8, 1.35)}
</svg>
"""


def picture_link(href: str, alt: str, stem: str, width: int, height: int) -> str:
    return (
        f'<a href="{esc(href)}">'
        f"<picture>"
        f'<source media="(prefers-color-scheme: dark)" srcset="./assets/{stem}-dark.svg">'
        f'<source media="(prefers-color-scheme: light)" srcset="./assets/{stem}-light.svg">'
        f'<img alt="{esc(alt)}" src="./assets/{stem}-light.svg" width="{width}" height="{height}">'
        f"</picture></a>"
    )


def render_featured_bento(cfg: dict, data: dict) -> tuple[str, str, dict[str, str]]:
    """生成「造物 · WORKS」的中英文 GFM 片段与全部配套深浅色 SVG 字典。"""
    projects = cfg.get("featured") or []
    if not projects:
        return "", "", {}

    svgs: dict[str, str] = {}
    count_roman = to_roman(len(projects))
    right_meta = f"I — {count_roman}" if len(projects) > 1 else "I"

    for mode in ("dark", "light"):
        svgs[f"section-works-{mode}.svg"] = make_section_header(
            mode, "造物", "WORKS", right_meta, "winter"
        )
        svgs[f"section-works-en-{mode}.svg"] = make_section_header(
            mode, "WORKS", "CATALOGUE", right_meta, "winter"
        )

    rows_zh: list[str] = []
    rows_en: list[str] = []

    for idx in range(0, len(projects), 2):
        pair = projects[idx : idx + 2]
        width = 414 if len(pair) == 2 else 836
        pair_links_zh: list[str] = []
        pair_links_en: list[str] = []

        for offset, p in enumerate(pair):
            repo = p["repo"]
            slug = p.get("slug") or slugify(repo.split("/")[-1])
            fallback_aspect = ASPECT_CYCLE[(idx + offset) % len(ASPECT_CYCLE)]
            repo_data = data[repo]
            stars_str = format_stars(int(repo_data.get("stars", 0)))
            url = f"https://github.com/{repo}"

            for mode in ("dark", "light"):
                svgs[f"work-{slug}-{mode}.svg"] = make_work_card(
                    p, repo_data, mode, "zh", fallback_aspect, width
                )
                svgs[f"work-{slug}-en-{mode}.svg"] = make_work_card(
                    p, repo_data, mode, "en", fallback_aspect, width
                )

            title_zh = p.get("title_zh") or repo.split("/")[-1]
            title_en = p.get("title_en") or title_zh
            lines_zh = resolve_work_Lines(p, "zh", width)
            lines_en = resolve_work_Lines(p, "en", width)
            alt_zh = f"{title_zh} (★ {stars_str}): {''.join(lines_zh)}"
            alt_en = f"{title_en} (★ {stars_str}): {' '.join(x for x in lines_en if x)}"

            pair_links_zh.append(picture_link(url, alt_zh, f"work-{slug}", width, 154))
            pair_links_en.append(picture_link(url, alt_en, f"work-{slug}-en", width, 154))

        rows_zh.append("&#8194;".join(pair_links_zh))
        rows_en.append("&#8194;".join(pair_links_en))

    sec_zh = picture_link(
        "https://github.com/Cec1c?tab=repositories",
        "造物 · WORKS",
        "section-works",
        836,
        30,
    )
    sec_en = picture_link(
        "https://github.com/Cec1c?tab=repositories",
        f"WORKS · {right_meta}",
        "section-works-en",
        836,
        30,
    )

    md_zh = f"<p align=\"center\">{sec_zh}<br>{'<br>'.join(rows_zh)}</p>"
    md_en = f"<p align=\"center\">{sec_en}<br>{'<br>'.join(rows_en)}</p>"
    return md_zh, md_en, svgs


def _upstream_row_widths(n: int) -> list[int]:
    if n == 3:
        return [273, 274, 273]
    if n == 2:
        return [414, 414]
    return [836]


def render_contrib_bento(entries: list[dict]) -> tuple[str, str, dict[str, str]]:
    """生成「开源贡献 · UPSTREAM」的中英文 GFM 片段与全部配套深浅色 SVG 字典。"""
    if not entries:
        return "", "", {}

    svgs: dict[str, str] = {}
    total_prs = sum(len(e.get("_prs") or []) for e in entries)
    right_meta = f"{to_roman(total_prs)} MERGED"

    for mode in ("dark", "light"):
        svgs[f"section-upstream-{mode}.svg"] = make_section_header(
            mode, "开源贡献", "UPSTREAM", right_meta, "knock"
        )
        svgs[f"section-upstream-en-{mode}.svg"] = make_section_header(
            mode, "UPSTREAM", "MERGED PRs", right_meta, "knock"
        )

    rows_zh: list[str] = []
    rows_en: list[str] = []
    ledger_groups: list[str] = []

    for idx in range(0, len(entries), 3):
        chunk = entries[idx : idx + 3]
        widths = _upstream_row_widths(len(chunk))
        chunk_zh: list[str] = []
        chunk_en: list[str] = []

        for e, w in zip(chunk, widths):
            full_repo = e["repo"]
            _, repo_name = full_repo.split("/", 1)
            slug = e.get("slug") or slugify(repo_name)
            prs = e.get("_prs") or []
            stars_str = format_stars(int((e.get("_data") or {}).get("stars", 0)))
            primary_url = (
                f"https://github.com/{full_repo}/pull/{prs[0]['number']}"
                if prs
                else f"https://github.com/{full_repo}"
            )

            for mode in ("dark", "light"):
                svgs[f"upstream-{slug}-{mode}.svg"] = make_upstream_card(e, w, mode, "zh")
                svgs[f"upstream-{slug}-en-{mode}.svg"] = make_upstream_card(e, w, mode, "en")

            pr_nums = " · ".join(f"#{p['number']}" for p in prs)
            alt = f"{full_repo} (★ {stars_str}) Merged {pr_nums}".strip()
            chunk_zh.append(picture_link(primary_url, alt, f"upstream-{slug}", w, 124))
            chunk_en.append(picture_link(primary_url, alt, f"upstream-{slug}-en", w, 124))

            if prs:
                pr_anchors = " · ".join(
                    f'<a href="https://github.com/{esc(full_repo)}/pull/{p["number"]}">#{p["number"]}</a>'
                    for p in prs
                )
                ledger_groups.append(f"{esc(full_repo)} {pr_anchors}")

        rows_zh.append("&#8194;".join(chunk_zh))
        rows_en.append("&#8194;".join(chunk_en))

    sec_zh = picture_link(
        "https://github.com/Cec1c",
        "开源贡献 · UPSTREAM",
        "section-upstream",
        836,
        30,
    )
    sec_en = picture_link(
        "https://github.com/Cec1c",
        f"UPSTREAM · {right_meta}",
        "section-upstream-en",
        836,
        30,
    )

    ledger_html = (
        f"<br><sub>Merged PRs &nbsp;·&nbsp; {' &nbsp;｜&nbsp; '.join(ledger_groups)}</sub>"
        if ledger_groups
        else ""
    )
    md_zh = f"<p align=\"center\">{sec_zh}<br>{'<br>'.join(rows_zh)}{ledger_html}</p>"
    md_en = f"<p align=\"center\">{sec_en}<br>{'<br>'.join(rows_en)}{ledger_html}</p>"
    return md_zh, md_en, svgs
