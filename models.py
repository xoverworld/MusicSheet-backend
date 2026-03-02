"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Auth models
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


# Transcription models
class TranscriptionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class TranscriptionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    audio_url: str
    sheet_music_url: Optional[str] = None
    transcription_data: Dict[str, Any]
    created_at: datetime


class TranscriptionListResponse(BaseModel):
    transcriptions: List[TranscriptionResponse]
    total: int


# Upload response
class UploadResponse(BaseModel):
    url: str
    path: str


# Error response
class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None