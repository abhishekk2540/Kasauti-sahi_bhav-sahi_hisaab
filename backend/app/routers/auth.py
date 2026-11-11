import io

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import User
from ..schemas import LoginIn, ProfileUpdate, SignupIn, TokenOut, UserOut
from ..security import create_token, hash_password, verify_password
from ..services.notify import deep_link

router = APIRouter(tags=["auth"])
MAX_LOGO_BYTES = 2 * 1024 * 1024


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, phone=u.phone, shop_name=u.shop_name, has_logo=bool(u.logo),
                   telegram_linked=bool(u.telegram_chat_id), telegram_link=deep_link("u", u.link_token))


@router.post("/auth/signup", response_model=TokenOut, status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    u = User(email=email, phone=body.phone, shop_name=body.shop_name, password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    return TokenOut(access_token=create_token(u.id))


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email.lower()))
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return TokenOut(access_token=create_token(u.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return _user_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    return _user_out(user)


@router.put("/me/logo", response_model=UserOut)
async def upload_logo(file: UploadFile = File(...), user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    data = await file.read(MAX_LOGO_BYTES + 1)
    if len(data) > MAX_LOGO_BYTES:
        raise HTTPException(413, "Logo must be under 2 MB")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        fmt = Image.open(io.BytesIO(data)).format
    except Exception:
        raise HTTPException(400, "Not a valid image")
    if fmt not in ("PNG", "JPEG", "WEBP"):
        raise HTTPException(400, "Use PNG, JPEG or WEBP")
    user.logo, user.logo_mime = data, f"image/{fmt.lower()}"
    db.commit()
    return _user_out(user)


@router.get("/me/logo")
def get_logo(user: User = Depends(current_user)):
    if not user.logo:
        raise HTTPException(404, "No logo")
    return Response(user.logo, media_type=user.logo_mime or "image/png")
