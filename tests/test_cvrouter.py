"""Tests for the fakevine ComicVine router."""
# ruff: noqa: S101, D103, ANN201, PLR2004, SLF001
import json

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from mockito import mock, when

from fakevine.cvrouter import CVRouter
from fakevine.models import cvapimodels as m
from fakevine.trunks.comic_trunk import (
    AuthenticationError,
    ComicTrunk,
    GatewayError,
    RateLimitError,
    RequestLimitError,
    UnsupportedResponseError,
)


def _json_from_response(resp):  # noqa: ANN001, ANN202
    # FastAPI/Starlette Response stores the rendered body in .body
    if hasattr(resp, "body") and resp.body is not None:
        try:
            return json.loads(resp.body.decode())
        except Exception:  # noqa: BLE001
            return resp.body.decode()
    return None


def test_fetch_response_trunk_returns_model():
    trunk = mock(ComicTrunk)
    when(trunk).volumes(...).thenReturn(m.CVResponse())

    router = CVRouter(trunk=trunk)

    res = router._fetch_response(params=m.FilterParams(), trunk_method=trunk.volumes)
    assert isinstance(res, m.CVResponse)


def test_fetch_response_deadend_when_no_trunk_method():
    trunk = mock(ComicTrunk)
    router = CVRouter(trunk=trunk)
    dead = router._fetch_response(params=m.CommonParams(), trunk_method=None)
    assert dead.status_code == status.HTTP_200_OK
    assert _json_from_response(dead) == {"error": "OK", "limit": None, "offset": None, "number_of_page_results": 0,
                "number_of_total_results": 0, "status_code": 1, "results": [], "version": "1.0" }


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (RateLimitError, 429),
        (AuthenticationError, 401),
        (RequestLimitError, 420),
        (GatewayError, 502),
    ],
)
def test_exception_mapping_from_trunk(exc: Exception, expected_status: int):
    trunk = mock(ComicTrunk)
    when(trunk).volumes(...).thenRaise(exc)

    router = CVRouter(trunk=trunk)
    resp = router._fetch_response(params=m.FilterParams(), trunk_method=trunk.volumes)
    assert resp.status_code == expected_status


def test_unsupported_response_error_returns_501():
    trunk = mock(ComicTrunk)
    when(trunk).volumes(...).thenRaise(UnsupportedResponseError())

    router = CVRouter(trunk=trunk)
    resp = router._fetch_response(params=m.FilterParams(), trunk_method=trunk.volumes)
    assert resp.status_code == 501
    # body should contain a traceback string
    body = _json_from_response(resp)
    assert isinstance(body, str)
    assert "Traceback" in body


def minimal_base_volume_dict():
    return {
        "api_detail_url": "http://example.com/1",
        "count_of_issues": 5,
        "date_added": "2020-01-01",
        "date_last_updated": "2020-02-01",
        "description": "A volume",
        "first_issue": {
            "api_detail_url": "http://example.com/issue/1",
            "id": 1,
            "name": "Issue 1",
            "issue_number": "1",
        },
        "id": 42,
        "image": {"small_url": "http://img"},
        "last_issue": {
            "api_detail_url": "http://example.com/issue/5",
            "id": 5,
            "name": "Issue 5",
            "issue_number": "5",
        },
        "name": "Volume Name",
        "publisher": {
            "api_detail_url": "http://example.com/publisher/1",
            "id": 1,
            "name": "Pub",
        },
        "site_detail_url": "http://example.com/site/1",
        "start_year": "2000",
    }


@pytest.fixture
def client_and_trunk():
    trunk = mock(ComicTrunk)
    when(trunk).volumes(...).thenReturn(m.MultiResponse[m.BaseVolume](results=[]))
    when(trunk).volume(...).thenReturn(m.SingleResponse[m.DetailVolume](results=m.DetailVolume(**minimal_base_volume_dict())))
    when(trunk).search(...).thenReturn(m.CVResponse(results=[]))
    when(trunk).types(...).thenReturn(m.CVResponse(results=[{"detail_resource_name": "volume"}]))

    router = CVRouter(trunk=trunk)
    router.api_key = "secret"

    app = FastAPI()
    app.include_router(router.router)
    client = TestClient(app)

    return client, trunk


def test_undefined_route(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    response = client.get('/monkeyscanfly')
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_volumes_route_requires_api_key(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/volumes")
    assert r.status_code == CVRouter.INVALID_API_KEY.status_code


def test_volumes_route_with_api_key_returns_ok(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/volumes", params={"api_key": "secret"})
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_volume_detail_with_api_key(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/volume/4050-1234", params={"api_key": "secret"})
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d, dict)
    assert d.get("status_code") == 1


def test_types_endpoint_with_api_key(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    rt = client.get("/types", params={"api_key": "secret"})
    assert rt.status_code == 200
    assert isinstance(rt.json(), dict)


def test_search_without_query_returns_object_not_found_client(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    rs = client.get("/search", params={"api_key": "secret"})
    assert rs.status_code == status.HTTP_200_OK
    assert rs.json() == {
        "error": "Object Not Found",
        "limit": 0,
        "offset": 0,
        "number_of_page_results": 0,
        "number_of_total_results": 0,
        "status_code": 101,
        "results": [],
        }

def test_malformed_route_valid_root(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    rs = client.get("/volume/1234-1234", params={"api_key": "secret"})
    assert rs.status_code == status.HTTP_404_NOT_FOUND
    assert rs.json() == {
        "error": "Error in URL Format",
        "limit": 0,
        "offset": 0,
        "number_of_page_results": 0,
        "number_of_total_results": 0,
        "status_code": 102,
        "results": [],
        }

def test_malformed_route_invalid_root(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    rs = client.get("/voume/4050-1234", params={"api_key": "secret"})
    assert rs.status_code == status.HTTP_404_NOT_FOUND
    assert rs.json() == {
        "error": "Error in URL Format",
        "limit": 0,
        "offset": 0,
        "number_of_page_results": 0,
        "number_of_total_results": 0,
        "status_code": 102,
        "results": [],
        }


def test_search_with_query_calls_trunk_and_returns_ok(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    rs2 = client.get("/search", params={"api_key": "secret", "query": "bat"})
    assert rs2.status_code == 200


@pytest.mark.asyncio
async def test_get_search_without_query_returns_object_not_found():
    trunk = mock(ComicTrunk)
    router = CVRouter(trunk=trunk)

    resp = await router._get_search(params=m.SearchParams())
    assert resp.status_code == 200
    content = _json_from_response(resp)
    assert isinstance(content, dict)
    assert content == {
        "error": "Object Not Found",
        "limit": 0,
        "offset": 0,
        "number_of_page_results": 0,
        "number_of_total_results": 0,
        "status_code": 101,
        "results": [],
        }
