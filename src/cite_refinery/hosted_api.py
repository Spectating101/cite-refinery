"""Private API for transactional research workspaces; never mount the public demo.

Token-only first milestone. Run on loopback; terminate TLS at a trusted private
proxy only after a separate deployment/security review. No CORS wildcard.
"""

from typing import Any

from .hosted_store import NotFound, PermissionDenied, StateConflict, WorkspaceDB


def create_private_app(db_path: str):
    try:
        from fastapi import Depends, FastAPI, Header, HTTPException, Request
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError("Install cite-refinery[server] for private HTTP API") from exc

    store = WorkspaceDB(db_path)
    app = FastAPI(
        title="Cite-Refinery Private Workspaces",
        version="0.21.0",
        docs_url=None, redoc_url=None, openapi_url=None,
    )

    @app.middleware("http")
    async def defensive_headers(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            raw_size = request.headers.get("content-length")
            if not raw_size:
                return JSONResponse({"detail": "content-length required"}, status_code=411)
            if not raw_size.isdigit() or int(raw_size) > 8 * 1024 * 1024:
                return JSONResponse({"detail": "request too large"}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.exception_handler(PermissionDenied)
    async def forbidden(_request: Request, _exc: PermissionDenied):
        return JSONResponse({"detail": "access denied"}, status_code=403)

    @app.exception_handler(NotFound)
    async def not_found(_request: Request, _exc: NotFound):
        return JSONResponse({"detail": "not found"}, status_code=404)

    @app.exception_handler(StateConflict)
    async def conflict(_request: Request, exc: StateConflict):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def bad_input(_request: Request, exc: ValueError):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    def current_user(authorization: str | None = Header(default=None)) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Bearer credential required",
                                headers={"WWW-Authenticate": "Bearer"})
        raw = authorization[len("Bearer "):]
        try:
            return store.authenticate(raw)
        except PermissionDenied:
            raise HTTPException(401, "Invalid or expired credential",
                                headers={"WWW-Authenticate": "Bearer"}) from None

    class ProjectCreate(BaseModel):
        tenant_id: str = Field(min_length=1, max_length=120)
        title: str = Field(min_length=1, max_length=300)
        problem: str = Field(min_length=1, max_length=10000)

    class EvolutionCapture(BaseModel):
        label: str = Field(min_length=5, max_length=140)
        expected_revision: int = Field(ge=0)

    class PacketRequest(BaseModel):
        packet: dict[str, Any]

    class EnqueueRequest(BaseModel):
        packet: dict[str, Any]
        expected_revision: int = Field(ge=0)
        expected_packet_digest: str = Field(min_length=64, max_length=64)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "cite-refinery-private-api"}

    @app.get("/api/projects")
    def projects(user: str = Depends(current_user)):
        return store.list_projects(user)

    @app.post("/api/projects", status_code=201)
    def new_project(body: ProjectCreate, user: str = Depends(current_user)):
        project_id = store.create_project(user, body.tenant_id, body.title, body.problem)
        return {"id": project_id}

    @app.get("/api/projects/{project_id}")
    def project(project_id: str, user: str = Depends(current_user)):
        return store.project_projection(user, project_id)

    @app.get("/api/projects/{project_id}/atlas")
    def atlas(project_id: str, user: str = Depends(current_user)):
        return store.project_projection(user, project_id)["atlas"]

    @app.get("/api/projects/{project_id}/nodes/{node_id}/coverage")
    def node(project_id: str, node_id: str, user: str = Depends(current_user)):
        from .workspace import ProductWorkspace
        from .hosted_store import _MemoryStore
        data = store.project_state(user, project_id)
        if node_id not in data["semantic_nodes"]:
            raise NotFound("unknown node")
        return ProductWorkspace(_MemoryStore(data)).node_view(project_id, node_id)

    @app.get("/api/projects/{project_id}/evolution/snapshots")
    def snapshots(project_id: str, user: str = Depends(current_user)):
        return store.list_snapshots(user, project_id)

    @app.post("/api/projects/{project_id}/evolution/snapshots", status_code=201)
    def capture_snapshot(project_id: str, body: EvolutionCapture,
                         user: str = Depends(current_user)):
        return store.capture_snapshot(
            user, project_id, body.label, body.expected_revision)

    @app.get("/api/projects/{project_id}/evolution/compare")
    def compare_evolution(project_id: str, from_snapshot: str, to_snapshot: str,
                          user: str = Depends(current_user)):
        return store.compare_snapshots(
            user, project_id, from_snapshot, to_snapshot)

    @app.post("/api/projects/{project_id}/ingest/preview")
    def preview(project_id: str, body: PacketRequest, user: str = Depends(current_user)):
        return store.preview(user, project_id, body.packet)

    @app.post("/api/projects/{project_id}/ingest", status_code=202)
    def enqueue(project_id: str, body: EnqueueRequest, user: str = Depends(current_user)):
        job_id = store.enqueue(
            user, project_id, body.packet,
            body.expected_revision, body.expected_packet_digest)
        return {"job_id": job_id, "status": "queued"}

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str, user: str = Depends(current_user)):
        return store.get_job(user, job_id)

    @app.get("/api/projects/{project_id}/audit")
    def audit(project_id: str, user: str = Depends(current_user)):
        return store.audit_events(user, project_id)

    return app
