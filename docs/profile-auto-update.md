# 主页自动更新与留档说明

主页采用「漫宿 · 冬寂版」（Mansus Winter Bento）无框深浅双色 SVG 磁贴架构。其中的「造物 · WORKS」与「开源贡献 · UPSTREAM」两个区块及对应 SVG 磁贴由 GitHub Actions 每天北京时间 06:00 自动刷新，贪吃蛇动画每 12 小时自动更新至 `output` 分支。

## 结构与数据流

```text
.github/workflows/update-profile.yml    # 每日刷新代表作与外部贡献 SVG + README
        └─ scripts/update_profile.py    # 更新脚本
                ├─ scripts/profile_render.py   # Bento 矢量磁贴与 GFM 渲染（纯函数，可单测）
                ├─ projects.yml                # 造物白名单与忽略列表（人工维护）
                └─ contributions.yml           # 外部开源贡献概述（人工维护，可选）
.github/workflows/generate-snake.yml    # 每 12 小时生成漫宿「冬」色贪吃蛇至 output 分支
archive/                                # 历史原版与备选方案（方案三·林地志异、方案一初版）留档
```

脚本只重写两份 README 里被注释标记包裹的部分及受管 SVG（`assets/section-*.svg`、`assets/work-*.svg`、`assets/upstream-*.svg`）：

- 中文版：`<!-- PROFILE:FEATURED:START -->` / `<!-- PROFILE:CONTRIB:START -->`
- 英文版：`<!-- PROFILE-EN:FEATURED:START -->` / `<!-- PROFILE-EN:CONTRIB:START -->`

标记外部的首屏（终端 `assets/hero-terminal-*.svg`、冬之印身份卡 `assets/hero-identity-*.svg`、三准则徽章 `assets/aspects/badge-*.svg`）、无字冬之十字分割线、贪吃蛇与底部三联入口永不被更新脚本覆盖。

## 维护代表造物

编辑 `projects.yml` 的 `featured` 列表（每两个仓库排成一行）：

```yaml
  - repo: Cec1c/新仓库名
    title_zh: 卡片标题
    title_en: Card Title
    aspect: winter          # winter / lantern / knock（可选，不填自动轮转）
    badge: release          # release（默认，自动取最新 tag）/ static / stars
    tag3: "关键技术栈"       # 可选，第 3 枚铭牌
    desc_zh: 一句话讲清项目用途、核心运行方式与关键能力。
    desc_en: One concise sentence describing what it does and how it runs.
```

如需精确控制两行折行点，可直接提供两元素的 `lines_zh` 与 `lines_en` 列表。

## 维护开源贡献

外部仓库只要有已合并的 PR，就会在下次运行时自动收录到「开源贡献 · UPSTREAM」磁贴行并生成底部 PR 快捷跳转。如需自定义精炼概述，在 `contributions.yml` 补充 `takeaway_zh/en` 或 `lines_zh/en`。

## 新仓库提醒与忽略

脚本每天扫描名下「非 fork、非归档、建仓满 7 天」的公开仓库。若既不在 `featured` 也不在 `ignore` 中，会自动创建带 `profile-updater` 标签的提醒 Issue（同一仓库只提醒一次）。不展示的仓库加入 `projects.yml` 的 `ignore` 即可。
