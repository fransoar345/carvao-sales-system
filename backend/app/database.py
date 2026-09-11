from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings


settings = get_settings()
database_url = settings.database_url

if not database_url or database_url.startswith("${{") or "://" not in database_url:
    print("[DATABASE] DATABASE_URL invalida ou nao resolvida; usando SQLite local.")
    database_url = "sqlite:///./carvao.db"
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
try:
    make_url(database_url)
    engine = create_engine(database_url, connect_args=connect_args)
except Exception as exc:
    print(f"[DATABASE] Falha ao configurar DATABASE_URL ({type(exc).__name__}); usando SQLite local.")
    engine = create_engine("sqlite:///./carvao.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
