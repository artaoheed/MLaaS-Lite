from fastapi import FastAPI

app = FastAPI(title="MLaaS Platform API", version="0.1.0")

@app.get("/")
def read_root():
    return {"status": "active", "service": "mlaas-backend"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

