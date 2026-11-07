"""Tests for PerfectDraftApiClient.authenticate() against Cognito.

Stdlib only, like ``test_keg_detection.py``: ``api.py`` is loaded as part of
a stub ``perfectdraft`` package so the integration's ``__init__.py`` (which
needs Home Assistant) never runs, and a fake session replays canned
responses instead of touching the network.
"""
import asyncio
import importlib
import json
import sys
import types
import unittest
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "perfectdraft"

try:
    import aiohttp
except ImportError:  # the client only needs aiohttp.ClientError at runtime
    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientError = type("ClientError", (Exception,), {})
    aiohttp.ClientSession = object
    sys.modules["aiohttp"] = aiohttp

_pkg = types.ModuleType("_perfectdraft_stub")
_pkg.__path__ = [str(PKG_DIR)]
sys.modules["_perfectdraft_stub"] = _pkg

api = importlib.import_module("_perfectdraft_stub.api")
exceptions = importlib.import_module("_perfectdraft_stub.exceptions")

EMAIL = "drinker@example.com"
PASSWORD = "hunter2"
TOKEN = "recaptcha-token"
TOKENS = {"AccessToken": "access-jwt-1", "IdToken": "id-jwt-1", "RefreshToken": "refresh-jwt-1"}


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body if isinstance(body, str) else json.dumps(body)

    async def text(self):
        return self._body

    async def json(self, content_type="application/json"):
        if content_type is not None:
            raise AssertionError("Cognito replies x-amz-json; parse with content_type=None")
        return json.loads(self._body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, status=200, body=None, raises=None):
        self._response = FakeResponse(status, body if body is not None else {})
        self._raises = raises
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._raises:
            raise self._raises
        return self._response


def sign_in(session):
    client = api.PerfectDraftApiClient(session)
    result = asyncio.run(client.authenticate(EMAIL, PASSWORD, TOKEN))
    return client, result


def rejection(session):
    client = api.PerfectDraftApiClient(session)
    client.set_tokens("old-access", "old-id", "old-refresh")
    with unittest.TestCase().assertRaises(exceptions.AuthenticationError) as ctx:
        asyncio.run(client.authenticate(EMAIL, PASSWORD, TOKEN))
    return client, ctx.exception


