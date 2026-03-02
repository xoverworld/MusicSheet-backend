"""
Database module
Handles local PostgreSQL database operations
"""

from sqlalchemy.orm import Session
from db_models import User, Transcription, get_db
from typing import List, Optional
import os
from config import get_settings

settings = get_settings()


class Database:
    """Database operations wrapper"""
    
    def __init__(self):
        """Initialize database"""
        # Ensure upload directories exist
        os.makedirs(settings.upload_dir, exist_ok=True)
        os.makedirs(os.path.join(settings.upload_dir, "audio"), exist_ok=True)
        os.makedirs(os.path.join(settings.upload_dir, "sheets"), exist_ok=True)
    
    # User operations
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    def create_user(self, db: Session, email: str, hashed_password: str) -> User:
        """Create new user"""
        user = User(email=email, hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def update_user_password(self, db: Session, user_id: str, hashed_password: str) -> User:
        """Update user password"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.hashed_password = hashed_password
            db.commit()
            db.refresh(user)
        return user
    
    # Transcription operations
    def create_transcription(
        self, 
        db: Session,
        user_id: str, 
        title: str, 
        audio_filename: str,
        sheet_music_filename: Optional[str],
        transcription_data: dict
    ) -> Transcription:
        """Save transcription to database"""
        transcription = Transcription(
            user_id=user_id,
            title=title,
            audio_filename=audio_filename,
            sheet_music_filename=sheet_music_filename,
            transcription_data=transcription_data
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        return transcription
    
    def get_user_transcriptions(self, db: Session, user_id: str) -> List[Transcription]:
        """Get all transcriptions for a user"""
        return db.query(Transcription).filter(
            Transcription.user_id == user_id
        ).order_by(Transcription.created_at.desc()).all()
    
    def get_transcription_by_id(
        self, 
        db: Session,
        transcription_id: str, 
        user_id: str
    ) -> Optional[Transcription]:
        """Get specific transcription by ID"""
        return db.query(Transcription).filter(
            Transcription.id == transcription_id,
            Transcription.user_id == user_id
        ).first()
    
    def delete_transcription(self, db: Session, transcription_id: str, user_id: str) -> bool:
        """Delete transcription"""
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id,
            Transcription.user_id == user_id
        ).first()
        
        if transcription:
            # Delete files
            self.delete_file(transcription.audio_filename)
            if transcription.sheet_music_filename:
                self.delete_file(transcription.sheet_music_filename)
            
            # Delete from database
            db.delete(transcription)
            db.commit()
            return True
        return False
    
    # File operations
    def save_audio(self, user_id: str, file_name: str, file_data: bytes) -> str:
        """Save audio file to local storage"""
        file_path = os.path.join(settings.upload_dir, "audio", f"{user_id}_{file_name}")
        with open(file_path, "wb") as f:
            f.write(file_data)
        return file_path
    
    def save_sheet_music(self, user_id: str, file_name: str, file_data: bytes) -> str:
        """Save sheet music image to local storage"""
        file_path = os.path.join(settings.upload_dir, "sheets", f"{user_id}_{file_name}")
        with open(file_path, "wb") as f:
            f.write(file_data)
        return file_path
    
    def get_file_path(self, filename: str, file_type: str = "audio") -> str:
        """Get full path to a file"""
        return os.path.join(settings.upload_dir, file_type, filename)
    
    def delete_file(self, filename: str):
        """Delete file from storage"""
        if not filename:
            return
        
        # Try both audio and sheets directories
        for subdir in ["audio", "sheets"]:
            file_path = os.path.join(settings.upload_dir, subdir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")


# Singleton instance
database = Database()