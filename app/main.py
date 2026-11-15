"""アプリの入口: みらい商事のヘルプデスク（社内向けのアシスタントと、顧客向けの FAQ 窓口）"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth import check_secret
from app.db import create_db_and_tables
from app.llm.factory import check_provider
from app.routers import approvals, assistant, auth, public

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logging.getLogger("watchfiles").setLevel(logging.WARNING)   # 開発用のサーバーが出す「ファイルの変更」の記録は出さない


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_secret()
    check_provider()
    create_db_and_tables()
    yield


app = FastAPI(title="みらい商事 ヘルプデスク API（練習用）", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(assistant.router)
app.include_router(public.router)
app.include_router(approvals.router)
