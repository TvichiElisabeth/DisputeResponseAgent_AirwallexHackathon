"""Web UI for the dispute agent: FastAPI + server-rendered HTML + HTMX.

Run (one worker: state lives in records/state.json):
    uvicorn web.main:app --port 8000

Every action returns the whole main section re-rendered, so the numbers,
the queue, the cards and the outcomes never disagree after a click.
"""
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web import service

BASE = Path(__file__).resolve().parent
app = FastAPI(title="Dispute Response Agent", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


FILTERS = {"all", "needs", "auto"}


def _view(path: str, query: str = "") -> dict:
    """Which screen to draw: the queue (with a sidebar filter) or one case.
    Presentation only: every screen renders from the same service.page()."""
    parts = [s for s in path.split("/") if s]
    if len(parts) == 2 and parts[0] == "cases" and parts[1].isalnum():
        return {"screen": "case", "case": parts[1].upper(), "filter": "all"}
    f = parse_qs(query).get("view", ["all"])[0]
    return {"screen": "queue", "case": None, "filter": f if f in FILTERS else "all"}


def _main(request: Request) -> HTMLResponse:
    """After an action, re-draw the screen the person clicked from (HTMX sends its URL)."""
    current = urlsplit(request.headers.get("HX-Current-URL", "/"))
    return templates.TemplateResponse(request, "partials/_main.html",
                                      {"p": service.page(), "v": _view(current.path, current.query)})


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html",
                                      {"p": service.page(), "v": _view("/", request.url.query)})


@app.get("/cases/{case}", response_class=HTMLResponse)
def case_page(request: Request, case: str):
    return templates.TemplateResponse(request, "index.html",
                                      {"p": service.page(), "v": _view(f"/cases/{case}")})


@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


# ---- bank simulator (demo controls) ----

@app.post("/sandbox/seed", response_class=HTMLResponse)
def sandbox_seed(request: Request):
    service.seed()
    return _main(request)


@app.post("/sandbox/reject/A", response_class=HTMLResponse)
def sandbox_reject_a(request: Request):
    service.reject_a()
    return _main(request)


# ---- the agent ----

@app.post("/review", response_class=HTMLResponse)
def review(request: Request):
    service.review()
    return _main(request)


@app.post("/cases/{case}/approve", response_class=HTMLResponse)
def approve(request: Request, case: str, fingerprint: str = Form(...)):
    service.decide_approval(case, fingerprint, approve=True)
    return _main(request)


@app.post("/cases/{case}/reject", response_class=HTMLResponse)
def reject(request: Request, case: str, fingerprint: str = Form(...)):
    service.decide_approval(case, fingerprint, approve=False)
    return _main(request)


# ---- escalations ----

@app.post("/escalations/{case}/prepare", response_class=HTMLResponse)
def prepare(request: Request, case: str):
    service.prepare_package(case)
    return _main(request)


@app.post("/escalations/{case}/validate", response_class=HTMLResponse)
def validate(request: Request, case: str, subject: str = Form(""), body: str = Form(""),
             checks: list[str] = Form(default=[])):
    return templates.TemplateResponse(request, "partials/_gate.html",
                                      {"g": service.gate(case, subject, body, checks)})


@app.post("/escalations/{case}/resolve", response_class=HTMLResponse)
def resolve(request: Request, case: str, subject: str = Form(""), body: str = Form(""),
            checks: list[str] = Form(default=[])):
    service.resolve(case, subject, body, checks)
    return _main(request)


@app.post("/escalations/{case}/keep", response_class=HTMLResponse)
def keep(request: Request, case: str):
    service.keep_investigating(case)
    return _main(request)
