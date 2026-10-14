# 主页自动更新说明

主页 README 里的「近期项目 / 参与和工具 / 其他项目」三个区块由 GitHub Actions 自动维护，
每天北京时间 06:00 刷新一次，也可以在任何时候手动触发。

## 它是怎么工作的

```
.github/workflows/update-profile.yml   # 定时任务
        └─ scripts/update_profile.py   # 更新脚本
                ├─ scripts/profile_render.py   # 卡片渲染（不联网，可单独测试）
                ├─ projects.yml                # 项目白名单（人工维护）
                └─ contributions.yml           # 贡献文案覆盖（人工维护，可选）
```

脚本只重写 README 里被注释标记圈住的部分：

```markdown
<!-- PROFILE:FEATURED:START -->
...这一段是脚本生成的，不要手改...
<!-- PROFILE:FEATURED:END -->
```

标记外面的内容（终端头部、工具栈、状态条、公益服务器区块、结语）永远不动。

## 加一个新项目

1. 在 `projects.yml` 里选一个区块：
   - `featured` → README 的「近期项目」
   - `others` → README 的「其他项目」
2. 追加一条，填写中英文案：

```yaml
  - repo: Cec1c/新仓库名
    title_zh: 卡片标题
    title_en: Card Title
    desc_zh: 一句话或一段话的中文简介。
    desc_en: One or two sentences in English.
    badge: release      # release / static / stars，多数情况不用写（默认 release）
```

改完提交，等下一次定时任务，或手动触发一次 workflow 即可。

## 想让某个 PR 出现在「参与和工具」

不需要做任何事。只要 PR 合并了，脚本会在下次运行时自动发现它，并带着 PR 标题出现在主页上。

如果想给它写更好的中文说明，在 `contributions.yml` 里补一条：

```yaml
repos:
  owner/repo:
    order: 3                    # 卡片排序，数字小的在前
    title_zh: 卡片标题
    takeaway_zh: 参与做了什么，一句话概述。
    prs:
      123:                      # PR 编号
        zh: 这个 PR 具体改了什么。
        en: What this PR changed.
```

没写的部分会降级：没有 takeaway 就只显示仓库链接，没有 PR 说明就显示 PR 原始标题。

## 不想让某个仓库出现 / 被提醒

在 `projects.yml` 的 `ignore` 里加上 `owner/name`。加进去之后既不会上榜，也不会再收到提醒。

## 新仓库提醒

脚本每天扫描你名下「非 fork、非归档、建仓满 7 天」的仓库，发现既不在白名单也不在 `ignore`
里的，就开一个带 `profile-updater` 标签的 Issue 列出来。同一个仓库只提醒一次，无论 Issue
是否关闭。

- **要收录** → 按上面的「加一个新项目」操作，然后关掉 Issue。
- **不收录** → 加进 `ignore`，然后关掉 Issue。

## 关于 PROFILE_PAT

「参与和工具」区块需要读你的贡献图，而 Actions 自带的 `GITHUB_TOKEN` 读不到，因此需要一个
用户级凭证，存在仓库 Secret 里，名字叫 `PROFILE_PAT`。

创建方式（任选其一）：

- **Fine-grained token**：Settings → Developer settings → Personal access tokens → Fine-grained tokens，
  只勾 `Public repositories` 的只读权限即可。
- **Classic token**：同一个页面里的 Classic 分支，勾 `read:user`。

建好后在仓库的 Settings → Secrets and variables → Actions 里新建名为 `PROFILE_PAT` 的 Secret。

**如果这个 Secret 缺失或过期**：脚本会打印明确的警告，贡献区块保持上一次的内容不变，
其他区块照常更新，并且以非零退出码结束（Actions 会显示为失败，你就能注意到）。

## 出问题时怎么办

| 现象 | 原因与处理 |
|---|---|
| Actions 失败，日志里有 `Bad credentials` | `PROFILE_PAT` 过期，重新生成并更新 Secret |
| 日志里有 `标记 ... 出现 0 次` | README 里的标记被误删了，对照上面的格式补回成对标记 |
| 主页某张卡片的版本号看着旧 | 该仓库的 GitHub Release 没有标记为 "Latest"，在 Releases 页面点一下 `Set as the latest release` |
| 想立刻刷新而不是等到明天 | 仓库 Actions 页面 → Update Profile README → Run workflow |
| 数据没变化但产生了提交 | 不应该发生。脚本对相同输入产生逐字节相同的输出，若有请检查是否有手工改动落在标记区间内 |
