"""Profile README 卡片的渲染器。

只做一件事：把「配置 + 抓取到的仓库数据」渲染成 README 用的 HTML 表格。
不联网、不读文件，因此可以被单元校验脚本直接复用。
"""

from __future__ import annotations

import re
from html import escape
from urllib.parse import quote

IND = "      "  # 卡片内部缩进，与现有 README 保持一致

# YAML 折叠块在合并行时会插入空格，落点若紧贴中文标点就多出一个空格，这里只收敛这一种情况。
# 注意不要动「英文 与 中文」之间的空格——那是原稿里有意保留的排版。
CJK_SPACE = re.compile(r"\s+(?=[，。、；：！？）」』】…])|(?<=[（「『【])\s+")

DEFAULT_RELEASE_COLOR = "9c55d4"
DEFAULT_STAR_COLOR = "d8c66b"
DEFAULT_CONTRIB_STAR_COLOR = "9c55d4"


def clean(text: str, view: str) -> str:
    """中文视图下收敛 YAML 折行带来的标点旁多余空格；英文原样返回。"""
    return CJK_SPACE.sub("", text) if view == "zh" else text


def _star_badge(repo: str, alt: str, color: str) -> str:
    return (
        f'<a href="https://github.com/{repo}/stargazers">'
        f'<img src="https://img.shields.io/github/stars/{repo}?style=flat-square&amp;color={color}"'
        f' alt="{escape(alt)} stars" /></a>'
    )


def _release_badge(repo: str, alt: str, color: str) -> str:
    return (
        f'<a href="https://github.com/{repo}/releases/latest">'
        f'<img src="https://img.shields.io/github/v/release/{repo}'
        f'?sort=date&amp;display_name=tag&amp;style=flat-square&amp;color={color}"'
        f' alt="{escape(alt)} release" /></a>'
    )


def primary_language(data: dict) -> dict | None:
    """取仓库的主语言（字节数最大的那个）。GitHub 返回的顺序已按 SIZE 降序。"""
    langs = data.get("languages") or []
    return langs[0] if langs else None


def aggregate_languages(repo_langs: dict[str, list[dict]], ignore: set[str], top: int) -> list[dict]:
    """把各仓库的语言字节数汇总，返回占比最高的前 top 个。

    占比按「该语言字节数 / 全部语言字节数」计算——也就是 GitHub 自己的口径。
    """
    totals: dict[str, dict] = {}
    for langs in repo_langs.values():
        for lang in langs:
            name = lang.get("name")
            if not name or name in ignore:
                continue
            entry = totals.setdefault(name, {"name": name, "color": lang.get("color"), "size": 0})
            entry["size"] += lang.get("size") or 0
    grand = sum(e["size"] for e in totals.values()) or 1
    ranked = sorted(totals.values(), key=lambda e: (-e["size"], e["name"]))
    for entry in ranked:
        entry["percent"] = entry["size"] * 100.0 / grand
    return ranked[:top]


LANG_FALLBACK_COLOR = "8b8b8b"


def _language_badge(name: str, color: str | None = None) -> str:
    """语言徽章：用 GitHub 的官方语言色。

    shields.io 的路径里 `-` 是分隔符，字面量要写两次；空格写成下划线。
    先做这两个替换，再逐字节百分号编码——直接交给 quote() 会把 `--` 也编掉。
    """
    text = name.replace("-", "--").replace(" ", "_")
    encoded = "".join(c if c.isalnum() or c in "._~" else f"%{ord(c):02X}" for c in text)
    hexcolor = (color or LANG_FALLBACK_COLOR).lstrip("#")
    search = quote(f"language:{name}", safe="")
    return (
        f'<a href="https://github.com/search?q={search}&amp;type=repositories">'
        f'<img src="https://img.shields.io/badge/{encoded}-{hexcolor}?style=flat-square"'
        f' alt="{escape(name)}" /></a>'
    )


def build_toolbelt(ranked: list[dict], pinned: list[str], top: int) -> str:
    """底部工具栈。

    pinned 里的语言（toolbelt_extra）永远上榜并排在最前——它们代表「你想让人看到的
    技术栈」；剩余位置由实际字节占比最高的语言（ranked）补齐，代表「你实际写的代码」。
    """
    by_name = {l["name"]: l for l in ranked}
    chosen: list[dict] = []
    for name in pinned:
        entry = by_name.get(name) or {"name": name, "color": None}
        chosen.append({**entry, "pinned": True})
    for entry in ranked:
        if len(chosen) >= top:
            break
        if entry["name"] not in pinned:
            chosen.append({**entry, "pinned": False})
    if not chosen:
        return ""
    lines = [f"  {_language_badge(l['name'], l.get('color'))}" for l in chosen]
    return '<p align="center">\n' + "\n".join(lines) + "\n</p>"


def _static_badge(repo: str, label: str, message: str, color: str) -> str:
    # shields.io 用 + 表示空格，alt 文本里还原成空格更易读（"Python: MCP Server"）
    alt = f"{label}: {message.replace('+', ' ')}"
    return (
        f'<a href="https://github.com/{repo}">'
        f'<img src="https://img.shields.io/static/v1?label={quote(label, safe="")}'
        f'&amp;message={quote(message, safe="+")}&amp;color={color}&amp;style=flat-square"'
        f' alt="{escape(alt)}" /></a>'
    )


