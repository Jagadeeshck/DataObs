from typing import Any, Dict, List

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from .authentication import SourceAuthenticator
from .dead_letter import safe_dead_letter
from .normalizer import normalize
from .repository import InMemoryEventRepository


class Batch(BaseModel):
    events: List[Dict[str, Any]]


def create_app(authenticator: SourceAuthenticator, repository=None):
    app = FastAPI(title="DataObs OpenLineage Ingest")
    repo = repository or InMemoryEventRepository()

    def one(payload, authorization):
        try:
            binding = authenticator.authenticate(authorization.removeprefix("Bearer "))
            event = normalize(payload, binding)
            created = repo.append(event)
            return {"event_id": event["event_id"], "status": "accepted" if created else "duplicate"}
        except PermissionError as e:
            raise HTTPException(401, str(e))
        except Exception as e:
            source = "unknown"
            record = safe_dead_letter(payload, str(e), source)
            repo.dead_letter(record["event_fingerprint"], record)
            raise HTTPException(422, "invalid OpenLineage event")

    @app.post("/api/v1/openlineage/events", status_code=202)
    def event(payload: Dict[str, Any], authorization: str = Header("")):
        return one(payload, authorization)

    @app.post("/api/v1/openlineage/events/batch", status_code=207)
    def batch(body: Batch, authorization: str = Header("")):
        if len(body.events) > 100:
            raise HTTPException(413, "batch event limit exceeded")
        out = []
        for item in body.events:
            try:
                out.append(one(item, authorization))
            except HTTPException as e:
                out.append({"status": "rejected", "code": e.status_code})
        return {"results": out}

    @app.get("/api/v1/openlineage/sources")
    def sources():
        return {"sources": []}

    @app.get("/api/v1/openlineage/dead-letter")
    def dead_letter():
        return {"events": list(repo.dead_letters.values())}

    @app.post("/api/v1/openlineage/dead-letter/{event_id}/replay")
    def replay(event_id: str):
        raise HTTPException(409, "redacted dead letters require source replay")

    return app
