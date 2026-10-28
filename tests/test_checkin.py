import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


def install_test_dependency_stubs():
    """Allow the isolated unit tests to run when optional runtime packages are absent."""
    if importlib.util.find_spec("requests") is None:
        requests = types.ModuleType("requests")

        class DummySession:
            def __init__(self):
                self.headers = {}

            def mount(self, *_args, **_kwargs):
                pass

            def close(self):
                pass

        class DummyAdapter:
            def __init__(self, *_args, **_kwargs):
                pass

        class DummyRetry:
            def __init__(self, *_args, **_kwargs):
                pass

        requests.Session = DummySession
        requests.Response = object
        requests.exceptions = types.SimpleNamespace(RequestException=Exception)
        sys.modules["requests"] = requests

        adapters = types.ModuleType("requests.adapters")
        adapters.HTTPAdapter = DummyAdapter
        sys.modules["requests.adapters"] = adapters

        urllib3 = types.ModuleType("urllib3")
        urllib3_util = types.ModuleType("urllib3.util")
        urllib3_retry = types.ModuleType("urllib3.util.retry")
        urllib3_retry.Retry = DummyRetry
        sys.modules["urllib3"] = urllib3
        sys.modules["urllib3.util"] = urllib3_util
        sys.modules["urllib3.util.retry"] = urllib3_retry

    if importlib.util.find_spec("pypushdeer") is None:
        pypushdeer = types.ModuleType("pypushdeer")
        pypushdeer.PushDeer = object
        sys.modules["pypushdeer"] = pypushdeer


install_test_dependency_stubs()

from checkin import API, CheckinResult, CheckinStatus, Checker, Config, PLATFORM_UA, main  # noqa: E402


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


class CheckinTests(unittest.TestCase):
    def test_glados_network_domain_remains_enabled(self):
        self.assertIn("glados.network", Config.DOMAINS)

    def make_api(self, bodies):
        api = object.__new__(API)
        api.domain = "glados.cloud"
        api.cookie_index = 1
        api.verbose = False
        api.headers = {"user-agent": PLATFORM_UA["Windows"]}
        api._device_ua_cache = {}

        attempts = []
        responses = iter(bodies)

        def fake_make_request(_url, _method, _data=None, _cookies="", user_agent=None):
            attempts.append(user_agent)
            return FakeResponse(next(responses))

        api._make_request = fake_make_request
        return api, attempts

    def test_device_mismatch_retries_using_login_device_platform(self):
        api, attempts = self.make_api(
            [
                {"code": 4, "reason": "device-mismatch", "loginDevice": "Android"},
                {"code": 0, "points": 2, "message": "ok"},
            ]
        )

        result = api.checkin("test-cookie")

        self.assertEqual(result["code"], CheckinStatus.SUCCESS)
        self.assertEqual(result["status"], "签到成功")
        self.assertEqual(attempts, [PLATFORM_UA["Windows"], PLATFORM_UA["Android"]])

    def test_repeat_checkin_is_a_valid_account_result(self):
        api, attempts = self.make_api([{"code": 1, "message": "already checked in"}])

        result = api.checkin("test-cookie")

        self.assertEqual(result["code"], CheckinStatus.REPEAT)
        self.assertEqual(len(attempts), 1)

    def test_no_exchange_plan_does_not_attempt_a_points_exchange(self):
        for exchange_plan in (None, "not-a-plan"):
            with self.subTest(exchange_plan=exchange_plan):
                environment = {"GLADOS_COOKIES": "test-cookie"}
                if exchange_plan is not None:
                    environment["GLADOS_EXCHANGE_PLAN"] = exchange_plan
                with patch.dict("os.environ", environment, clear=True):
                    config = Config()

                api = MagicMock()
                api.get_status.return_value = ("10 天", 0)
                api.checkin.return_value = {
                    "status": "签到成功",
                    "points": "2",
                    "message": "ok",
                    "code": CheckinStatus.SUCCESS,
                }
                api.get_points.return_value = ("12 积分", 12)
                api_context = MagicMock()
                api_context.__enter__.return_value = api

                with patch("checkin.API", return_value=api_context):
                    result = Checker(config)._checkin_on_domain("test-cookie", 1, "glados.network")

                self.assertEqual(result.exchange, "未配置兑换计划，跳过自动兑换")
                api.exchange.assert_not_called()

    def test_workflow_passes_four_cookie_secrets_to_the_script(self):
        workflow_path = Path(__file__).parents[1] / ".github" / "workflows" / "gladosCheck.yml"
        cookie_env_line = next(
            line for line in workflow_path.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("GLADOS_COOKIES:")
        )
        for secret_name in (
            "GLADOS_COOKIES",
            "GLADOS_COOKIES_2",
            "GLADOS_COOKIES_3",
            "GLADOS_COOKIES_4",
        ):
            with self.subTest(secret_name=secret_name):
                self.assertIn(f"${{{{ secrets.{secret_name} }}}}", cookie_env_line)

        with patch.dict(
            "os.environ",
            {"GLADOS_COOKIES": "cookie-1&cookie-2&cookie-3&cookie-4"},
            clear=True,
        ):
            config = Config()

        self.assertEqual(
            config.cookies_list,
            ["cookie-1", "cookie-2", "cookie-3", "cookie-4"],
        )

    def test_only_accounts_failing_on_every_domain_are_reported(self):
        checker = object.__new__(Checker)
        checker.config = types.SimpleNamespace(cookies_list=["cookie-1", "cookie-2"])
        checker.results = [
            CheckinResult(1, "glados.network", code=CheckinStatus.SUCCESS),
            CheckinResult(1, "glados.cloud", code=CheckinStatus.FAILURE),
            CheckinResult(2, "glados.network", code=CheckinStatus.FAILURE),
            CheckinResult(2, "glados.cloud", code=CheckinStatus.FAILURE),
        ]

        self.assertEqual(checker.cookies_without_successful_checkin(), [2])

    def test_main_marks_all_domain_failures_as_an_actions_failure(self):
        config = types.SimpleNamespace(cookies_list=["test-cookie"])
        checker = MagicMock()
        checker.format_results.return_value = {"title": "summary", "rows": []}
        checker.cookies_without_successful_checkin.return_value = [1]

        with (
            patch("checkin.Config", return_value=config),
            patch("checkin.Checker", return_value=checker),
            patch("checkin.PushService.send", return_value=True),
        ):
            with self.assertRaises(SystemExit) as error:
                main()

        self.assertEqual(error.exception.code, 1)
        checker.cookies_without_successful_checkin.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
