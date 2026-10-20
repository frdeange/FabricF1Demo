from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

AUDIENCE = "api://AzureADTokenExchange"
FABRIC = "https://api.fabric.microsoft.com"
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 1024 * 1024


class PilotError(Exception):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PilotError("HTTP redirect refused.")


def request_json(request: Request) -> dict:
    with build_opener(NoRedirects()).open(request, timeout=TIMEOUT_SECONDS) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise PilotError("Response exceeded size limit.")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise PilotError("Expected a JSON object.")
    return result


def uuid_value(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "")
    try:
        parsed = str(UUID(value))
    except (ValueError, AttributeError):
        raise PilotError(f"Missing or invalid {name}.") from None
    if value.lower() != parsed:
        raise PilotError(f"Missing or invalid {name}.")
    return parsed


def oidc_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        valid = (
            parts.scheme == "https"
            and (parts.hostname or "").endswith(".actions.githubusercontent.com")
            and parts.username is None
            and parts.password is None
            and parts.port in (None, 443)
            and not parts.fragment
            and bool(parts.path)
        )
    except ValueError:
        valid = False
    if not valid:
        raise PilotError("Invalid GitHub OIDC request URL.")
    query = [(key, val) for key, val in parse_qsl(parts.query) if key != "audience"]
    query.append(("audience", AUDIENCE))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def token_value(response: dict, field: str) -> str:
    value = response.get(field)
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        raise PilotError("Missing or invalid token in response.")
    return value


def verify(env: Mapping[str, str], transport=request_json) -> None:
    client = uuid_value(env, "AZURE_CLIENT_ID")
    tenant = uuid_value(env, "AZURE_TENANT_ID")
    workspace = uuid_value(env, "FABRIC_WORKSPACE_ID")
    url = oidc_url(env.get("ACTIONS_ID_TOKEN_REQUEST_URL", ""))
    runner_token = env.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
    if not runner_token or any(char.isspace() for char in runner_token):
        raise PilotError("Missing or invalid GitHub runner OIDC authorization.")
    stage = "GitHub OIDC"
    try:
        assertion = token_value(
            transport(Request(url, headers={"Authorization": f"Bearer {runner_token}"})),
            "value",
        )
        stage = "Entra token exchange"
        payload = urlencode(
            {
                "client_id": client,
                "scope": f"{FABRIC}/.default",
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": assertion,
            }
        ).encode("ascii")
        access = token_value(
            transport(
                Request(
                    f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
            ),
            "access_token",
        )
        stage = "Fabric DEV read"
        result = transport(
            Request(
                f"{FABRIC}/v1/workspaces/{workspace}",
                headers={"Authorization": f"Bearer {access}"},
            )
        )
        if result.get("id") != workspace or result.get("displayName") != "f1-dev":
            raise PilotError("Target workspace readback did not match f1-dev.")
    except HTTPError as exc:
        raise PilotError(f"{stage} failed (HTTP {exc.code}).") from None
    except (URLError, TimeoutError, OSError):
        raise PilotError(f"{stage} failed (network error).") from None
    except (ValueError, UnicodeError):
        raise PilotError(f"{stage} returned invalid JSON.") from None


def main(env: Mapping[str, str] | None = None, transport=request_json) -> int:
    env = os.environ if env is None else env
    try:
        verify(env, transport)
    except PilotError as exc:
        # Only fixed, locally constructed messages may reach public runner logs.
        print(f"DEV identity verification failed: {exc}", file=sys.stderr)
        return 1
    message = (
        "PASS: GitHub OIDC exchange and read-only f1-dev workspace access verified. "
        "No deployment, data access, or resource mutation performed."
    )
    print(message)
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as output:
                output.write(f"## DEV identity pilot\n\n{message}\n")
                sha = env.get("GITHUB_SHA", "")
                if re.fullmatch(r"[0-9a-f]{40}", sha):
                    output.write(f"\nRevision: `{sha}`\n")
        except OSError:
            print("Failed to write GitHub step summary.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