def build_badges(project: dict, data: dict, view: str = "zh",
                 alt: str | None = None, fallback_star_color: str = DEFAULT_STAR_COLOR) -> str:
    """按配置生成一张卡片的徽章行内容（不含外层 <p>）。

    alt 用于徽章的无障碍文本，默认取卡片标题；配置里的 ``alt_zh`` / ``alt_en``
    可覆盖（现有 README 中「Codex-Cli-Ultra」的 alt 写成「Codex CLI Ultra」即属此例）。
    """
    repo = project["repo"]
    if alt is None:
        alt = (
            project.get(f"alt_{view}")
            or (project.get("title_zh") if view == "zh" else project.get("title_en"))
            or project.get("title_zh")
            or repo.split("/")[-1]
        )
    mode = project.get("badge", "release")
    star_color = project.get("star_color", fallback_star_color)

    parts: list[str] = []
    # 语言徽章放最前面：它描述「这是什么项目」，比版本号更先被看到。
    # 默认取仓库主语言，projects.yml 里的 language 字段可覆盖 GitHub 的判定。
    lang_name = project.get("language")
    if lang_name:
        parts.append(_language_badge(lang_name, project.get("language_color")))
    else:
        lang = primary_language(data)
        if lang:
            parts.append(_language_badge(lang["name"], lang.get("color")))

    if mode == "release":
        if data.get("tag"):
            parts.append(_release_badge(repo, alt, project.get("release_color", DEFAULT_RELEASE_COLOR)))
        parts.append(_star_badge(repo, alt, star_color))
    elif mode == "static":
        parts.append(
            _static_badge(repo, project.get("badge_label", ""), project.get("badge_message", ""),
                          project.get("badge_color", DEFAULT_RELEASE_COLOR))
        )
        parts.append(_star_badge(repo, alt, star_color))
    elif mode == "stars":
        parts.append(_star_badge(repo, alt, star_color))
    else:
        raise ValueError(f"{repo}: 未知的 badge 模式 {mode!r}")

    return "\n".join(parts)


def build_card(project: dict, data: dict, view: str, fallback_star_color: str = DEFAULT_STAR_COLOR) -> str:
    """生成一张项目卡片（<td>…</td>）。view 取 'zh' 或 'en'。"""
    repo = project["repo"]
    title = project.get(f"title_{view}") or project.get("title_zh") or repo.split("/")[-1]
    desc = clean(project.get(f"desc_{view}", ""), view)

    body: list[str] = [
        f'{IND}<h3>{title}</h3>',
        f"{IND}<p>",
        f'{IND}  <a href="https://github.com/{repo}"><b>{repo}</b></a>',
        f"{IND}  {desc}",
        f"{IND}</p>",
    ]

    extra = project.get(f"extra_{view}")
    if extra:
        body.append(f"{IND}<p>{clean(extra, view)}</p>")

    for link in project.get("links") or []:
        label = link.get(f"label_{view}") or link.get("label_en") or link["url"]
        body.append(f'{IND}<p><a href="{link["url"]}">{label}</a></p>')

    badges = build_badges(project, data, view, fallback_star_color=fallback_star_color).splitlines()
    body.append(f"{IND}<p>")
    body.extend(f"{IND}  {line}" for line in badges)
    body.append(f"{IND}</p>")

    inner = "\n".join(body)
    return f'    <td width="50%" valign="top">\n{inner}\n    </td>'


def build_contribution_card(entry: dict, repo_data: dict, prs: list[dict], view: str,
                            star_color: str = DEFAULT_CONTRIB_STAR_COLOR) -> str:
    """生成一张「参与和工具」卡片。prs 为 [{number, title}]，已按新→旧排序。"""
    repo = entry["repo"]
    name = entry.get(f"title_{view}") or repo.split("/")[-1]
    takeaway = clean(entry.get(f"takeaway_{view}") or "", view)
    sep = "：" if view == "zh" else ": "

    head = [
        f"{IND}<h3>{name}</h3>",
        f"{IND}<p>",
        f'{IND}  <a href="https://github.com/{repo}"><b>{repo}</b></a>',
    ]
    if takeaway:
        head.append(f"{IND}  {takeaway}")
    head.append(f"{IND}</p>")
    body: list[str] = head

    for pr in prs:
        number = pr["number"]
        overrides = (entry.get("prs") or {}).get(str(number)) or (entry.get("prs") or {}).get(number) or {}
        text = overrides.get(view) or pr.get("title", "")
        body.append(
            f'{IND}<p><a href="https://github.com/{repo}/pull/{number}">Merged PR #{number}</a>'
            f"{sep}{text}</p>"
        )

    # 徽章 alt：现有 README 两处写法不一（CPA-Manager-Plus 用仓库名、本地化项目用英文全称），
    # 因此默认取仓库名，可由配置的 alt 字段覆盖。
    alt = entry.get("alt") or repo.split("/")[-1]
    rows = [_star_badge(repo, alt, star_color)]
    for pr in prs:
        number = pr["number"]
        rows.append(
            f'<a href="https://github.com/{repo}/pull/{number}">'
            f'<img src="https://img.shields.io/badge/merged-PR%20%23{number}-d8c66b?style=flat-square"'
            f' alt="Merged PR {number}" /></a>'
        )
    body.append(f"{IND}<p>")
    body.extend(f"{IND}  {row}" for row in rows)
    body.append(f"{IND}</p>")

    inner = "\n".join(body)
    return f'    <td width="50%" valign="top">\n{inner}\n    </td>'


def build_table(cards: list[str]) -> str:
    """把卡片两两一行拼成表格；奇数张时最后一行只放一张。"""
    if not cards:
        return ""
    rows = []
    for i in range(0, len(cards), 2):
        pair = cards[i : i + 2]
        rows.append("  <tr>\n" + "\n".join(pair) + "\n  </tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"
