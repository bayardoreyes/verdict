from fastapi import FastAPI

app = FastAPI(title="Verdict API")


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Verdict"}