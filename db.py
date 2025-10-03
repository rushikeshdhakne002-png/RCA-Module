from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import pathlib, os

BASE_DIR = pathlib.Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "rca_tracker.db"

# Default to local SQLite; allow override via env for cloud Postgres
DEFAULT_DB_URL = f"sqlite:///{DB_PATH.as_posix()}"
DB_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)

engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(String(100), index=True)
    module_name = Column(String(100), index=True)
    reported_date = Column(DateTime(timezone=True), index=True)
    reported_by = Column(String(100), index=True)
    priority = Column(String(20), index=True)
    description = Column(Text)
    steps_to_reproduce = Column(Text)
    impacted_functionality = Column(Text)
    root_cause_identified = Column(String(200))
    rca_notes = Column(Text)
    short_term_fix = Column(Text)
    long_term_preventive_action = Column(Text)
    responsible_person = Column(String(100), index=True)
    target_completion_date = Column(DateTime(timezone=True))
    verified_by = Column(String(100))
    verification_date = Column(DateTime(timezone=True))
    status = Column(String(30), index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

def init_db():
    Base.metadata.create_all(bind=engine)
