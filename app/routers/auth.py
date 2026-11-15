"""社内向けの入口のログイン"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.auth import create_access_token, verify_password
from app.db import get_session
from app.models import Token, User

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    # /docs の Authorize ボタンと同じ形（username にメールアドレスを入れる）
    user = session.exec(select(User).where(User.email == form.username)).first()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="メールアドレスかパスワードが違います")
    return Token(access_token=create_access_token(user.id))
