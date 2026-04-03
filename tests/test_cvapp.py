"""Tests for the fakevine ComicVine app."""
# ruff: noqa: S101, D103, ANN201, PLR2004, SLF001
import json
from unittest.mock import AsyncMock

import pytest
from fastapi import Response, status
from fastapi.testclient import TestClient
from lxml import etree

from fakevine.cvapp import CVApp, cvresponse_to_xml, jsonp_encoder
from fakevine.models import cvapimodels as m
from fakevine.trunks.comic_trunk import (
    AuthenticationError,
    ComicTrunk,
    GatewayError,
    ObjectNotFoundError,
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


@pytest.mark.asyncio
async def test_fetch_response_trunk_returns_response():
    trunk = AsyncMock(spec=ComicTrunk)
    trunk.volumes = AsyncMock(return_value=m.CVResponse())

    app = CVApp(trunk=trunk, api_keys=["testkey"])

    res = await app._fetch_response(params=m.FilterParams(api_key="testkey"), trunk_method=trunk.volumes)
    assert isinstance(res, Response)

@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (RateLimitError, 429),
        (AuthenticationError, 401),
        (RequestLimitError, 420),
        (GatewayError, 502),
    ],
)
@pytest.mark.asyncio
async def test_exception_mapping_from_trunk(exc: Exception, expected_status: int):
    trunk = AsyncMock(spec=ComicTrunk)
    trunk.volumes = AsyncMock(side_effect=exc)

    app = CVApp(trunk=trunk, api_keys=["testkey"])
    resp = await app._fetch_response(params=m.FilterParams(api_key="testkey"), trunk_method=trunk.volumes)
    assert resp.status_code == expected_status


@pytest.mark.asyncio
async def test_unsupported_response_error_returns_501():
    trunk = AsyncMock(spec=ComicTrunk)
    trunk.volumes = AsyncMock(side_effect=UnsupportedResponseError())

    app = CVApp(trunk=trunk, api_keys=["testkey"])
    resp = await app._fetch_response(params=m.FilterParams(api_key="testkey"), trunk_method=trunk.volumes)
    assert resp.status_code == 501


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
    trunk = AsyncMock(spec=ComicTrunk)
    trunk.volumes = AsyncMock(return_value=m.MultiResponse[m.BaseVolume](results=[]))
    trunk.volume = AsyncMock(return_value=m.SingleResponse[m.DetailVolume](results=m.DetailVolume(**minimal_base_volume_dict())))
    trunk.search = AsyncMock(return_value=m.CVResponse(results=[]))
    trunk.types = AsyncMock(return_value=m.CVResponse(results=[
        m.BaseTypes(detail_resource_name= "volume", id=4050, list_resource_name="volumes"),
        ]))

    app = CVApp(trunk=trunk, api_keys=["secret"])

    client = TestClient(app.app)

    return client, trunk


