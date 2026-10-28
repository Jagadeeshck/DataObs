from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.pathway_routes import PathwayRepository, create_pathway_router
from src.api.stream_routes import create_stream_router


class RecordingES:
    def __init__(self):
        self.requests = []

    def search(self, **request):
        self.requests.append(request)
        return {"hits": {"hits": []}}


def client():
    es = RecordingES()

    def auth(request: Request):
        request.state.tenant_id = "tenant-a"
        request.state.environment = "prod"
        request.state.principal = {"scopes": ["dataobs:admin"]}
        request.state.request_id = "release-test"

    app = FastAPI()
    app.include_router(create_pathway_router(lambda: es, auth))
    app.include_router(create_stream_router(lambda: SimpleNamespace(es=es), auth))
    return TestClient(app), es


def test_search_body_cannot_override_trusted_tenant_or_environment():
    c, es = client()
    for body in ({"environment": "stage"}, {"tenant_id": "tenant-b"}):
        assert c.post("/api/v1/pathways/search", json=body).status_code == 403
    assert not es.requests
    assert c.post("/api/v1/pathways/search", json={"environment": "prod"}).status_code == 200
    filters = es.requests[-1]["query"]["bool"]["filter"]
    assert {"term": {"tenant_id": "tenant-a"}} in filters
    assert {"term": {"environment": "prod"}} in filters


@pytest.mark.parametrize("path", ["pathways", "streams", "stream-topology/nodes"])
def test_query_cannot_escape_authenticated_environment(path):
    c, es = client()
    assert c.get(f"/api/v1/{path}?environment=stage", headers={"X-DataObs-Environment": "prod"}).status_code == 403
    assert not es.requests


@pytest.mark.parametrize("limit", [0, -1, 201, "invalid", None])
def test_search_body_page_bounds_are_enforced(limit):
    c, es = client()
    assert c.post("/api/v1/pathways/search", json={"limit": limit}).status_code == 422
    assert not es.requests


def test_pathway_repository_only_accepts_allowlisted_bounded_literal_queries():
    es = RecordingES()
    repo = PathwayRepository(es)
    for index in ("*", "dataobs-*", "unrelated"):
        with pytest.raises(ValueError):
            repo.search(index, "tenant-a", "prod", size=1)
    with pytest.raises(ValueError):
        repo.search("dataobs-pathway-definitions-v1-read", "tenant-a", "prod", size=501)
    repo.search(
        "dataobs-pathway-definitions-v1-read",
        "tenant-a",
        "prod",
        size=20,
        filters={"search": "orders*?"},
        after=["name", "id"],
    )
    request = es.requests[-1]
    assert request["search_after"] == ["name", "id"]
    assert request["sort"][-1] == {"_id": "asc"}
    assert "wildcard" not in repr(request["query"])
    assert request["query"]["bool"]["filter"][-1]["multi_match"]["query"] == "orders*?"
    repo.get_many("dataobs-pathway-nodes-v1-read", [str(i) for i in range(500)], "tenant-a", "prod")
    assert len(es.requests[-1]["query"]["bool"]["filter"][-1]["bool"]["should"][0]["terms"]["node_id"]) == 200
