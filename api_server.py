from fastapi import FastAPI

app = FastAPI(
    title="VI Translate API",
    description="API wrapper for VI-Translate",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "VI Translate API"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
