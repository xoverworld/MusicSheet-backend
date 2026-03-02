"""
Database models using SQLAlchemy
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

from config import get_settings

settings = get_settings()

# Create database engine
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    transcriptions = relationship("Transcription", back_populates="user", cascade="all, delete-orphan")


class Transcription(Base):
    """Transcription model"""
    __tablename__ = "transcriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    audio_filename = Column(String(255), nullable=False)
    sheet_music_filename = Column(String(255), nullable=True)
    transcription_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="transcriptions")


def init_db():
    """Initialize database (create tables)"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


if __name__ == "__main__":
    # Run this to create tables
    init_db()