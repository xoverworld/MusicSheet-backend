"""
Audio Format Converter
Converts various audio formats (MP3, M4A, OGG, etc.) to WAV using pydub
"""

import io
import numpy as np
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError


class AudioConverter:
    """Handle conversion of various audio formats to WAV"""
    
    SUPPORTED_FORMATS = {
        'mp3', 'wav', 'm4a', 'aac', 'ogg', 
        'flac', 'wma', 'opus', 'webm', 'aiff'
    }
    
    @staticmethod
    def convert_to_wav(audio_data, filename):
        """
        Convert any audio format to WAV
        
        Args:
            audio_data: Audio file bytes
            filename: Original filename (for format detection)
            
        Returns:
            tuple: (sample_rate, audio_array)
        """
        # Get file extension
        extension = AudioConverter.get_file_extension(filename)
        
        try:
            # Load audio file
            if extension == 'wav':
                audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            elif extension == 'mp3':
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            elif extension in ['m4a', 'aac']:
                audio = AudioSegment.from_file(io.BytesIO(audio_data), format='m4a')
            elif extension == 'ogg':
                audio = AudioSegment.from_ogg(io.BytesIO(audio_data))
            elif extension == 'flac':
                audio = AudioSegment.from_file(io.BytesIO(audio_data), format='flac')
            else:
                # Try to auto-detect format
                audio = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Convert to mono
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Ensure 44.1kHz sample rate
            if audio.frame_rate != 44100:
                audio = audio.set_frame_rate(44100)
            
            # Convert to numpy array
            samples = np.array(audio.get_array_of_samples())
            
            # Normalize to float32 [-1.0, 1.0]
            if audio.sample_width == 1:  # 8-bit
                samples = samples.astype(np.float32) / 128.0 - 1.0
            elif audio.sample_width == 2:  # 16-bit
                samples = samples.astype(np.float32) / 32768.0
            elif audio.sample_width == 4:  # 32-bit
                samples = samples.astype(np.float32) / 2147483648.0
            else:
                samples = samples.astype(np.float32)
            
            return audio.frame_rate, samples
            
        except CouldntDecodeError as e:
            raise ValueError(f"Failed to decode audio file: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error converting audio: {str(e)}")
    
    @staticmethod
    def get_audio_info(audio_data, filename):
        """
        Get audio file information
        
        Args:
            audio_data: Audio file bytes
            filename: Original filename
            
        Returns:
            dict with audio metadata
        """
        extension = AudioConverter.get_file_extension(filename)
        
        try:
            if extension == 'wav':
                audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            elif extension == 'mp3':
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            else:
                audio = AudioSegment.from_file(io.BytesIO(audio_data))
            
            return {
                'format': extension,
                'duration': len(audio) / 1000.0,  # Convert ms to seconds
                'sample_rate': audio.frame_rate,
                'channels': audio.channels,
                'sample_width': audio.sample_width * 8,  # Convert bytes to bits
            }
        except Exception as e:
            raise ValueError(f"Failed to get audio info: {str(e)}")
    
    @staticmethod
    def is_supported_format(filename):
        """
        Check if file format is supported
        
        Args:
            filename: Filename with extension
            
        Returns:
            bool
        """
        extension = AudioConverter.get_file_extension(filename)
        return extension in AudioConverter.SUPPORTED_FORMATS
    
    @staticmethod
    def get_file_extension(filename):
        """
        Get file extension
        
        Args:
            filename: Filename
            
        Returns:
            Extension without dot (lowercase)
        """
        if '.' in filename:
            return filename.rsplit('.', 1)[1].lower()
        return ''