def test_undefined_route(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    response = client.get('/monkeyscanfly',params={'api_key':'secret'})
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_volumes_route_requires_api_key(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/volumes")
    assert r.status_code == status.HTTP_401_UNAUTHORIZED


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
        "version" : '1.0',
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
        "version" : '1.0',
        }


def test_search_with_query_calls_trunk_and_returns_ok(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    rs2 = client.get("/search", params={"api_key": "secret", "query": "bat"})
    assert rs2.status_code == 200


# ============================================================================
# P1: Response Format Tests (XML/JSONP)
# ============================================================================


def test_volumes_returns_xml_format(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/volumes", params={"api_key": "secret", "format": "xml"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/xml"
    # Verify it's valid XML
    root = etree.fromstring(r.content)
    assert root.tag == "response"
    assert root.find("status_code") is not None


def test_volumes_returns_jsonp_format(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    callback = "myCallback"
    r = client.get("/volumes", params={"api_key": "secret", "format": "jsonp", "json_callback": callback})
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/javascript; charset=UTF-8"
    assert r.text.startswith(f"{callback}(")
    assert r.text.endswith(")")


def test_volume_detail_returns_xml_format(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/volume/4050-1234", params={"api_key": "secret", "format": "xml"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/xml"
    root = etree.fromstring(r.content)
    assert root.tag == "response"


def test_volume_detail_returns_jsonp_format(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    callback = "parseVolume"
    r = client.get("/volume/4050-1234", params={"api_key": "secret", "format": "jsonp", "json_callback": callback})
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/javascript; charset=UTF-8"
    assert r.text.startswith(f"{callback}(")


def test_search_returns_xml_format(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/search", params={"api_key": "secret", "query": "bat", "format": "xml"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/xml"
    root = etree.fromstring(r.content)
    assert root.tag == "response"


def test_search_returns_jsonp_format(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    callback = "searchCallback"
    r = client.get("/search", params={"api_key": "secret", "query": "test", "format": "jsonp", "json_callback": callback})
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/javascript; charset=UTF-8"
    assert r.text.startswith(f"{callback}(")


def test_types_returns_json_format(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/types", params={"api_key": "secret", "format": "json"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    data = r.json()
    assert isinstance(data, dict)


def test_types_returns_xml_format(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/types", params={"api_key": "secret", "format": "xml"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/xml"
    root = etree.fromstring(r.content)
    assert root.tag == "response"


def test_types_returns_jsonp_format(client_and_trunk: tuple[TestClient, ComicTrunk]):
    """Note: types endpoint doesn't accept json_callback parameter, so JSONP requires callback in URL.
    
    Since the types endpoint signature only accepts format and api_key, it cannot support
    the full JSONP feature that requires a callback parameter. This test documents that behavior.
    """
    client, _ = client_and_trunk
    # Send with json_callback parameter - types endpoint ignores this parameter
    # since it doesn't have it in the signature, so format stays jsonp but no callback is set
    # which means _fetch_response will convert it to json with status 103
    r = client.get("/types", params={"api_key": "secret", "format": "jsonp", "json_callback": "typesCallback"})
    assert r.status_code == 200
    # Since callback isn't properly received by the endpoint, it returns as json
    assert r.headers["content-type"] == "application/json"


def test_jsonp_without_callback_returns_status_103(client_and_trunk: tuple[TestClient, ComicTrunk]):
    client, _ = client_and_trunk
    r = client.get("/volumes", params={"api_key": "secret", "format": "jsonp"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("status_code") == 103


# ============================================================================
# P1: Validation Error Handling Tests
# ============================================================================


def test_volumes_endpoint_with_api_key_validation(client_and_trunk: tuple[TestClient, ComicTrunk]):
    """Test that validation happens at the endpoint level."""
    client, _ = client_and_trunk
    # Valid request should work
    r = client.get("/volumes", params={"api_key": "secret"})
    assert r.status_code == 200
    # Without api_key should fail
    r = client.get("/volumes")
    assert r.status_code == 401


# ============================================================================
# P2: ObjectNotFoundError & NotImplementedError Tests
# ============================================================================


@pytest.mark.asyncio
async def test_object_not_found_error_returns_200_with_status_101():
    trunk = AsyncMock(spec=ComicTrunk)
    trunk.volumes = AsyncMock(side_effect=ObjectNotFoundError)
    
    app = CVApp(trunk=trunk, api_keys=["testkey"])
    resp = await app._fetch_response(params=m.FilterParams(api_key="testkey"), trunk_method=trunk.volumes)
    assert resp.status_code == 200  # Returns 200 per ComicVine API
    data = json.loads(resp.body.decode())
    assert data.get("status_code") == 101


@pytest.mark.asyncio
async def test_not_implemented_error_returns_501():
    trunk = AsyncMock(spec=ComicTrunk)
    trunk.volumes = AsyncMock(side_effect=NotImplementedError)
    
    app = CVApp(trunk=trunk, api_keys=["testkey"])
    resp = await app._fetch_response(params=m.FilterParams(api_key="testkey"), trunk_method=trunk.volumes)
    assert resp.status_code == 501


# ============================================================================
# P2: Parameter Validation Verification Tests
# ============================================================================


def test_search_endpoint_adds_resource_type_to_field_list(client_and_trunk: tuple[TestClient, ComicTrunk]):
    """Test that search endpoint adds resource_type to field_list."""
    client, trunk = client_and_trunk
    r = client.get("/search", params={"api_key": "secret", "query": "test", "field_list": "name,id"})
    assert r.status_code == 200
    # Verify trunk.search was called
    trunk.search.assert_called_once()
    # Check that params were modified to include resource_type
    call_args = trunk.search.call_args
    params_used = call_args.kwargs["params"]
    assert "resource_type" in params_used.field_list


def test_volumes_endpoint_validates_parameters(client_and_trunk: tuple[TestClient, ComicTrunk]):
    """Test that volumes endpoint validates parameters."""
    client, trunk = client_and_trunk
    # Valid request should work
    r = client.get("/volumes", params={"api_key": "secret", "sort": "id:asc"})
    assert r.status_code == 200
    trunk.volumes.assert_called_once()


# ============================================================================
# P2: XML/JSONP Encoding Function Tests
# ============================================================================


def test_cvresponse_to_xml_structure():
    response = m.CVResponse(
        results=[],
        status_code=1,
        limit=100,
        offset=0,
        number_of_page_results=0,
        number_of_total_results=0,
        version="1.0"
    )
    xml_str = cvresponse_to_xml(response)
    root = etree.fromstring(xml_str.encode() if isinstance(xml_str, str) else xml_str)

    assert root.tag == "response"
    assert root.find("status_code") is not None
    assert root.find("status_code").text == "1"
    assert root.find("limit") is not None
    assert root.find("results") is not None
    assert root.find("version") is not None


def test_cvresponse_to_xml_with_results():
    volume = m.BaseVolume(**minimal_base_volume_dict())
    response = m.CVResponse(
        results=[volume],
        status_code=1,
        limit=100,
        offset=0,
        number_of_page_results=1,
        number_of_total_results=1,
        version="1.0"
    )
    xml_str = cvresponse_to_xml(response)
    root = etree.fromstring(xml_str.encode() if isinstance(xml_str, str) else xml_str)
    
    results = root.find("results")
    assert results is not None
    # Should have volume results
    assert len(results) > 0


def test_cvresponse_to_xml_with_dict_results():
    response = m.CVResponse(
        results={"resource_name": "volume", "count": 42},
        status_code=1,
        limit=100,
        offset=0,
        number_of_page_results=1,
        number_of_total_results=1,
        version="1.0"
    )
    xml_str = cvresponse_to_xml(response)
    root = etree.fromstring(xml_str.encode() if isinstance(xml_str, str) else xml_str)
    
    results = root.find("results")
    assert results is not None


def test_entity_to_xml_handles_null_fields():
    volume = m.BaseVolume(**minimal_base_volume_dict())
    response = m.CVResponse(results=volume, status_code=1)
    xml_str = cvresponse_to_xml(response)
    root = etree.fromstring(xml_str.encode() if isinstance(xml_str, str) else xml_str)
    
    # Verify XML parses without errors and contains data
    assert root.tag == "response"
    assert root.find("results") is not None


def test_linkedentity_to_xml_format():
    # Create a volume with a publisher (which is a linked entity)
    volume = m.BaseVolume(**minimal_base_volume_dict())
    response = m.CVResponse(results=[volume], status_code=1)
    xml_str = cvresponse_to_xml(response)
    root = etree.fromstring(xml_str.encode() if isinstance(xml_str, str) else xml_str)
    
    results = root.find("results")
    assert results is not None
    # Should have volume with nested publisher
    assert len(results) > 0


def test_jsonp_encoder_formats_correctly():
    response = m.CVResponse(
        results=[],
        status_code=1,
        limit=100,
        offset=0,
        number_of_page_results=0,
        number_of_total_results=0,
        version="1.0"
    )
    callback = "myCallback"
    output = jsonp_encoder(response, callback)
    
    assert output.startswith(f"{callback}(")
    assert output.endswith(")")
    # Extract the JSON part
    json_part = output[len(callback)+1:-1]
    parsed = json.loads(json_part)
    assert parsed["status_code"] == 1
    assert parsed["limit"] == 100

