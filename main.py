"""
FastAPI Server for Piano Transcription
Handles audio upload and transcription
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from typing import Optional
import logging

from transcriber import PianoTranscriber
from audio_converter import AudioConverter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Piano Transcription API",
    description="Convert piano audio to sheet music using custom signal processing",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Piano Transcription API",
        "version": "2.0.0",
        "endpoints": {
            "health": "GET /health",
            "transcribe": "POST /transcribe",
            "analyze": "POST /analyze",
            "docs": "GET /docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Piano transcription server is running"
    }


@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe audio file to musical notation
    
    Args:
        audio: Audio file (MP3, WAV, M4A, OGG, FLAC, etc.)
        
    Returns:
        JSON with transcription results
    """
    try:
        # Read file data
        audio_data = await audio.read()
        filename = audio.filename or "audio"
        
        logger.info(f"Received file: {filename}, size: {len(audio_data)} bytes")
        
        # Check if format is supported
        if not AudioConverter.is_supported_format(filename):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Unsupported audio format",
                    "supported": "WAV, MP3, M4A, AAC, OGG, FLAC, WMA, OPUS, WEBM, AIFF"
                }
            )
        
        file_extension = AudioConverter.get_file_extension(filename)
        logger.info(f"File format: {file_extension}")
        
        # Convert to WAV if needed
        try:
            logger.info(f"Converting {file_extension} to WAV...")
            sample_rate, audio_array = AudioConverter.convert_to_wav(audio_data, filename)
            logger.info(f"Conversion successful: {len(audio_array)} samples at {sample_rate}Hz")
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": "Failed to decode audio file", "details": str(e)}
            )
        
        # Create transcriber and process audio
        transcriber = PianoTranscriber(sample_rate)
        result = transcriber.transcribe(audio_array)
        
        logger.info(f"Transcription complete: {len(result['notes'])} notes, "
                   f"tempo: {result['tempo']} BPM, key: {result['key']}")
        
        # Return results
        return {
            "success": True,
            "transcription": {
                "title": "Piano Transcription",
                "tempo": result['tempo'],
                "key": result['key'],
                "timeSignature": result['timeSignature'],
                "duration": result['duration'],
                "measures": result['measures'],
                "notes": result['notes']
            },
            "metadata": {
                "sampleRate": sample_rate,
                "audioLength": len(audio_array),
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
            detail={"error": "Transcription failed", "details": str(e)}
        )


@app.post("/analyze")
async def analyze_audio(audio: UploadFile = File(...)):
    """
    Get audio file information without full transcription
    
    Args:
        audio: Audio file
        
    Returns:
        JSON with audio metadata
    """
    try:
        # Read file data
        audio_data = await audio.read()
        filename = audio.filename or "audio"
        
        file_extension = AudioConverter.get_file_extension(filename)
        
        # Get audio info
        try:
            info = AudioConverter.get_audio_info(audio_data, filename)
            
            return {
                "success": True,
                "analysis": {
                    "format": file_extension,
                    "duration": info['duration'],
                    "sampleRate": info['sample_rate'],
                    "channels": info['channels'],
                    "bitDepth": info['sample_width']
                }
            }
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": "Failed to analyze audio", "details": str(e)}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Analysis failed", "details": str(e)}
        )


@app.get("/test")
async def test_endpoint():
    """Test endpoint for debugging"""
    return {
        "message": "Piano Transcription API",
        "version": "2.0.0",
        "status": "running",
        "supported_formats": list(AudioConverter.SUPPORTED_FORMATS)
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("🎹 Starting Piano Transcription Server")
    logger.info("📝 Endpoints:")
    logger.info("   - POST http://localhost:3001/transcribe")
    logger.info("   - POST http://localhost:3001/analyze")
    logger.info("   - GET  http://localhost:3001/health")
    logger.info("   - GET  http://localhost:3001/docs (API documentation)")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3001,
        log_level="info"
    )