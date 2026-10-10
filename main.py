import os

from fastapi import FastAPI

from supa import get_client

app = FastAPI(title="Auth API", version="1.0")
supabase = get_client()
print("Server running and connected to Supabase")


@app.get("/")
def root():
    return {"name": "Auth API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
