"""
FastAPI Server for Piano Transcription
Handles audio upload, transcription, authentication, and local database storage
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import logging
import uuid
import os

from transcriber import PianoTranscriber
from audio_converter import AudioConverter
from auth import hash_password, authenticate_user, create_access_token, get_current_user
from database import database
from db_models import get_db, User, init_db
from models import UserRegister, UserLogin, TokenResponse, PasswordChange, UserResponse
from config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database tables
init_db()

# Create FastAPI app
app = FastAPI(
    title="Piano Transcription API",
    description="Convert piano audio to sheet music with local database",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for serving files
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Piano Transcription API",
        "version": "2.0.0",
        "database": "PostgreSQL (Local)",
        "endpoints": {
            "health": "GET /health",
            "register": "POST /auth/register",
            "login": "POST /auth/login",
            "transcribe": "POST /transcribe",
            "transcriptions": "GET /transcriptions",
            "docs": "GET /docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Piano transcription server is running",
        "database": "PostgreSQL (Local)"
    }


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = database.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password and create user
        hashed_password = hash_password(user_data.password)
        user = database.create_user(db, user_data.email, hashed_password)
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@app.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    try:
        # Authenticate user
        user = authenticate_user(db, user_data.email, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at
    }


@app.post("/auth/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        # Verify old password
        from auth import verify_password
        if not verify_password(password_data.old_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Update password
        hashed_password = hash_password(password_data.new_password)
        database.update_user_password(db, current_user.id, hashed_password)
        
        return {"message": "Password updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


# ============================================================================
# TRANSCRIPTION ROUTES (Protected)
# ============================================================================

@app.post("/transcribe-temp")
async def transcribe_audio_temp(audio: UploadFile = File(...)):
    """
    Transcribe audio without saving to database (works without authentication)
    """
    try:
        # Read file data
        audio_data = await audio.read()
        filename = audio.filename or "audio"
        
        logger.info(f"Temporary transcription: {filename}, size: {len(audio_data)} bytes")
        
        # Check if format is supported
        if not AudioConverter.is_supported_format(filename):
            raise HTTPException(
                status_code=400,
                detail="Unsupported audio format. Supported: WAV, MP3, M4A, AAC, OGG, FLAC"
            )
        
        file_extension = AudioConverter.get_file_extension(filename)
        
        # Convert to WAV
        logger.info(f"Converting {file_extension} to WAV...")
        sample_rate, audio_array = AudioConverter.convert_to_wav(audio_data, filename)
        logger.info(f"Conversion successful: {len(audio_array)} samples at {sample_rate}Hz")
        
        # Transcribe audio
        transcriber = PianoTranscriber(sample_rate)
        result = transcriber.transcribe(audio_array)
        
        logger.info(f"Transcription complete: {len(result['notes'])} notes")
        
        # Return results WITHOUT saving
        return {
            "success": True,
            "transcription": {
                "title": "Untitled",
                "tempo": result['tempo'],
                "key": result['key'],
                "timeSignature": result['timeSignature'],
                "duration": result['duration'],
                "measures": result['measures'],
                "notes": result['notes']
            },
            "metadata": {
                "sampleRate": sample_rate,
                "durationSeconds": result['duration'],
                "originalFormat": file_extension
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    title: str = Form("Untitled Transcription"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Transcribe audio file to musical notation"""
    try:
        # Read file data
        audio_data = await audio.read()
        filename = audio.filename or "audio"
        
        logger.info(f"User {current_user.id}: Received file: {filename}, size: {len(audio_data)} bytes")
        
        # Check if format is supported
        if not AudioConverter.is_supported_format(filename):
            raise HTTPException(
                status_code=400,
                detail="Unsupported audio format. Supported: WAV, MP3, M4A, AAC, OGG, FLAC"
            )
        
        file_extension = AudioConverter.get_file_extension(filename)
        
        # Convert to WAV
        logger.info(f"Converting {file_extension} to WAV...")
        sample_rate, audio_array = AudioConverter.convert_to_wav(audio_data, filename)
        logger.info(f"Conversion successful: {len(audio_array)} samples at {sample_rate}Hz")
        
        # Transcribe audio
        transcriber = PianoTranscriber(sample_rate)
        result = transcriber.transcribe(audio_array)
        
        logger.info(f"Transcription complete: {len(result['notes'])} notes")
        
        # Save audio file
        audio_filename = f"{uuid.uuid4()}.{file_extension}"
        audio_path = database.save_audio(current_user.id, audio_filename, audio_data)
        
        # Save transcription to database
        transcription = database.create_transcription(
            db=db,
            user_id=current_user.id,
            title=title,
            audio_filename=os.path.basename(audio_path),
            sheet_music_filename=None,
            transcription_data={
                "tempo": result['tempo'],
                "key": result['key'],
                "timeSignature": result['timeSignature'],
                "duration": result['duration'],
                "measures": result['measures'],
                "notes": result['notes']
            }
        )
        
        # Return results
        return {
            "success": True,
            "transcription_id": transcription.id,
            "transcription": {
                "title": title,
                "tempo": result['tempo'],
                "key": result['key'],
                "timeSignature": result['timeSignature'],
                "duration": result['duration'],
                "measures": result['measures'],
                "notes": result['notes']
            },
            "audio_url": f"/uploads/audio/{os.path.basename(audio_path)}",
            "metadata": {
                "sampleRate": sample_rate,
                "durationSeconds": result['duration'],
                "originalFormat": file_extension
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@app.get("/transcriptions")
async def get_transcriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all transcriptions for current user"""
    try:
        transcriptions = database.get_user_transcriptions(db, current_user.id)
        
        return {
            "transcriptions": [
                {
                    "id": t.id,
                    "title": t.title,
                    "audio_url": f"/uploads/audio/{t.audio_filename}",
                    "sheet_music_url": f"/uploads/sheets/{t.sheet_music_filename}" if t.sheet_music_filename else None,
                    "transcription_data": t.transcription_data,
                    "created_at": t.created_at
                }
                for t in transcriptions
            ],
            "total": len(transcriptions)
        }
        
    except Exception as e:
        logger.error(f"Get transcriptions error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve transcriptions")


@app.get("/transcriptions/{transcription_id}")
async def get_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific transcription by ID"""
    try:
        transcription = database.get_transcription_by_id(db, transcription_id, current_user.id)
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found")
        
        return {
            "id": transcription.id,
            "title": transcription.title,
            "audio_url": f"/uploads/audio/{transcription.audio_filename}",
            "sheet_music_url": f"/uploads/sheets/{transcription.sheet_music_filename}" if transcription.sheet_music_filename else None,
            "transcription_data": transcription.transcription_data,
            "created_at": transcription.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get transcription error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve transcription")


@app.delete("/transcriptions/{transcription_id}")
async def delete_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete transcription"""
    try:
        success = database.delete_transcription(db, transcription_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Transcription not found")
        
        return {"message": "Transcription deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete transcription error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete transcription")


# ============================================================================
# PUBLIC ROUTES
# ============================================================================

@app.post("/analyze")
async def analyze_audio(audio: UploadFile = File(...)):
    """Get audio file information without transcription"""
    try:
        audio_data = await audio.read()
        filename = audio.filename or "audio"
        
        info = AudioConverter.get_audio_info(audio_data, filename)
        
        return {"success": True, "analysis": info}
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/test")
async def test_endpoint():
    """Test endpoint"""
    import os
    
    # Check if uploads directory exists
    uploads_exist = os.path.exists(settings.upload_dir)
    audio_dir = os.path.join(settings.upload_dir, "audio")
    audio_files = []
    
    if os.path.exists(audio_dir):
        audio_files = os.listdir(audio_dir)
    
    return {
        "message": "Piano Transcription API",
        "version": "2.0.0",
        "database": "PostgreSQL (Local)",
        "status": "running",
        "uploads_dir": settings.upload_dir,
        "uploads_exist": uploads_exist,
        "audio_dir_exists": os.path.exists(audio_dir),
        "audio_files": audio_files[:10]  # First 10 files
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("🎹 Starting Piano Transcription Server")
    logger.info("💾 Using Local PostgreSQL Database")
    logger.info("📝 Endpoints:")
    logger.info("   - POST http://localhost:3001/auth/register")
    logger.info("   - POST http://localhost:3001/auth/login")
    logger.info("   - POST http://localhost:3001/transcribe")
    logger.info("   - GET  http://localhost:3001/transcriptions")
    logger.info("   - GET  http://localhost:3001/docs (API documentation)")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3001,
        log_level="info"
    )