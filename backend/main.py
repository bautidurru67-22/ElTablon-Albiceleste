from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.hoy import router as hoy_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "service": "El Tablón Albiceleste API"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

app.include_router(hoy_router, prefix="/api")
