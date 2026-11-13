#!/usr/bin/env python3
"""刷新 Cec1c 主页 README 里「造物 / 开源贡献」两个受管 Bento 区块及对应深浅色 SVG 磁贴。

设计原则：
  - 只重写 README 标记区间内部的内容与受管 SVG 磁贴，首屏终端/冬之印/贪吃蛇/底部入口不动。
  - 任何一个区块抓取失败就保留该区块与对应 SVG 原样，绝不写入半成品。
  - 幂等：数据没变时输出与原文逐字节相同，因此不会产生空提交。

用法：
    GITHUB_TOKEN=xxx python scripts/update_profile.py [--dry-run] [--skip-issues] [--skip-contrib]
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
    render_contrib_bento,
    render_featured_bento,
)

API = "https://api.github.com"
UA = "Cec1c-profile-updater"
BATCH = 20
NEW_REPO_GRACE_DAYS = 7
ISSUE_LABEL = "profile-updater"
ISSUE_MARKER = "<!-- profile-updater:new-repos -->"
MAX_PRS_PER_REPO = 3
RETRIES = 3


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
            if exc.code < 500 and exc.code != 429:
                raise last from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            last = FetchError(f"网络错误 {req.full_url}: {reason}")
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
        f"{API}/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers=headers,
        method="POST",
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


def fetch_repo_data(
    repos: list[str],
    token: str,
    lang_ignore: set[str] | None = None,
) -> dict[str, dict]:
    """批量取 latestRelease / stars / 语言构成。"""
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
                + LANG_FIELDS
                + " }"
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


def fetch_contribution_repos(viewer: str, token: str) -> dict[str, dict]:
    """取「我有 PR 贡献的外部非 fork 仓库」及其总 PR 数与当前星标。"""
    today = datetime.now(timezone.utc)
    found: dict[str, dict] = {}

    def collect(year_from: datetime, year_to: datetime) -> list[int]:
        q = (
            "{ viewer { contributionsCollection(from: %s, to: %s) {"
            " contributionYears"
            " pullRequestContributionsByRepository(maxRepositories: 100) {"
            " repository { nameWithOwner url stargazerCount isFork }"
            " contributions(first: 1) { totalCount } } } } }"
            % (
                json.dumps(year_from.strftime("%Y-%m-%dT%H:%M:%SZ")),
                json.dumps(year_to.strftime("%Y-%m-%dT%H:%M:%SZ")),
            )
        )
        coll = graphql(q, token)["viewer"]["contributionsCollection"]
        for item in coll["pullRequestContributionsByRepository"]:
            repo = item["repository"]
            full = repo["nameWithOwner"]
            if full.split("/")[0] == viewer:
                continue
            if repo.get("isFork"):
                continue
            prev_total = found.get(full, {}).get("total", 0)
            found[full] = {
                "stars": repo.get("stargazerCount", 0),
                "total": prev_total + item["contributions"]["totalCount"],
            }
        return coll.get("contributionYears") or []

    years = collect(today - timedelta(days=365), today)
    for year in years:
        if year == today.year:
            continue
        collect(
            datetime(year, 1, 1, tzinfo=timezone.utc),
            datetime(year, 12, 31, 23, 59, tzinfo=timezone.utc),
        )
    return found


def fetch_merged_prs(repo: str, viewer: str, token: str) -> list[dict]:
    """取某仓库里由我提交且确实已合并的最近若干个 PR。"""
    q_str = f"repo:{repo} is:pr author:{viewer} is:merged sort:updated-desc"
    query = (
        "{ search(query: %s, type: ISSUE, first: 20) {"
        " nodes { ... on PullRequest { number title merged mergedAt } } } }"
        % json.dumps(q_str)
    )
    data = graphql(query, token)
    nodes = (data.get("search") or {}).get("nodes") or []
    merged = [n for n in nodes if n and n.get("merged") and n.get("mergedAt")]
    merged.sort(key=lambda n: n["mergedAt"], reverse=True)
    return [{"number": n["number"], "title": n.get("title", "")} for n in merged]


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
# 标记替换与受管 SVG 写入
# --------------------------------------------------------------------------- #

def replace_section(text: str, key: str, body: str) -> tuple[str, bool]:
    """替换一对标记之间的内容。标记缺失或重复时抛错，绝不猜位置。"""
    start = f"<!-- {key}:START -->"
    end = f"<!-- {key}:END -->"
    for marker in (start, end):
        count = text.count(marker)
        if count != 1:
            raise FetchError(f"标记 {marker} 出现 {count} 次（要求恰好 1 次）")
    head, rest_text = text.split(start, 1)
    _, tail = rest_text.split(end, 1)
    return f"{head}{start}\n{body}\n{end}{tail}", True


def sync_svg_group(assets_dir: Path, prefix: str, new_svgs: dict[str, str]) -> None:
    """幂等写入受管前缀的 SVG，并清理已下架条目的残留 SVG。"""
    assets_dir.mkdir(parents=True, exist_ok=True)
    expected = set(new_svgs.keys())
    for existing in assets_dir.glob(f"{prefix}*.svg"):
        if existing.name not in expected:
            existing.unlink()
    for fname, content in new_svgs.items():
        target = assets_dir / fname
        encoded = content.encode("utf-8")
        if not target.exists() or target.read_bytes() != encoded:
            target.write_bytes(encoded)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"缺少配置文件: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def read_text_preserving_newline(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), newline


def write_text_preserving_newline(path: Path, text: str, newline: str) -> None:
    data = text.replace("\n", newline) if newline != "\n" else text
    encoded = data.encode("utf-8")
    if not path.exists() or path.read_bytes() != encoded:
        path.write_bytes(encoded)


def collect_contrib_entries(
    contrib_cfg: dict,
    discovered: dict[str, dict],
    viewer: str,
    token: str,
    ignores: set[str],
) -> list[dict]:
    """把抓到的外部仓库 + contributions.yml 的文案合并成渲染用的条目。"""
    overrides: dict[str, dict] = contrib_cfg.get("repos") or {}
    listed = [r for r in overrides if r in discovered and r not in ignores]
    listed.sort(key=lambda r: (overrides[r].get("order", 1000), r.lower()))
    rest_repos = sorted(
        (r for r in discovered if r not in overrides and r not in ignores),
        key=lambda r: (-discovered[r]["total"], r.lower()),
    )
    ordered: list[str] = listed + rest_repos

    entries: list[dict] = []
    for repo in ordered:
        prs = fetch_merged_prs(repo, viewer, token)[:MAX_PRS_PER_REPO]
        if not prs:
            continue
        entry = dict(overrides.get(repo) or {})
        entry["repo"] = repo
        entry["_data"] = discovered[repo]
        entry["_prs"] = prs
        entries.append(entry)
    return entries


def detect_new_repos(
    cfg: dict,
    contrib_cfg: dict,
    owned: list[dict],
    viewer: str,
    token: str,
) -> list[dict]:
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
        "主页更新脚本发现了下面这些仓库：它们建仓已满 7 天，既不在 `projects.yml` 的 `featured` 里，也不在 `ignore` 里。",
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
        "**要上主页造物列表**：加进 `projects.yml` 的 `featured`，补上中英文案即可。",
        "**不展示**：加进 `projects.yml` 的 `ignore`，以后不会再提醒。",
        "",
        "处理完可以直接关掉这个 Issue；脚本不会重复提醒已经在这里出现过的仓库。",
    ]
    if dry_run:
        print(f"[dry-run] 会开 Issue：{title}")
        return
    try:
        rest(
            f"/repos/{viewer}/{viewer}/labels",
            token,
            "POST",
            {"name": ISSUE_LABEL, "color": "9c55d4", "description": "主页自动更新脚本使用"},
        )
    except FetchError:
        pass
    payload = {"title": title, "body": "\n".join(lines), "labels": [ISSUE_LABEL]}
    created = rest(f"/repos/{viewer}/{viewer}/issues", token, "POST", payload)
    print(f"已开 Issue: {created.get('html_url')}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent.parent),
        help="配置文件所在目录（默认仓库根目录）",
    )
    ap.add_argument("--dry-run", action="store_true", help="只渲染不写文件")
    ap.add_argument("--skip-issues", action="store_true", help="跳过新仓库提醒")
    ap.add_argument("--skip-contrib", action="store_true", help="跳过贡献区块（无 PAT 时可用）")
    args = ap.parse_args()

    config_dir = Path(args.config)
    assets_dir = config_dir / "assets"
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("PROFILE_PAT") or ""
    if not token:
        raise SystemExit("需要设置 GITHUB_TOKEN（或本地用 gh auth token）")
    viewer_token = os.environ.get("PROFILE_PAT") or os.environ.get("GITHUB_TOKEN") or ""

    viewer = os.environ.get("GITHUB_REPOSITORY_OWNER") or ""
    if not viewer:
        viewer = rest("/user", viewer_token)["login"]
    print(
        f"以 {viewer} 身份运行（{'dry-run' if args.dry_run else '写入模式'}，"
        f"贡献图凭证：{'PAT' if os.environ.get('PROFILE_PAT') else '默认 token'}）"
    )

    cfg = load_yaml(config_dir / "projects.yml")
    contrib_cfg = load_yaml(config_dir / "contributions.yml")
    featured_repos = [p["repo"] for p in (cfg.get("featured") or [])]
    data = fetch_repo_data(featured_repos, token, set(cfg.get("language_ignore") or []))
    for repo, info in data.items():
        print(f"  {repo}: ★{info['stars']} tag={info['tag']}")

    readme_zh, nl_zh = read_text_preserving_newline(config_dir / "README.md")
    readme_en, nl_en = read_text_preserving_newline(config_dir / "README.en.md")
    failed = False

    # --- 造物（WORKS）区块 ---
    featured_zh, featured_en, work_svgs = render_featured_bento(cfg, data)
    if featured_zh and featured_en:
        readme_zh, _ = replace_section(readme_zh, "PROFILE:FEATURED", featured_zh)
        readme_en, _ = replace_section(readme_en, "PROFILE-EN:FEATURED", featured_en)
        if not args.dry_run:
            sec_svgs = {k: v for k, v in work_svgs.items() if k.startswith("section-works")}
            card_svgs = {k: v for k, v in work_svgs.items() if k.startswith("work-")}
            sync_svg_group(assets_dir, "section-works", sec_svgs)
            sync_svg_group(assets_dir, "work-", card_svgs)

    # --- 开源贡献（UPSTREAM）区块 ---
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
            body_zh, body_en, upstream_svgs = render_contrib_bento(entries)
            if body_zh and body_en:
                readme_zh, _ = replace_section(readme_zh, "PROFILE:CONTRIB", body_zh)
                readme_en, _ = replace_section(readme_en, "PROFILE-EN:CONTRIB", body_en)
                if not args.dry_run:
                    sec_up = {k: v for k, v in upstream_svgs.items() if k.startswith("section-upstream")}
                    card_up = {k: v for k, v in upstream_svgs.items() if k.startswith("upstream-")}
                    sync_svg_group(assets_dir, "section-upstream", sec_up)
                    sync_svg_group(assets_dir, "upstream-", card_up)
        except FetchError as exc:
            print(f"!! 贡献区块抓取失败，保留原样：{exc}", file=sys.stderr, flush=True)
            failed = True

    if args.dry_run:
        out = config_dir / "readme.preview.zh.md"
        write_text_preserving_newline(out, readme_zh, nl_zh)
        print(f"dry-run：渲染结果写到 {out}，未改动 README / assets")
        return 0

    write_text_preserving_newline(config_dir / "README.md", readme_zh, nl_zh)
    write_text_preserving_newline(config_dir / "README.en.md", readme_en, nl_en)
    print("已同步写入 README.md / README.en.md / assets/*.svg")

    # --- 新仓库提醒 ---
    if not args.skip_issues:
        try:
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
