"""HTTP endpoints for authentication (IAM-001). Logic lives in auth_service."""

from collections.abc import Iterator
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import auth_service as auth
from .errors import _correlation_id, _envelope

SESSION_COOKIE = "se_session"
CSRF_HEADER = "X-CSRF-Token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

STATUS_BY_CODE = {
    "invalid_credentials": 401,
    "account_locked": 429,
    "email_taken": 409,
    "email_not_verified": 403,
    "invalid_token": 400,
    "invalid_email": 422,
    "invalid_display_name": 422,
    "weak_password": 422,
}
MESSAGE_BY_CODE = {
    "invalid_credentials": "The email or password is incorrect.",
    "account_locked": "Too many failed attempts. Try again later.",
    "email_taken": "An account with this email already exists.",
    "email_not_verified": "The email address has not been verified.",
    "invalid_token": "The link or token is invalid or has expired.",
    "invalid_email": "The email address is not valid.",
    "invalid_display_name": "The name is required and must be at most 200 characters.",
    "weak_password": "The password does not meet the password policy.",
}


async def auth_error_handler(request: Request, exc: auth.AuthError) -> JSONResponse:
    details = [{"msg": problem} for problem in exc.problems] or None
    message = MESSAGE_BY_CODE.get(exc.code, "Error")
    return JSONResponse(
        _envelope(exc.code, message, _correlation_id(request), details),
        status_code=STATUS_BY_CODE.get(exc.code, 400),
    )


class RegisterBody(BaseModel):
    email: str = Field(max_length=320)
    display_name: str = Field(max_length=200)
    password: str = Field(max_length=1024)


class LoginBody(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


class ChangePasswordBody(BaseModel):
    current_password: str = Field(max_length=1024)
    new_password: str = Field(max_length=1024)


class ResetRequestBody(BaseModel):
    email: str = Field(max_length=320)


class ResetConfirmBody(BaseModel):
    token: str = Field(max_length=512)
    new_password: str = Field(max_length=1024)


def get_db(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    if factory is None:
        raise HTTPException(status_code=503)
    with factory() as session:
        yield session


def check_origin(request: Request) -> None:
    """Reject cross-site browser requests that carry a foreign Origin header."""
    if request.method not in UNSAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin is None:
        return
    allowed = request.app.state.settings.allowed_origins
    if origin.rstrip("/") in allowed:
        return
    if urlparse(origin).netloc == request.headers.get("host"):
        return
    raise HTTPException(status_code=403)


def user_payload(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_system_admin": user.is_system_admin,
    }


class Authenticated:
    def __init__(self, record, user) -> None:
        self.record = record
        self.user = user


def current_auth(request: Request, db: Session = Depends(get_db)) -> Authenticated:
    token = request.cookies.get(SESSION_COOKIE)
    found = auth.authenticate(db, request.app.state.auth_policy, token) if token else None
    if found is None:
        raise HTTPException(status_code=401)
    return Authenticated(*found)


def csrf_protected(
    request: Request, current: Authenticated = Depends(current_auth)
) -> Authenticated:
    if not auth.csrf_matches(current.record, request.headers.get(CSRF_HEADER)):
        raise HTTPException(status_code=403)
    return current


def set_session_cookie(request: Request, response: Response, token: str) -> None:
    policy = request.app.state.auth_policy
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(policy.session_absolute.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=request.app.state.settings.environment == "production",
        path="/",
    )


router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(check_origin)])


@router.post("/register", status_code=201)
def register(body: RegisterBody, request: Request, db: Session = Depends(get_db)) -> dict:
    user = auth.register(
        db,
        request.app.state.auth_policy,
        email=body.email,
        display_name=body.display_name,
        password=body.password,
    )
    policy = request.app.state.auth_policy
    if policy.require_email_verification:
        auth.request_email_verification(
            db, policy, request.app.state.mailer, email=user.email
        )
    return {
        "user": user_payload(user),
        "verification_required": policy.require_email_verification,
    }


@router.post("/email-verification/request", status_code=202)
def email_verification_request(
    body: ResetRequestBody, request: Request, db: Session = Depends(get_db)
) -> dict:
    auth.request_email_verification(
        db, request.app.state.auth_policy, request.app.state.mailer, email=body.email
    )
    return {"status": "accepted"}


class EmailConfirmBody(BaseModel):
    token: str = Field(min_length=1, max_length=200)


@router.post("/email-verification/confirm", status_code=204)
def email_verification_confirm(
    body: EmailConfirmBody, request: Request, db: Session = Depends(get_db)
) -> Response:
    auth.confirm_email(db, token=body.token)
    return Response(status_code=204)


@router.post("/login")
def login(
    body: LoginBody, request: Request, response: Response, db: Session = Depends(get_db)
) -> dict:
    issued = auth.login(
        db, request.app.state.auth_policy, email=body.email, password=body.password
    )
    set_session_cookie(request, response, issued.token)
    return {"user": user_payload(issued.user), "csrf_token": issued.csrf_token}


@router.get("/me")
def me(current: Authenticated = Depends(current_auth)) -> dict:
    return {"user": user_payload(current.user), "csrf_token": current.record.csrf_token}


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current: Authenticated = Depends(csrf_protected),
) -> Response:
    auth.logout(db, request.cookies[SESSION_COOKIE])
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordBody,
    request: Request,
    db: Session = Depends(get_db),
    current: Authenticated = Depends(csrf_protected),
) -> Response:
    auth.change_password(
        db,
        request.app.state.auth_policy,
        current.user,
        current_password=body.current_password,
        new_password=body.new_password,
        keep_session_id=current.record.id,
    )
    return Response(status_code=204)


@router.post("/password-reset/request", status_code=202)
def password_reset_request(
    body: ResetRequestBody, request: Request, db: Session = Depends(get_db)
) -> dict:
    auth.request_password_reset(
        db, request.app.state.auth_policy, request.app.state.mailer, email=body.email
    )
    return {"status": "accepted"}


@router.post("/password-reset/confirm", status_code=204)
def password_reset_confirm(
    body: ResetConfirmBody, request: Request, db: Session = Depends(get_db)
) -> Response:
    auth.reset_password(
        db,
        request.app.state.auth_policy,
        token=body.token,
        new_password=body.new_password,
    )
    return Response(status_code=204)
