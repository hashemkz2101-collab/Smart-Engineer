from fastapi import FastAPI

app = FastAPI(
    title="Smart Engineer API",
    version="0.1.0",
    description="Smart Engineer backend API.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
