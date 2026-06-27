from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.ingest.catalog import load_source_catalog
from app.store import EditorialStore


app = FastAPI(
    title="Market Signal Studio API",
    description="Source-verifiable editorial engine for finance content packages.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = EditorialStore()


class RssIngestRequest(BaseModel):
    feed_url: str = Field(..., min_length=8)
    source_name: str = Field(..., min_length=2)
    source_type: str = "news_discovery"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/stories")
def stories() -> list[dict[str, object]]:
    return store.list_stories()


@app.post("/api/stories/refresh")
def refresh_stories() -> list[dict[str, object]]:
    store.refresh_stories()
    return store.list_stories()


@app.get("/api/stories/{story_id}")
def story(story_id: str) -> dict[str, object]:
    try:
        return store.get_story(story_id).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story not found") from exc


@app.post("/api/stories/{story_id}/package")
def package(story_id: str) -> dict[str, object]:
    try:
        return store.get_or_generate_package(story_id).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story not found") from exc


@app.get("/api/stories/{story_id}/qa")
def qa(story_id: str) -> dict[str, object]:
    try:
        return store.get_qa(story_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story not found") from exc


@app.post("/api/sources/rss")
def ingest_rss(request: RssIngestRequest) -> dict[str, object]:
    items = store.ingest_rss(request.feed_url, request.source_name, request.source_type)
    return {"ingested": len(items), "items": items, "stories": store.list_stories()}


@app.get("/api/sources/catalog")
def source_catalog() -> list[dict[str, str]]:
    return [feed.to_dict() for feed in load_source_catalog()]
