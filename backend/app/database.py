import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings


settings = get_settings()
database_url = settings.database_url
is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))

if not database_url or database_url.startswith("${{") or "://" not in database_url:
    if is_railway:
        raise RuntimeError("DATABASE_URL ausente ou invalida na Railway. Conecte um PostgreSQL persistente antes de iniciar o servico.")
    print("[DATABASE] DATABASE_URL ausente; usando SQLite somente no ambiente local.")
    database_url = "sqlite:///./carvao.db"
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

if is_railway and database_url.startswith("sqlite"):
    raise RuntimeError("SQLite temporario nao e permitido na Railway. Configure DATABASE_URL com o PostgreSQL persistente.")

connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
try:
    make_url(database_url)
    engine = create_engine(database_url, connect_args=connect_args)
except Exception as exc:
    raise RuntimeError(f"DATABASE_URL invalida: {type(exc).__name__}") from exc
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
