#!/usr/bin/env python3
"""刷新 Cec1c 主页 README 里三个受管区块的数据。

设计原则：
  - 只重写标记区间内部的内容，区间外一个字节都不动。
  - 任何一个区块抓取失败就保留该区块原样，绝不写入半成品。
  - 幂等：数据没变时输出与原文逐字节相同，因此不会产生空提交。

用法：
    GITHUB_TOKEN=xxx python scripts/update_profile.py [--dry-run] [--skip-issues]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_render import (  # noqa: E402
    DEFAULT_CONTRIB_STAR_COLOR,
    DEFAULT_STAR_COLOR,
    aggregate_languages,
    build_card,
    build_contribution_card,
    build_table,
    build_toolbelt,
)

API = "https://api.github.com"
UA = "Cec1c-profile-updater"
BATCH = 20
NEW_REPO_GRACE_DAYS = 7
ISSUE_LABEL = "profile-updater"
ISSUE_MARKER = "<!-- profile-updater:new-repos -->"
MAX_PRS_PER_REPO = 2
SEARCH_INTERVAL = 2.0  # search API 限流较严，逐个仓库串行并留间隔
RETRIES = 3  # GitHub 的 search 接口偶发 5xx，重试几次再放弃

# 受管区块 -> README 里的标记前缀
SECTIONS = ("FEATURED", "CONTRIB", "OTHERS", "TOOLBELT")


class FetchError(RuntimeError):
    """抓取失败。调用方据此保留原有内容。"""


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #

def _open(req: urllib.request.Request):
    last: FetchError | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            last = FetchError(f"HTTP {exc.code} {req.full_url}: {detail}")
            # 4xx 是请求本身的问题，重试没有意义；5xx 与限流才重试
            if exc.code < 500 and exc.code != 429:
                raise last from exc
        except urllib.error.URLError as exc:
            last = FetchError(f"网络错误 {req.full_url}: {exc.reason}")
        if attempt < RETRIES - 1:
            time.sleep(2 ** attempt * 2)
    raise last  # type: ignore[misc]


def rest(path: str, token: str, method: str = "GET", payload: dict | None = None):
    url = path if path.startswith("http") else API + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    return _open(req)


def graphql(query: str, token: str) -> dict:
    headers = {
        "User-Agent": UA,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    req = urllib.request.Request(
        f"{API}/graphql", data=json.dumps({"query": query}).encode("utf-8"),
        headers=headers, method="POST",
    )
    body = _open(req)
    if "errors" in body:
        raise FetchError(f"GraphQL 错误: {json.dumps(body['errors'], ensure_ascii=False)[:400]}")
    return body["data"]


# --------------------------------------------------------------------------- #
# 抓取
# --------------------------------------------------------------------------- #

LANG_FIELDS = (
    " languages(first: 12, orderBy: {field: SIZE, direction: DESC})"
    " { edges { size node { name color } } }"
)


def _languages_of(node: dict) -> list[dict]:
    return [
        {"name": e["node"]["name"], "color": e["node"].get("color"), "size": e.get("size") or 0}
        for e in (node.get("languages") or {}).get("edges", [])
    ]


def fetch_repo_data(repos: list[str], token: str, lang_ignore: set[str] | None = None
                    ) -> dict[str, dict]:
    """批量取 latestRelease / stars / 语言构成。一次请求覆盖最多 BATCH 个仓库。

    lang_ignore 里的语言不算「主语言」——比如 .ftl 翻译文件不该让一张卡片显得像是
    用 Fluent 写的一样。它只影响卡片判定，与底部工具栈的统计相互独立。
    """
    lang_ignore = lang_ignore or set()
    out: dict[str, dict] = {}
    for i in range(0, len(repos), BATCH):
        chunk = repos[i : i + BATCH]
        blocks = []
        for idx, full in enumerate(chunk):
            owner, name = full.split("/", 1)
            blocks.append(
                f'  r{idx}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{'
                " nameWithOwner stargazerCount"
                " latestRelease { tagName isPrerelease isDraft }"
                + LANG_FIELDS + " }"
            )
        data = graphql("{\n" + "\n".join(blocks) + "\n}", token)
        for idx, full in enumerate(chunk):
            node = data.get(f"r{idx}")
            if node is None:
                raise FetchError(f"仓库不存在或无权访问: {full}")
            release = node.get("latestRelease") or {}
            tag = release.get("tagName")
            if release.get("isDraft"):
                tag = None
            out[full] = {
                "stars": node.get("stargazerCount", 0),
                "tag": tag,
                "languages": [l for l in _languages_of(node) if l["name"] not in lang_ignore],
            }
    return out


def fetch_languages_only(repos: list[str], token: str) -> dict[str, list[dict]]:
    """只取语言构成，用于底部工具栈的统计。

    与 fetch_repo_data 分开是因为工具栈要统计**所有**仓库，而不只是白名单里的；
    其中可能有已删除或改名、查不到的仓库，跳过即可，不影响其余统计。
    """
    out: dict[str, list[dict]] = {}
    for i in range(0, len(repos), BATCH):
        chunk = repos[i : i + BATCH]
        blocks = []
        for idx, full in enumerate(chunk):
            owner, name = full.split("/", 1)
            blocks.append(
                f'  r{idx}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{'
                + LANG_FIELDS + " }"
            )
        data = graphql("{\n" + "\n".join(blocks) + "\n}", token)
        for idx, full in enumerate(chunk):
            node = data.get(f"r{idx}")
            if node:
                out[full] = _languages_of(node)
    return out


def fetch_contribution_repos(viewer: str, token: str) -> dict[str, dict]:
    """取「我有 merged/open PR 的外部仓库」及其总 PR 数。"""
    today = datetime.now(timezone.utc)
    found: dict[str, dict] = {}

    def collect(year_from: datetime, year_to: datetime) -> list[int]:
        q = (
            "{ viewer { contributionsCollection(from: %s, to: %s) {"
            " contributionYears"
            " pullRequestContributionsByRepository(maxRepositories: 100) {"
            " repository { nameWithOwner url stargazerCount isFork }"
            " contributions(first: 1) { totalCount } } } } }"
            % (json.dumps(year_from.strftime("%Y-%m-%dT%H:%M:%SZ")),
               json.dumps(year_to.strftime("%Y-%m-%dT%H:%M:%SZ")))
        )
        coll = graphql(q, token)["viewer"]["contributionsCollection"]
        for item in coll["pullRequestContributionsByRepository"]:
            repo = item["repository"]
            full = repo["nameWithOwner"]
            if full.split("/")[0] == viewer:
                continue  # 自己名下的仓库走 projects.yml，不进「参与和工具」
            if repo.get("isFork"):
                # 别人 fork 出来的仓库不算上游贡献；自己的 fork 已在 ignore 里排除
                continue
            found[full] = {"stars": repo.get("stargazerCount", 0), "total": item["contributions"]["totalCount"]}
        return coll.get("contributionYears") or []

    years = collect(today - timedelta(days=365), today)
    for year in years:
        if year == today.year:
            continue
        collect(datetime(year, 1, 1, tzinfo=timezone.utc), datetime(year, 12, 31, 23, 59, tzinfo=timezone.utc))
    return found


def fetch_merged_prs(repo: str, viewer: str, token: str) -> list[dict]:
    """取某仓库里由我提交且**确实已合并**的最近若干个 PR。

    search 的 is:merged 限定词不可靠（会把 open 的 PR 也带回来），因此这里以
    pull_request.merged_at 是否存在为准，并按合并时间而不是创建时间排序。
    """
    query = f"repo:{repo} type:pr author:{viewer} is:merged"
    params = urllib.parse.urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": 50})
    time.sleep(SEARCH_INTERVAL)
    data = rest(f"/search/issues?{params}", token)
    merged = [
        it for it in data.get("items", [])
        if (it.get("pull_request") or {}).get("merged_at")
    ]
    merged.sort(key=lambda it: it["pull_request"]["merged_at"], reverse=True)
    return [{"number": it["number"], "title": it.get("title", "")} for it in merged]


def fetch_owner_repos(owner: str, token: str) -> list[dict]:
    out: list[dict] = []
    page = 1
    while True:
        batch = rest(f"/users/{owner}/repos?per_page=100&sort=created&direction=desc&page={page}", token)
        if not batch:
            return out
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


# --------------------------------------------------------------------------- #
# 标记替换
# --------------------------------------------------------------------------- #

def replace_section(text: str, key: str, body: str) -> tuple[str, bool]:
    """替换一对标记之间的内容。标记缺失或重复时抛错，绝不猜位置。"""
    start = f"<!-- {key}:START -->"
    end = f"<!-- {key}:END -->"
    for marker in (start, end):
        count = text.count(marker)
        if count != 1:
            raise FetchError(f"标记 {marker} 出现 {count} 次（要求恰好 1 次）")
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{start}\n{body}\n{end}{tail}", True


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"缺少配置文件: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def read_text_preserving_newline(path: Path) -> tuple[str, str]:
    """读文本并返回 (文本, 换行符)。文本统一成 \\n，写回时还原，避免污染 diff。"""
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), newline


def write_text_preserving_newline(path: Path, text: str, newline: str) -> None:
    data = text.replace("\n", newline) if newline != "\n" else text
    path.write_bytes(data.encode("utf-8"))


def build_projects_section(cfg: dict, data: dict, view: str, key: str) -> str:
    projects = cfg.get(key) or []
    cards = [build_card(p, data[p["repo"]], view, DEFAULT_STAR_COLOR) for p in projects]
    return build_table(cards)


def build_contrib_section(contrib_cfg: dict, entries: list[dict], view: str) -> str:
    star_color = contrib_cfg.get("star_color", DEFAULT_CONTRIB_STAR_COLOR)
    cards = []
    for entry in entries:
        cards.append(
            build_contribution_card(entry, entry["_data"], entry["_prs"], view, star_color)
        )
    return build_table(cards)


def collect_contrib_entries(
    contrib_cfg: dict, discovered: dict[str, dict], viewer: str, token: str, ignores: set[str]
) -> list[dict]:
    """把抓到的外部仓库 + contributions.yml 的文案合并成渲染用的条目。"""
    overrides: dict[str, dict] = contrib_cfg.get("repos") or {}
    # 顺序：配置了 order 的按 order 升序排在前面，其余按 PR 数（多的在前），保证顺序稳定可控
    listed = [r for r in overrides if r in discovered and r not in ignores]
    listed.sort(key=lambda r: (overrides[r].get("order", 1000), r.lower()))
    rest = sorted(
        (r for r in discovered if r not in overrides and r not in ignores),
        key=lambda r: (-discovered[r]["total"], r.lower()),
    )
    ordered: list[str] = listed + rest

    entries: list[dict] = []
    for repo in ordered:
        prs = fetch_merged_prs(repo, viewer, token)[:MAX_PRS_PER_REPO]
        if not prs:
            continue  # 没有真正 merged 的 PR 就不展示
        entry = dict(overrides.get(repo) or {})
        entry["repo"] = repo
        entry["_data"] = discovered[repo]
        entry["_prs"] = prs
        entries.append(entry)
    return entries


def toolbelt_repos(cfg: dict, owned: list[dict]) -> list[str]:
    """参与工具栈统计的仓库：自己名下、非 fork、非归档、且没被 ignore。"""
    ignores = set(cfg.get("ignore") or [])
    return [
        r["full_name"] for r in owned
        if not r.get("fork") and not r.get("archived") and r["full_name"] not in ignores
    ]


def detect_new_repos(cfg: dict, contrib_cfg: dict, owned: list[dict],
                     viewer: str, token: str) -> list[dict]:
    """找出「建仓已满 7 天、非 fork、未白名单、未忽略、未提醒过」的新仓库。"""
    ignores = set(cfg.get("ignore") or [])
    tracked = {p["repo"] for key in ("featured", "others") for p in (cfg.get(key) or [])}
    tracked |= set((contrib_cfg.get("repos") or {}).keys())

    cutoff = datetime.now(timezone.utc) - timedelta(days=NEW_REPO_GRACE_DAYS)
    candidates = []
    for repo in owned:
        full = repo["full_name"]
        if repo.get("fork") or repo.get("archived"):
            continue
        if full in ignores or full in tracked:
            continue
        created = datetime.strptime(repo["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if created > cutoff:
            continue
        candidates.append(repo)

    if not candidates:
        return []

    # 幂等：历史上提醒过的仓库不再提醒
    already: set[str] = set()
    params = urllib.parse.urlencode({"state": "all", "labels": ISSUE_LABEL, "per_page": 100})
    for issue in rest(f"/repos/{viewer}/{viewer}/issues?{params}", token):
        body = issue.get("body") or ""
        if ISSUE_MARKER in body:
            for line in body.splitlines():
                line = line.strip()
                if line.startswith("- `") and "`" in line[3:]:
                    already.add(line[3:].split("`", 1)[0])

    return [r for r in candidates if r["full_name"] not in already]


def open_issue(viewer: str, repos: list[dict], token: str, dry_run: bool) -> None:
    title = "[profile] 发现未收录的仓库：" + "、".join(r["name"] for r in repos)
    lines = [
        ISSUE_MARKER,
        "",
        "主页更新脚本发现了下面这些仓库：它们建仓已满 7 天，既不在 `projects.yml` 的白名单里，也不在 `ignore` 里。",
        "",
    ]
    for r in repos:
        lines.append(
            f"- `{r['full_name']}` — 建仓 {r['created_at'][:10]}，"
            f"{r.get('language') or '未知语言'}，★{r.get('stargazers_count', 0)}"
        )
        if r.get("description"):
            lines.append(f"  - {r['description']}")
    lines += [
        "",
        "**要收录**：把它加进 `projects.yml` 的 `featured` 或 `others`，补上中英文案即可。",
        "**不收录**：把它加进 `projects.yml` 的 `ignore`，以后不会再提醒。",
        "",
        "处理完可以直接关掉这个 Issue；脚本不会重复提醒已经在这里出现过的仓库。",
    ]
    if dry_run:
        print(f"[dry-run] 会开 Issue：{title}")
        return
    try:
        rest(f"/repos/{viewer}/{viewer}/labels", token, "POST",
             {"name": ISSUE_LABEL, "color": "9c55d4", "description": "主页自动更新脚本使用"})
    except FetchError:
        pass  # 标签已存在
    payload = {"title": title, "body": "\n".join(lines), "labels": [ISSUE_LABEL]}
    created = rest(f"/repos/{viewer}/{viewer}/issues", token, "POST", payload)
    print(f"已开 Issue: {created.get('html_url')}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(Path(__file__).resolve().parent.parent),
                    help="配置文件所在目录（默认仓库根目录）")
    ap.add_argument("--dry-run", action="store_true", help="只渲染不写文件")
    ap.add_argument("--skip-issues", action="store_true", help="跳过新仓库提醒")
    ap.add_argument("--skip-contrib", action="store_true", help="跳过贡献区块（无 PAT 时可用）")
    args = ap.parse_args()

    config_dir = Path(args.config)
    # 基础 token：读写仓库元数据、提交 README、开 Issue；Actions 里就是 GITHUB_TOKEN
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("PROFILE_PAT") or ""
    if not token:
        raise SystemExit("需要设置 GITHUB_TOKEN（或本地用 gh auth token）")
    # 用户级 token：只有它能读「我的贡献图」。Actions 默认 token 读不到，必须用 PAT。
    viewer_token = os.environ.get("PROFILE_PAT") or os.environ.get("GITHUB_TOKEN") or ""

    # 取用户名：Actions 里直接读环境变量，不发请求。
    # GITHUB_TOKEN 是集成身份，访问不了 /user 这个用户级接口（会 403 Resource not accessible
    # by integration），所以不能靠它；本地运行才回退到 API 查询。
    viewer = os.environ.get("GITHUB_REPOSITORY_OWNER") or ""
    if not viewer:
        viewer = rest("/user", viewer_token)["login"]
    print(f"以 {viewer} 身份运行（{'dry-run' if args.dry_run else '写入模式'}，"
          f"贡献图凭证：{'PAT' if os.environ.get('PROFILE_PAT') else '默认 token'}）")

    cfg = load_yaml(config_dir / "projects.yml")
    contrib_cfg = load_yaml(config_dir / "contributions.yml")
    data = fetch_repo_data(
        [p["repo"] for key in ("featured", "others") for p in (cfg.get(key) or [])],
        token,
        set(cfg.get("language_ignore") or []),
    )
    for repo, info in data.items():
        print(f"  {repo}: ★{info['stars']} tag={info['tag']}")

    readme_zh, nl_zh = read_text_preserving_newline(config_dir / "README.md")
    readme_en, nl_en = read_text_preserving_newline(config_dir / "README.en.md")
    failed = False  # 有任何区块降级则最终以非零码退出，让 CI 能察觉
    owned: list[dict] = []  # 自己的仓库列表，工具栈与新仓库扫描共用

    # --- 项目区块 ---
    for key in ("FEATURED", "OTHERS"):
        readme_zh, _ = replace_section(
            readme_zh, f"PROFILE:{key}", build_projects_section(cfg, data, "zh", key.lower())
        )
        readme_en, _ = replace_section(
            readme_en, f"PROFILE-EN:{key}", build_projects_section(cfg, data, "en", key.lower())
        )

    # --- 底部工具栈：按所有仓库的语言字节数汇总 ---
    try:
        owned = fetch_owner_repos(viewer, token)
        langs = fetch_languages_only(toolbelt_repos(cfg, owned), token)
        # 多取一些候选，好让 toolbelt_extra 里钉住的语言也能查到真实占比与配色
        ranked = aggregate_languages(
            langs, set(cfg.get("toolbelt_ignore") or []), max(int(cfg.get("toolbelt_top", 6)), 30)
        )
        print("  工具栈：" + "、".join(f"{l['name']} {l['percent']:.1f}%" for l in ranked[:8]))
        pinned = list(cfg.get("toolbelt_extra") or [])
        if pinned:
            print("  钉住：" + "、".join(pinned))
        body = build_toolbelt(ranked, pinned, int(cfg.get("toolbelt_top", 6)))
        if body:
            readme_zh, _ = replace_section(readme_zh, "PROFILE:TOOLBELT", body)
            readme_en, _ = replace_section(readme_en, "PROFILE-EN:TOOLBELT", body)
    except FetchError as exc:
        print(f"!! 工具栈抓取失败，保留原样：{exc}", file=sys.stderr, flush=True)
        failed = True

    # --- 贡献区块 ---
    if args.skip_contrib:
        print("按参数跳过贡献区块")
    else:
        try:
            discovered = fetch_contribution_repos(viewer, viewer_token)
            ignores = set(cfg.get("ignore") or [])
            entries = collect_contrib_entries(contrib_cfg, discovered, viewer, viewer_token, ignores)
            for repo, info in discovered.items():
                if repo not in ignores:
                    print(f"  贡献仓库 {repo}: {info['total']} PR, ★{info['stars']}")
            body_zh = build_contrib_section(contrib_cfg, entries, "zh")
            body_en = build_contrib_section(contrib_cfg, entries, "en")
            readme_zh, _ = replace_section(readme_zh, "PROFILE:CONTRIB", body_zh)
            readme_en, _ = replace_section(readme_en, "PROFILE-EN:CONTRIB", body_en)
        except FetchError as exc:
            print(f"!! 贡献区块抓取失败，保留原样：{exc}", file=sys.stderr, flush=True)
            failed = True

    if args.dry_run:
        out = config_dir / "readme.preview.zh.md"
        write_text_preserving_newline(out, readme_zh, nl_zh)
        print(f"dry-run：渲染结果写到 {out}，未改动 README")
        return 0

    write_text_preserving_newline(config_dir / "README.md", readme_zh, nl_zh)
    write_text_preserving_newline(config_dir / "README.en.md", readme_en, nl_en)
    print("已写入 README.md / README.en.md")

    # --- 新仓库提醒 ---
    if not args.skip_issues:
        try:
            if not owned:
                owned = fetch_owner_repos(viewer, token)
            new_repos = detect_new_repos(cfg, contrib_cfg, owned, viewer, token)
            if new_repos:
                open_issue(viewer, new_repos, token, args.dry_run)
            else:
                print("没有未收录的新仓库")
        except FetchError as exc:
            print(f"!! 新仓库扫描失败：{exc}", file=sys.stderr, flush=True)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
