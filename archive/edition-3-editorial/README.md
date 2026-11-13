<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/masthead-dark.svg">
  <img src="./assets/masthead-light.svg" alt="Cec1c — 林地志异 · 器物、接口与长线服务索引" width="840" height="82">
</picture>

<p>
  <sub>个人博客 <a href="https://mansus.cc"><strong>mansus.cc</strong></a> &nbsp;·&nbsp; <strong>简体中文</strong> / <a href="./README.en.md">English</a> &nbsp;·&nbsp; 三卷索引：冬（器物） · 启（接口） · 灯（长明）</sub>
</p>

这里按三卷整理我写过的独立程序、协议扩展、上游补丁与长线服务端。多数本地工具围绕单一具体问题写成，在各自边界内定型完结，安静留驻桌面而无需频繁更迭；服务端与配套网关则随社区日常运行持续维护。

<h3>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/chapter-winter-dark.svg">
    <img src="./assets/chapter-winter-light.svg" alt="Chapter I · Winter" width="840" height="38">
  </picture><br>
  <img src="./assets/aspects/badge-winter.svg" alt="冬 · Winter" width="56" height="28" align="absmiddle">&nbsp; 静默器物
</h3>

离线运行于本地桌面的视觉处理与屏幕辅助程序，不依赖外部云端服务，定型后即作为常备工具留存。

<p>
  <strong><a href="https://github.com/Cec1c/Aletheia-Lens">Aletheia-Lens</a></strong> &nbsp;<code>★ 120</code> &nbsp;<samp>Python · ONNX Runtime (CPU / CUDA 12)</samp><br>
  Windows 本地动漫插画与漫画批量修复 GUI，支持压缩包直读、自动遮罩检测与去网点。
</p>

<p>
  <strong><a href="https://github.com/Cec1c/MortarHUD">MortarHUD</a></strong> &nbsp;<code>★ 34</code> &nbsp;<samp>C# / WPF · .NET 10</samp><br>
  《Wardogs》透明置顶迫击炮外置 HUD，经 OpenCV 与 Tesseract 读屏识别地图绝对坐标，实时解算方位角与距离。
</p>

<h3>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/chapter-knock-dark.svg">
    <img src="./assets/chapter-knock-light.svg" alt="Chapter II · Knock" width="840" height="38">
  </picture><br>
  <img src="./assets/aspects/badge-knock.svg" alt="启 · Knock" width="56" height="28" align="absmiddle">&nbsp; 门径与接口
</h3>

衔接封包档案、AI 命令行界面与外部工程的协议层与扩展管理器，以及提交至上游开源仓库的补丁记录。

<p>
  <strong><a href="https://github.com/Cec1c/PVF-MCP">PVF-MCP</a></strong> &nbsp;<code>★ 19</code> &nbsp;<samp>Go · stdio MCP</samp><br>
  面向 pvfUtility 的 MCP 服务端，提供 26 个工具完成 PVF 检索、结构化编辑、序列化保存与当前文档读取。
</p>

<p>
  <strong><a href="https://github.com/Cec1c/codex-cli-ultra">codex-cli-ultra</a></strong> &nbsp;<code>★ 13</code> &nbsp;<samp>JS / Rust</samp><br>
  Codex CLI 跨平台安装与扩展管理器，支持外置 Fluent FTL 中文语言包、终端主题与状态栏扩展。
</p>

###### 上游开源补丁 · UPSTREAM PATCHES

- **[Kuddev/pebrel](https://github.com/Kuddev/pebrel)** &nbsp;`★ 3.7k` &nbsp;—&nbsp; 平滑光标轨迹契约与外观配置持久化（[#307](https://github.com/Kuddev/pebrel/pull/307) · [#293](https://github.com/Kuddev/pebrel/pull/293)）
- **[seakee/CPA-Manager-Plus](https://github.com/seakee/CPA-Manager-Plus)** &nbsp;`★ 4.0k` &nbsp;—&nbsp; 修复插件资源代理的未授权管理密钥提权问题（[#463](https://github.com/seakee/CPA-Manager-Plus/pull/463)）
- **[taekchef/claude-code-zh-cn](https://github.com/taekchef/claude-code-zh-cn)** &nbsp;`★ 848` &nbsp;—&nbsp; Windows PowerShell 安装器、Hook / Launcher 与界面翻译（[#11](https://github.com/taekchef/claude-code-zh-cn/pull/11)）

<h3>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/chapter-lantern-dark.svg">
    <img src="./assets/chapter-lantern-light.svg" alt="Chapter III · Lantern" width="840" height="38">
  </picture><br>
  <img src="./assets/aspects/badge-lantern.svg" alt="灯 · Lantern" width="56" height="28" align="absmiddle">&nbsp; 旧日长明
</h3>

围绕复古横版动作游戏持续维护的开源服务端与分发管理栈，以及依托这套设施长线运转的非营利公益服。

<p>
  <strong><a href="https://github.com/Cec1c/ServerS5A3">ServerS5A3</a></strong> &nbsp;<code>★ 84</code> &nbsp;<samp>Go · Linux / Docker</samp><br>
  复古横版动作游戏的 Go Linux 服务端与存档核心，支持容器化部署、120 频道表校验与活动开关配置。
</p>

<p>
  <strong><a href="https://github.com/Cec1c/PurpleMagic">PurpleMagic</a></strong> &nbsp;<code>★ 43</code> &nbsp;<samp>Go / Flutter / React</samp><br>
  配套 ServerS5A3 的玩家登录器、更新分发网关与 Web GM 管理端，覆盖账号、物品邮件、活动与持久福利。
</p>

> **长线公益服记录** &nbsp;·&nbsp; 基于上述开源栈维护着一处非营利社区服；日常运行说明与支持渠道设于爱发电 **[Cecic](https://ifdian.net/a/Cecic)**，联机交流可通过 **QQ 群 [908172336](https://qm.qq.com/cgi-bin/qm/qr?group_code=908172336)** 接入。

<p>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/colophon-dark.svg">
    <img src="./assets/colophon-light.svg" alt="Colophon · Dusk Terminal" width="840" height="42">
  </picture><br>
  <img src="./assets/terminal-hero.svg" alt="cec1c — What seekest thou this day? 今日所求何物？" width="840" height="142">
</p>

<p align="right">
  <sub>个人博客 <a href="https://mansus.cc">mansus.cc</a> &nbsp;·&nbsp; <a href="./README.en.md">English Edition</a></sub>
</p>
