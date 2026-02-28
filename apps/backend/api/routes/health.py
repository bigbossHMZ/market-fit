from backend.api.router import app

@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
