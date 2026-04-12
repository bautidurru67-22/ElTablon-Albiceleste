from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "service": "El Tablón Albiceleste API"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}
