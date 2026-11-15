"""認証（パスワードのハッシュ化・JWT の発行と確認・ログインしている本人の取り出し）"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlmodel import Session

from app import config
from app.db import get_session
from app.models import User

password_hash = PasswordHash.recommended()       # パスワード専用の、わざと時間のかかる方式（Argon2）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")   # /docs の鍵マークのボタンもこれで表示される
SECRET_KEY = config.JWT_SECRET
ALGORITHM = "HS256"


def check_secret():
    """起動時に呼ぶ。署名の鍵が無い・短すぎるときは、分かりやすいエラーで止める"""
    if len(config.JWT_SECRET) < 32:
        raise ValueError("JWT_SECRET が設定されていないか、短すぎます（32文字以上）。"
                         "README の手順で作った値を .env に書いてください")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}    # 誰のトークンか・いつまで有効か
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme),
                     session: Session = Depends(get_session)) -> User:
    unauthorized = HTTPException(status_code=401,
                                 detail="ログインが必要です（トークンが正しくないか、期限が切れています）",
                                 headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        raise unauthorized
    user = session.get(User, int(payload["sub"]))
    if user is None:
        raise unauthorized
    return user
