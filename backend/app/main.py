from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.charts import render_signal_chart_svg
from app.ingest.catalog import load_source_catalog
from app.render_plan import build_storyboard, generate_srt, render_preview_html
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


class EditorialDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|hold|revise|archive)$")
    editor: str = "editor"
    notes: str = ""


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


@app.get("/api/stories/{story_id}/decision")
def decision(story_id: str) -> dict[str, object]:
    try:
        return store.get_decision(story_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story not found") from exc


@app.post("/api/stories/{story_id}/decision")
def record_decision(story_id: str, request: EditorialDecisionRequest) -> dict[str, object]:
    try:
        return store.record_decision(story_id, request.decision, request.editor, request.notes)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/stories/{story_id}/chart.svg")
def chart_svg(story_id: str) -> Response:
    try:
        story = store.get_story(story_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story not found") from exc
    return Response(content=render_signal_chart_svg(story), media_type="image/svg+xml")


@app.get("/api/stories/{story_id}/storyboard")
def storyboard(story_id: str) -> dict[str, object]:
    try:
        story = store.get_story(story_id)
        package = store.get_or_generate_package(story_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story not found") from exc
    return build_storyboard(story, package)


@app.get("/api/stories/{story_id}/captions.srt")
def captions(story_id: str) -> Response:
    try:
        package = store.get_or_generate_package(story_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story not found") from exc
    return Response(content=generate_srt(package), media_type="application/x-subrip")


@app.get("/api/stories/{story_id}/preview.html")
def preview(story_id: str) -> Response:
    try:
        story = store.get_story(story_id)
        package = store.get_or_generate_package(story_id)
        qa = store.get_qa(story_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story not found") from exc
    storyboard = build_storyboard(story, package)
    chart_ref = f"/api/stories/{story_id}/chart.svg"
    return Response(
        content=render_preview_html(story, package, storyboard, qa, chart_ref=chart_ref),
        media_type="text/html",
    )


@app.post("/api/sources/rss")
def ingest_rss(request: RssIngestRequest) -> dict[str, object]:
    items = store.ingest_rss(request.feed_url, request.source_name, request.source_type)
    return {"ingested": len(items), "items": items, "stories": store.list_stories()}


@app.get("/api/sources/catalog")
def source_catalog() -> list[dict[str, str]]:
    return [feed.to_dict() for feed in load_source_catalog()]
