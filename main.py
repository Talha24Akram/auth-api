import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from supa import get_client

app = FastAPI(
    title="Auth API",
    version="1.0",
    description="Sign up, log in and log out with Supabase Auth; routes guarded by a bearer-token dependency.",
)
bearer = HTTPBearer(auto_error=False, description="Paste the access_token from POST /auth/login")
supabase = get_client()
print("Server running and connected to Supabase")


class Credentials(BaseModel):
    email: str | None = None
    password: str | None = None


def error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


@app.exception_handler(StarletteHTTPException)
async def http_error(_, exc: StarletteHTTPException):
    return error(exc.status_code, str(exc.detail))


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    """The guard: verify the bearer token with Supabase and inject the user."""
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Access token required")
    try:
        user = supabase.auth.get_user(creds.credentials).user
    except Exception:
        user = None
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


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
def profile(user=Depends(current_user)):
    return {"id": user.id, "email": user.email, "created_at": user.created_at.isoformat()}


@app.get("/protected/dashboard")
def dashboard(user=Depends(current_user)):
    return {"message": f"Welcome back, {user.email}!"}


@app.post("/auth/logout", status_code=204)
def logout(user=Depends(current_user)):
    supabase.auth.sign_out()
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
