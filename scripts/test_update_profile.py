import unittest
from datetime import datetime, timezone
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
