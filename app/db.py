"""データベースの準備（エンジンとセッション）"""
from sqlmodel import Session, SQLModel, create_engine

from app import config

DATABASE_URL = config.DATABASE_URL     # .env の値も使えるよう、config から読む

# SQLite を FastAPI で使うときの決まり文句（複数のスレッドから使えるようにする）
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables():
    """models.py のクラスをもとに、テーブルを作る（起動時に1度だけ）"""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
