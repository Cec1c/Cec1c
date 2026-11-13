import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import profile_render as render
import update_profile as profile


class NewRepositoryTests(unittest.TestCase):
    def test_eligible_repository_uses_explicit_identity_and_token(self):
        repo = {"full_name": "Example/new-project", "created_at": "2020-01-01T00:00:00Z"}
        with patch.object(profile, "rest", return_value=[]) as request:
            result = profile.detect_new_repos({}, {}, [repo], "Example", "test-token")
        self.assertEqual(result, [repo])
        request.assert_called_once_with(
            "/repos/Example/Example/issues?state=all&labels=profile-updater&per_page=100",
            "test-token",
        )

    def test_previously_reported_repository_is_not_reported_again(self):
        repo = {"full_name": "Example/old-project", "created_at": "2020-01-01T00:00:00Z"}
        issue = {"body": profile.ISSUE_MARKER + "\n- `Example/old-project` — already reported"}
        with patch.object(profile, "rest", return_value=[issue]):
            self.assertEqual(
                profile.detect_new_repos({}, {}, [repo], "Example", "test-token"), []
            )

    def test_repository_within_grace_period_does_not_query_issues(self):
        repo = {
            "full_name": "Example/new-project",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with patch.object(profile, "rest") as request:
            self.assertEqual(
                profile.detect_new_repos({}, {}, [repo], "Example", "test-token"), []
            )
        request.assert_not_called()


class BentoRenderTests(unittest.TestCase):
    def test_featured_bento_generates_dual_theme_svgs_and_picture_links(self):
        cfg = {
            "featured": [
                {
                    "repo": "Cec1c/MortarHUD",
                    "slug": "mortarhud",
                    "title_zh": "MortarHUD",
                    "title_en": "MortarHUD",
                    "aspect": "winter",
                    "desc_zh": "《Wardogs》透明置顶迫击炮 HUD，实时解算地图方位角与距离。",
                    "desc_en": "Transparent Wardogs mortar HUD solving azimuth & range.",
                    "badge": "release",
                    "tag3": "OpenCV · Tesseract",
                },
                {
                    "repo": "Cec1c/ServerS5A3",
                    "slug": "servers5a3",
                    "title_zh": "ServerS5A3",
                    "title_en": "ServerS5A3",
                    "aspect": "knock",
                    "desc_zh": "复古横版动作游戏 Go Linux 服务端。",
                    "desc_en": "Go Linux server core.",
                    "badge": "static",
                    "tag2": "Linux · Docker",
                },
            ]
        }
        data = {
            "Cec1c/MortarHUD": {
                "stars": 34,
                "tag": "v1.1.0",
                "languages": [{"name": "C#", "color": "#178600", "size": 1000}],
            },
            "Cec1c/ServerS5A3": {
                "stars": 84,
                "tag": "client-v212-long-tag",
                "languages": [{"name": "Go", "color": "#00ADD8", "size": 2000}],
            },
        }
        md_zh, md_en, svgs = render.render_featured_bento(cfg, data)
        self.assertIn("work-mortarhud-dark.svg", svgs)
        self.assertIn("work-mortarhud-en-light.svg", svgs)
        self.assertIn("I — II", svgs["section-works-dark.svg"])
        self.assertIn("★ 34", svgs["work-mortarhud-dark.svg"])
        self.assertIn("v1.1.0", svgs["work-mortarhud-dark.svg"])
        self.assertIn("Linux · Docker", svgs["work-servers5a3-dark.svg"])
        self.assertNotIn("client-v212-long-tag", svgs["work-servers5a3-dark.svg"])
        self.assertIn("./assets/work-mortarhud-dark.svg", md_zh)
        self.assertIn("./assets/work-mortarhud-en-dark.svg", md_en)

    def test_contrib_bento_renders_upstream_tiles_and_pr_ledger(self):
        entries = [
            {
                "repo": "Kuddev/pebrel",
                "slug": "pebrel",
                "takeaway_zh": "平滑光标轨迹契约与外观配置持久化",
                "takeaway_en": "Smooth cursor trail contract & appearance persistence",
                "_data": {"stars": 3769, "total": 6},
                "_prs": [{"number": 307, "title": "feat"}, {"number": 293, "title": "fix"}],
            },
            {
                "repo": "seakee/CPA-Manager-Plus",
                "slug": "cpamp",
                "takeaway_zh": "修复未授权管理密钥提权",
                "takeaway_en": "Fix admin-key escalation",
                "_data": {"stars": 4073, "total": 1},
                "_prs": [{"number": 463, "title": "sec"}],
            },
            {
                "repo": "taekchef/claude-code-zh-cn",
                "slug": "cc-zh",
                "takeaway_zh": "Windows 安装器与翻译",
                "takeaway_en": "Windows installer & translation",
                "_data": {"stars": 848, "total": 1},
                "_prs": [{"number": 11, "title": "feat"}],
            },
        ]
        md_zh, md_en, svgs = render.render_contrib_bento(entries)
        self.assertIn("IV MERGED", svgs["section-upstream-dark.svg"])
        self.assertIn("★ 3.7k", svgs["upstream-pebrel-dark.svg"])
        self.assertIn("Merged #307 · #293", svgs["upstream-pebrel-dark.svg"])
        self.assertIn('href="https://github.com/Kuddev/pebrel/pull/293">#293</a>', md_zh)
        self.assertIn("./assets/upstream-cpamp-en-dark.svg", md_en)

    def test_replace_section_is_idempotent(self):
        doc = "head\n<!-- PROFILE:FEATURED:START -->\nold\n<!-- PROFILE:FEATURED:END -->\ntail\n"
        once, _ = profile.replace_section(doc, "PROFILE:FEATURED", "<p>new</p>")
        twice, _ = profile.replace_section(once, "PROFILE:FEATURED", "<p>new</p>")
        self.assertEqual(once, twice)

    def test_open_converts_read_timeout_to_fetch_error(self):
        req = profile.urllib.request.Request("https://api.github.com/rate_limit")
        with patch.object(profile.urllib.request, "urlopen", side_effect=TimeoutError("read timed out")), \
             patch.object(profile.time, "sleep"):
            with self.assertRaises(profile.FetchError):
                profile._open(req)


if __name__ == "__main__":
    unittest.main()
