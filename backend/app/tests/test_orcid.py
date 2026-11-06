from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import User


def test_unconfigured_orcid(client):
    assert client.get("/auth/capabilities").json() == {"orcid": False}
    assert client.get("/auth/orcid/login").status_code == 503
    assert client.get("/auth/orcid/callback?code=abc&state=bad").status_code == 400


@pytest.mark.parametrize("bad", [False, True])
def test_orcid_flow_and_state_validation(client, monkeypatch, db, bad):
    settings = get_settings()
    monkeypatch.setattr(settings, "orcid_client_id", "test-client")
    monkeypatch.setattr(settings, "orcid_client_secret", "test-secret")
    response = client.get("/auth/orcid/login", follow_redirects=False)
    assert response.status_code == 307
    url = urlparse(response.headers["location"])
    assert url.netloc == "sandbox.orcid.org"
    state = parse_qs(url.query)["state"][0]
    assert (
        client.get("/auth/orcid/callback", params={"state": "wrong", "code": "code"}).status_code
        == 400
    )

    class Provider:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            assert kwargs["data"]["redirect_uri"] == settings.orcid_redirect_uri
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "orcid": "invalid" if bad else "0000-0002-1825-0097",
                    "name": "ORCID Researcher",
                },
            )

    monkeypatch.setattr("app.api.routes.auth.httpx.Client", Provider)
    result = client.get(
        "/auth/orcid/callback", params={"code": "code", "state": state}, follow_redirects=False
    )
    if bad:
        assert result.status_code == 502
        assert not db.scalar(select(User))
    else:
        assert result.status_code == 303
        assert client.get("/me").json()["orcid_id"] == "0000-0002-1825-0097"
        user = db.scalar(select(User))
        assert user.email is None and not user.email_verified
        assert user.role == "subscriber"
        # Callback cannot be replayed after its state cookie was removed.
        assert (
            client.get("/auth/orcid/callback", params={"code": "code", "state": state}).status_code
            == 400
        )
