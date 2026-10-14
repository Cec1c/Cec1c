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
