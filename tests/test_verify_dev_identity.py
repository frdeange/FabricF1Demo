from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from scripts.verify_dev_identity import NoRedirects, PilotError, main, oidc_url, request_json

CLIENT = "11111111-1111-4111-8111-111111111111"
TENANT = "22222222-2222-4222-8222-222222222222"
WORKSPACE = "33333333-3333-4333-8333-333333333333"


def config():
    return {
        "AZURE_CLIENT_ID": CLIENT,
        "AZURE_TENANT_ID": TENANT,
        "FABRIC_WORKSPACE_ID": WORKSPACE,
        "ACTIONS_ID_TOKEN_REQUEST_URL": (
            "https://pipelines.actions.githubusercontent.com/test/idtoken?api-version=2"
        ),
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "runner-sensitive",
    }


class IdentityPilotTests(unittest.TestCase):
    def run_pilot(self, env=None, results=None):
        requests = []
        responses = iter(results if results is not None else [
            {"value": "assertion-sensitive"},
            {"access_token": "access-sensitive"},
            {"id": WORKSPACE, "displayName": "f1-dev"},
        ])

        def transport(request):
            requests.append(request)
            response = next(responses)
            if isinstance(response, Exception):
                raise response
            return response

        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(config() if env is None else env, transport)
        logs = stdout.getvalue() + stderr.getvalue()
        for sensitive in ("runner-sensitive", "assertion-sensitive", "access-sensitive"):
            self.assertNotIn(sensitive, logs)
        return code, logs, requests

    def test_success_uses_only_oidc_exchange_and_dev_get(self):
        code, logs, requests = self.run_pilot()
        self.assertEqual(0, code)
        self.assertIn("PASS", logs)
        self.assertEqual(["GET", "POST", "GET"], [r.get_method() for r in requests])
        self.assertEqual("Bearer runner-sensitive", requests[0].get_header("Authorization"))
        self.assertEqual(
            ["api://AzureADTokenExchange"],
            parse_qs(urlsplit(requests[0].full_url).query)["audience"],
        )
        self.assertEqual(
            f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token",
            requests[1].full_url,
        )
        self.assertEqual({
            "client_id": [CLIENT],
            "scope": ["https://api.fabric.microsoft.com/.default"],
            "grant_type": ["client_credentials"],
            "client_assertion_type": ["urn:ietf:params:oauth:client-assertion-type:jwt-bearer"],
            "client_assertion": ["assertion-sensitive"],
        }, parse_qs(requests[1].data.decode()))
        self.assertEqual(
            f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE}",
            requests[2].full_url,
        )
        self.assertEqual("Bearer access-sensitive", requests[2].get_header("Authorization"))

    def test_invalid_or_missing_configuration_never_calls_network(self):
        for key in config():
            env = config()
            del env[key]
            with self.subTest(key=key):
                code, _, requests = self.run_pilot(env)
                self.assertEqual(1, code)
                self.assertFalse(requests)
        for key in ("AZURE_CLIENT_ID", "AZURE_TENANT_ID", "FABRIC_WORKSPACE_ID"):
            env = config()
            env[key] = "../sensitive"
            code, _, requests = self.run_pilot(env)
            self.assertEqual(1, code)
            self.assertFalse(requests)

    def test_oidc_url_rejects_untrusted_destinations(self):
        for url in (
            "http://pipelines.actions.githubusercontent.com/test",
            "https://actions.githubusercontent.com.evil.test/test",
            "https://evil.test/test",
            "https://user@pipelines.actions.githubusercontent.com/test",
            "https://pipelines.actions.githubusercontent.com:8443/test",
            "https://pipelines.actions.githubusercontent.com/test#fragment",
            "https://pipelines.actions.githubusercontent.com:bad/test",
        ):
            with self.subTest(url=url), self.assertRaises(PilotError):
                oidc_url(url)

    def test_audience_is_replaced_and_existing_query_preserved(self):
        url = oidc_url(config()["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=wrong")
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(["api://AzureADTokenExchange"], query["audience"])
        self.assertEqual(["2"], query["api-version"])

    def test_stage_failures_are_sanitized(self):
        for index, stage in enumerate(("GitHub OIDC", "Entra token exchange", "Fabric DEV read")):
            prefix = [{"value": "assertion-sensitive"}, {"access_token": "access-sensitive"}][:index]
            for error in (
                HTTPError("https://sensitive", 403, "access-sensitive", {}, None),
                URLError("access-sensitive"),
                ValueError("assertion-sensitive"),
                TimeoutError("runner-sensitive"),
            ):
                with self.subTest(stage=stage, error=type(error).__name__):
                    code, logs, requests = self.run_pilot(results=prefix + [error])
                    self.assertEqual(1, code)
                    self.assertIn(stage, logs)
                    self.assertEqual(index + 1, len(requests))

    def test_malformed_tokens_and_workspace_mismatches_fail(self):
        for results in (
            [{}], [{"value": 42}], [{"value": "bad\nvalue"}],
            [{"value": "assertion-sensitive"}, {}],
            [{"value": "assertion-sensitive"}, {"access_token": "access-sensitive"}, {}],
            [{"value": "assertion-sensitive"}, {"access_token": "access-sensitive"},
             {"id": WORKSPACE, "displayName": "f1-pro"}],
            [{"value": "assertion-sensitive"}, {"access_token": "access-sensitive"},
             {"id": CLIENT, "displayName": "f1-dev"}],
        ):
            with self.subTest(results=results):
                self.assertEqual(1, self.run_pilot(results=results)[0])

    def test_redirects_are_refused(self):
        with self.assertRaises(PilotError):
            NoRedirects().redirect_request(None, None, 302, "", {}, "https://evil.test")

    def test_transport_installs_redirect_guard_and_timeout(self):
        from urllib.request import Request
        with patch("scripts.verify_dev_identity.build_opener") as opener:
            response = opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value = b'{"value":"ok"}'
            result = request_json(Request("https://example.test"))
            self.assertEqual({"value": "ok"}, result)
            self.assertIsInstance(opener.call_args.args[0], NoRedirects)
            self.assertEqual(30, opener.return_value.open.call_args.kwargs["timeout"])
            for raw in (b"[]", b"null", b"invalid", b"x" * (1024 * 1024 + 1)):
                response.read.return_value = raw
                with self.assertRaises((PilotError, ValueError)):
                    request_json(Request("https://example.test"))

    def test_summary_contains_no_credentials_or_target_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            env = config()
            summary = Path(directory) / "summary.md"
            env["GITHUB_STEP_SUMMARY"] = str(summary)
            env["GITHUB_SHA"] = "a" * 40
            self.assertEqual(0, self.run_pilot(env)[0])
            text = summary.read_text()
            self.assertIn("a" * 40, text)
            for value in (CLIENT, TENANT, WORKSPACE, "assertion-sensitive", "access-sensitive"):
                self.assertNotIn(value, text)
            summary.unlink()
            self.assertEqual(1, self.run_pilot(env, [{}])[0])
            self.assertFalse(summary.exists())


if __name__ == "__main__":
    unittest.main()
