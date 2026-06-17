from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, logging

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="MACMIA GPU Backend", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from routers import chat, cv, health, skills, rncp, rag_chat
from routers.rncp_metiers import router as rncp_metiers_router
app.include_router(chat.router,     prefix="/api", tags=["Chat"])
app.include_router(cv.router,       prefix="/api", tags=["CV"])
app.include_router(health.router,   prefix="/api", tags=["Health"])
app.include_router(skills.router,   prefix="/api", tags=["Skills"])
app.include_router(rncp.router,     prefix="/api", tags=["RNCP"])
app.include_router(rag_chat.router, prefix="/api", tags=["RAG"])
app.include_router(rncp_metiers_router, prefix="/api")

@app.on_event("startup")
async def startup():
    logging.getLogger(__name__).info("🚀 MACMIA GPU — Llama 3.1 8B — Tesla T4")


from fastapi import UploadFile, File
import os

@app.post("/upload-frontend")
async def upload_frontend(file: UploadFile = File(...)):
    os.makedirs("/home/docker/macmia/frontend", exist_ok=True)
    content = await file.read()
    # Remplacer automatiquement BACKEND_URL pour pointer vers /api
    text = content.decode("utf-8", errors="replace")
    import re
    text = re.sub(r'const BACKEND_URL = "[^"]*"', 'const BACKEND_URL = "/api"', text)
    open("/home/docker/macmia/frontend/index.html", "w", encoding="utf-8").write(text)
    return {"status": "ok", "size": len(content)}


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/")
async def serve_frontend():
    return FileResponse("/home/docker/macmia/frontend/index.html")


from fastapi.responses import FileResponse
@app.get("/download-backend")
async def download_backend():
    return FileResponse("/tmp/macmia_backend.zip", filename="macmia_backend.zip")


import httpx
from fastapi import Request
from fastapi.responses import HTMLResponse, Response

@app.get("/chroma-explorer", response_class=HTMLResponse)
async def chroma_explorer():
    return open("/home/docker/macmia/backend/chroma_explorer.html").read()

@app.api_route("/chroma/{path:path}", methods=["GET","POST","PUT","DELETE"])
async def chroma_proxy(path: str, request: Request):
    body = await request.body()
    async with httpx.AsyncClient() as client:
        r = await client.request(
            method=request.method,
            url=f"http://localhost:8001/api/v1/{path}",
            content=body,
            headers={"Content-Type": "application/json"}
        )
    return Response(content=r.content, media_type="application/json")

if __name__ == "__main__":
    from config import settings
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False)