class SuccessfulSignIn(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession(200, {"AuthenticationResult": {**TOKENS, "ExpiresIn": 3600}})
        self.client, self.result = sign_in(self.session)
        self.url, self.kwargs = self.session.calls[0]

    def test_posts_to_cognito_not_the_gateway(self):
        self.assertEqual(self.url, "https://cognito-idp.eu-west-1.amazonaws.com/")
        self.assertEqual(
            self.kwargs["headers"],
            {
                "Content-Type": "application/x-amz-json-1.1",
                "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
            },
        )

    def test_payload_carries_credentials_and_recaptcha_metadata(self):
        self.assertEqual(
            self.kwargs["json"],
            {
                "AuthFlow": "USER_PASSWORD_AUTH",
                "ClientId": "57ddq2ppqg2jcpup06r2g1deur",
                "AuthParameters": {"USERNAME": EMAIL, "PASSWORD": PASSWORD},
                "ClientMetadata": {
                    "recaptchaToken": TOKEN,
                    "recaptchaAction": "Magento/login",
                    "domain": "https://www.perfectdraft.com",
                },
            },
        )

    def test_stores_tokens_from_authentication_result(self):
        self.assertEqual(self.client.access_token, "access-jwt-1")
        self.assertEqual(self.client.id_token, "id-jwt-1")
        self.assertEqual(self.client.refresh_token, "refresh-jwt-1")
        self.assertEqual(self.result["AccessToken"], "access-jwt-1")


class Challenge(unittest.TestCase):
    def test_challenge_raises_and_keeps_tokens(self):
        client, err = rejection(FakeSession(200, {"ChallengeName": "NEW_PASSWORD_REQUIRED", "Session": "s"}))
        self.assertEqual(err.code, "NEW_PASSWORD_REQUIRED")
        self.assertEqual(err.kind, "other")
        self.assertIn("NEW_PASSWORD_REQUIRED", err.display_reason)
        self.assertEqual(client.access_token, "old-access")
        self.assertEqual(client.refresh_token, "old-refresh")

    def test_incomplete_result_raises(self):
        _, err = rejection(FakeSession(200, {"AuthenticationResult": {"AccessToken": "a"}}))
        self.assertIsNone(err.code)
        self.assertEqual(err.display_reason, "no reason given")


class Rejections(unittest.TestCase):
    def test_wrong_password_is_a_credentials_failure(self):
        _, err = rejection(FakeSession(400, {"__type": "NotAuthorizedException", "message": "Incorrect username or password."}))
        self.assertEqual(err.code, "NotAuthorizedException")
        self.assertEqual(err.kind, "credentials")
        self.assertEqual(err.display_reason, "Incorrect username or password")
        self.assertIn("400", str(err))

    def test_unknown_user_is_a_credentials_failure(self):
        _, err = rejection(FakeSession(400, {"__type": "UserNotFoundException", "message": "User does not exist."}))
        self.assertEqual(err.kind, "credentials")

    def test_lambda_rejection_is_a_token_failure(self):
        _, err = rejection(FakeSession(400, {
            "__type": "UserLambdaValidationException",
            "message": "PreAuthentication failed with error 'domain'.",
        }))
        self.assertEqual(err.kind, "token")
        self.assertEqual(err.display_reason, "PreAuthentication failed with error 'domain'")

    def test_namespaced_type_is_stripped(self):
        _, err = rejection(FakeSession(400, {
            "__type": "com.amazonaws.cognito.identity.idp.model#NotAuthorizedException",
            "message": "x",
        }))
        self.assertEqual(err.code, "NotAuthorizedException")

    def test_other_type_is_an_other_failure(self):
        for status in (401, 403):
            _, err = rejection(FakeSession(status, {"__type": "InvalidParameterException", "message": "USER_PASSWORD_AUTH flow not enabled"}))
            self.assertEqual(err.kind, "other")
            self.assertEqual(err.display_reason, "USER_PASSWORD_AUTH flow not enabled")

    def test_non_json_body_becomes_truncated_reason(self):
        _, err = rejection(FakeSession(403, "<html>" + "x" * 500 + "</html>"))
        self.assertIsNone(err.code)
        self.assertEqual(err.kind, "other")
        self.assertLessEqual(len(err.reason), 200)
        self.assertTrue(err.reason.startswith("<html>"))

    def test_empty_body_has_fallback_reason(self):
        _, err = rejection(FakeSession(400, ""))
        self.assertEqual(err.display_reason, "no reason given")

    def test_rejection_keeps_existing_tokens(self):
        client, _ = rejection(FakeSession(400, {"__type": "NotAuthorizedException", "message": "x"}))
        self.assertEqual(client.access_token, "old-access")


class OtherFailures(unittest.TestCase):
    def test_server_error_is_an_api_error(self):
        client = api.PerfectDraftApiClient(FakeSession(500, "boom"))
        with self.assertRaises(exceptions.PerfectDraftApiError) as ctx:
            asyncio.run(client.authenticate(EMAIL, PASSWORD, TOKEN))
        self.assertEqual(ctx.exception.status, 500)

    def test_network_failure_is_a_connection_error(self):
        client = api.PerfectDraftApiClient(FakeSession(raises=aiohttp.ClientError("down")))
        with self.assertRaises(exceptions.PerfectDraftConnectionError):
            asyncio.run(client.authenticate(EMAIL, PASSWORD, TOKEN))


class SecretsAreNotLogged(unittest.TestCase):
    def test_no_secret_reaches_the_log(self):
        cases = [
            FakeSession(200, {"AuthenticationResult": TOKENS}),
            FakeSession(400, {"__type": "NotAuthorizedException", "message": "Incorrect username or password."}),
        ]
        for session in cases:
            with self.assertLogs(api._LOGGER, level="DEBUG") as logs:
                api._LOGGER.debug("marker")
                client = api.PerfectDraftApiClient(session)
                try:
                    asyncio.run(client.authenticate(EMAIL, PASSWORD, TOKEN))
                except exceptions.AuthenticationError:
                    pass
            text = "\n".join(logs.output)
            for secret in (PASSWORD, TOKEN, *TOKENS.values()):
                self.assertNotIn(secret, text)


class LegacyRaises(unittest.TestCase):
    def test_single_argument_raise_still_works(self):
        err = exceptions.AuthenticationError("No refresh token available")
        self.assertIsNone(err.code)
        self.assertEqual(err.kind, "other")
        self.assertEqual(str(err), "No refresh token available")


if __name__ == "__main__":
    unittest.main()
