from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path
import os

# Database configuration
# Use DATABASE_URL from environment if available, otherwise use local SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Local development: use SQLite
    DB_DIR = Path(__file__).parent / "data"
    DB_DIR.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{DB_DIR}/resources.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}  # Needed for SQLite
    )
else:
    # Production: use environment DATABASE_URL (PostgreSQL, MySQL, etc.)
    engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
