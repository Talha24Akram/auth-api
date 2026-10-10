import os

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from supa import get_client

app = FastAPI(title="Auth API", version="1.0")
supabase = get_client()
print("Server running and connected to Supabase")


class Credentials(BaseModel):
    email: str | None = None
    password: str | None = None


def error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


@app.get("/")
def root():
    return {"name": "Auth API", "docs": "/docs"}


@app.post("/auth/signup", status_code=201)
def signup(body: Credentials):
    if not body.email or not body.password:
        return error(400, "email and password are required")
    try:
        res = supabase.auth.sign_up({"email": body.email, "password": body.password})
    except Exception as exc:  # Supabase rejects weak passwords, bad emails, duplicates
        return error(400, str(exc))
    return {"user": res.user.model_dump(mode="json") if res.user else None}


@app.post("/auth/login")
def login(body: Credentials):
    if not body.email or not body.password:
        return error(400, "email and password are required")
    try:
        res = supabase.auth.sign_in_with_password({"email": body.email, "password": body.password})
    except Exception:
        return error(401, "Invalid login credentials")
    return {
        "access_token": res.session.access_token,
        "refresh_token": res.session.refresh_token,
        "token_type": "bearer",
        "expires_in": res.session.expires_in,
    }


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def profile(authorization: str | None = Header(default=None)):
    parts = (authorization or "").split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return error(401, "Access token required")
    try:
        res = supabase.auth.get_user(parts[1])
        user = res.user
    except Exception:
        user = None
    if user is None:
        return error(401, "Invalid or expired token")
    return {"id": user.id, "email": user.email, "created_at": user.created_at.isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
