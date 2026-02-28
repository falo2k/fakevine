"""Tests for the fakevine API endpoints."""
# ruff: noqa: S101
from fastapi import status
from fastapi.testclient import TestClient

from fakevine.fakevine import app

client = TestClient(app)


def test_undefined():
    response = client.get('/monkeyscanfly')
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_search_noparams():
    response = client.get('/search')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "error": "Object Not Found",
        "limit": 0,
        "offset": 0,
        "number_of_page_results": 0,
        "number_of_total_results": 0,
        "status_code": 101,
        "results": [],
        }
