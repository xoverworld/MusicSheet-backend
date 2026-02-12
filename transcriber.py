"""
Piano Transcription Engine
Combines pitch detection and onset detection to transcribe piano audio
"""

import numpy as np
from pitch_detection import PitchDetector
from onset_detection import OnsetDetector


class PianoTranscriber:
    def __init__(self, sample_rate):
        """
        Initialize piano transcriber
        
        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.pitch_detector = PitchDetector(sample_rate)
        self.onset_detector = OnsetDetector(sample_rate)
    
    def transcribe(self, audio_buffer):
        """
        Main transcription method
        
        Args:
            audio_buffer: Audio samples as numpy array
            
        Returns:
            dict with transcription results
        """
        print(f"Transcribing audio: {len(audio_buffer)} samples at {self.sample_rate}Hz")
        
        # Step 1: Detect onsets (when notes start)
        onsets = self.onset_detector.detect_onsets_combined(audio_buffer)
        print(f"Detected {len(onsets)} onsets")
        
        # Step 2: Analyze pitch at each onset
        notes = []
        frame_size = 4096  # ~93ms at 44.1kHz
        
        for i in range(len(onsets)):
            onset = onsets[i]
            start_sample = int(onset['time'] * self.sample_rate)
            
            # Extract audio frame after onset
            end_sample = min(start_sample + frame_size, len(audio_buffer))
            frame = audio_buffer[start_sample:end_sample]
            
            if len(frame) < frame_size / 2:
                continue  # Skip if frame too short
            
            # Detect pitch using both methods
            pitch_auto = self.pitch_detector.detect_pitch(frame)
            pitch_spectral = self.pitch_detector.detect_pitch_spectral(frame)
            
            final_pitch = None
            
            # Use autocorrelation result if confident
            if pitch_auto and pitch_auto['confidence'] > 0.7:
                final_pitch = pitch_auto
            # Otherwise use spectral if available
            elif pitch_spectral:
                final_pitch = pitch_spectral
            
            if final_pitch and final_pitch['frequency'] > 0:
                midi = self.pitch_detector.frequency_to_midi(final_pitch['frequency'])
                note_name = self.pitch_detector.midi_to_note_name(midi)
                
                # Calculate duration (time until next onset or end)
                next_onset_time = onsets[i + 1]['time'] if i < len(onsets) - 1 else onset['time'] + 1
                duration = next_onset_time - onset['time']
                
                notes.append({
                    'time': onset['time'],
                    'duration': duration,
                    'frequency': final_pitch['frequency'],
                    'midi': int(midi),
                    'note': note_name,
                    'confidence': final_pitch.get('confidence', 0.5),
                    'velocity': min(1.0, onset['strength'] * 1.5)
                })
        
        print(f"Transcribed {len(notes)} notes")
        
        # Step 3: Post-processing - quantize to musical durations
        quantized_notes = self._quantize_notes(notes)
        
        # Step 4: Organize into measures
        measures = self._organize_measures(quantized_notes)
        
        # Step 5: Detect key and tempo
        key = self._detect_key(quantized_notes)
        tempo = self._estimate_tempo(onsets)
        
        return {
            'notes': quantized_notes,
            'measures': measures,
            'tempo': tempo,
            'key': key,
            'timeSignature': '4/4',
            'duration': len(audio_buffer) / self.sample_rate
        }
    
    def _quantize_notes(self, notes):
        """
        Quantize note durations to common musical values
        
        Args:
            notes: List of note dicts
            
        Returns:
            List of quantized note dicts
        """
        # Musical durations in seconds at 120 BPM
        quarter_note = 0.5  # 500ms at 120 BPM
        musical_durations = {
            'whole': quarter_note * 4,
            'half': quarter_note * 2,
            'quarter': quarter_note,
            'eighth': quarter_note / 2,
            'sixteenth': quarter_note / 4
        }
        
        quantized = []
        for note in notes:
            # Find closest musical duration
            closest_duration = 'quarter'
            smallest_diff = float('inf')
            
            for name, value in musical_durations.items():
                diff = abs(note['duration'] - value)
                if diff < smallest_diff:
                    smallest_diff = diff
                    closest_duration = name
            
            quantized_note = note.copy()
            quantized_note['musicalDuration'] = closest_duration
            quantized.append(quantized_note)
        
        return quantized
    
    def _organize_measures(self, notes):
        """
        Organize notes into measures
        
        Args:
            notes: List of note dicts
            
        Returns:
            List of measure dicts
        """
        measures = []
        beats_per_measure = 4
        quarter_note = 0.5  # At 120 BPM
        measure_duration = quarter_note * beats_per_measure
        
        current_measure = []
        measure_start_time = 0
        measure_number = 1
        
        for note in notes:
            # Check if note belongs to next measure
            while note['time'] >= measure_start_time + measure_duration:
                if current_measure:
                    measures.append({
                        'number': measure_number,
                        'notes': current_measure,
                        'startTime': measure_start_time
                    })
                    measure_number += 1
                current_measure = []
                measure_start_time += measure_duration
            
            note_copy = note.copy()
            note_copy['beatPosition'] = (note['time'] - measure_start_time) / quarter_note
            current_measure.append(note_copy)
        
        # Add last measure
        if current_measure:
            measures.append({
                'number': measure_number,
                'notes': current_measure,
                'startTime': measure_start_time
            })
        
        return measures
    
    def _estimate_tempo(self, onsets):
        """
        Estimate tempo from onset intervals
        
        Args:
            onsets: List of onset dicts
            
        Returns:
            Tempo in BPM
        """
        if len(onsets) < 2:
            return 120  # Default tempo
        
        # Calculate intervals between onsets
        intervals = []
        for i in range(1, len(onsets)):
            intervals.append(onsets[i]['time'] - onsets[i - 1]['time'])
        
        # Find median interval (more robust than mean)
        median_interval = np.median(intervals)
        
        # Convert to BPM (assuming median interval is a quarter note)
        bpm = 60 / median_interval
        
        # Clamp to reasonable range
        return int(max(40, min(240, bpm)))
    
    def _detect_key(self, notes):
        """
        Detect musical key using Krumhansl-Schmuckler algorithm
        
        Args:
            notes: List of note dicts
            
        Returns:
            Key name (e.g., 'C major')
        """
        if not notes:
            return 'C major'
        
        # Count note occurrences (pitch classes)
        pitch_class_counts = np.zeros(12)
        
        for note in notes:
            pitch_class = note['midi'] % 12
            pitch_class_counts[pitch_class] += note['duration']
        
        # Major and minor key profiles (Krumhansl-Kessler)
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        best_key = 'C major'
        max_correlation = float('-inf')
        
        # Try all 24 keys (12 major + 12 minor)
        for tonic in range(12):
            # Major key
            major_corr = self._correlate(pitch_class_counts, major_profile, tonic)
            if major_corr > max_correlation:
                max_correlation = major_corr
                best_key = f"{note_names[tonic]} major"
            
            # Minor key
            minor_corr = self._correlate(pitch_class_counts, minor_profile, tonic)
            if minor_corr > max_correlation:
                max_correlation = minor_corr
                best_key = f"{note_names[tonic]} minor"
        
        return best_key
    
    def _correlate(self, observed, profile, shift):
        """
        Calculate correlation between pitch class distribution and key profile
        
        Args:
            observed: Observed pitch class distribution
            profile: Key profile
            shift: Transposition in semitones
            
        Returns:
            Correlation value
        """
        correlation = 0
        for i in range(12):
            correlation += observed[i] * profile[(i - shift) % 12]
        return correlation