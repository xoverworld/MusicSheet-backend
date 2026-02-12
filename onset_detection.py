"""
Onset Detection - Detects when notes begin in audio
Uses spectral flux and energy-based methods
"""

import numpy as np
from fft import FFT, apply_hamming_window, next_power_of_2


class OnsetDetector:
    def __init__(self, sample_rate, hop_size=512):
        """
        Initialize onset detector
        
        Args:
            sample_rate: Audio sample rate in Hz
            hop_size: Hop size in samples
        """
        self.sample_rate = sample_rate
        self.hop_size = hop_size
    
    def detect_onsets(self, audio_buffer, threshold=0.3):
        """
        Detect onsets using spectral flux method
        
        Args:
            audio_buffer: Audio samples
            threshold: Detection threshold
            
        Returns:
            List of onset dicts with 'time' and 'strength'
        """
        frame_size = 2048
        hop_size = self.hop_size
        num_frames = int((len(audio_buffer) - frame_size) / hop_size)
        
        # Calculate spectral flux for each frame
        spectral_flux = np.zeros(num_frames)
        previous_spectrum = None
        
        fft = FFT(next_power_of_2(frame_size))
        
        for i in range(num_frames):
            start = i * hop_size
            frame = audio_buffer[start:start + frame_size]
            windowed = apply_hamming_window(frame)
            
            fft_result = fft.forward(windowed)
            magnitude = fft.magnitude(fft_result)
            
            if previous_spectrum is not None:
                # Calculate spectral flux (vectorized - much faster!)
                diff = magnitude - previous_spectrum
                spectral_flux[i] = np.sum(diff[diff > 0])
            
            previous_spectrum = magnitude.copy()
        
        # Normalize spectral flux
        max_flux = np.max(spectral_flux)
        if max_flux > 0:
            spectral_flux = spectral_flux / max_flux
        
        # Peak picking with adaptive threshold
        onsets = []
        window_size = 5  # frames for local average
        
        for i in range(window_size, len(spectral_flux) - window_size):
            # Calculate local average
            local_sum = np.sum(spectral_flux[i - window_size:i + window_size])
            local_avg = local_sum / (2 * window_size)
            adaptive_threshold = local_avg + threshold
            
            # Check if this is a peak above threshold
            if (spectral_flux[i] > adaptive_threshold and
                spectral_flux[i] > spectral_flux[i - 1] and
                spectral_flux[i] > spectral_flux[i + 1]):
                
                # Convert frame index to time
                time_in_seconds = (i * hop_size) / self.sample_rate
                onsets.append({
                    'time': time_in_seconds,
                    'strength': float(spectral_flux[i])
                })
        
        # Remove onsets that are too close together (< 50ms)
        filtered_onsets = []
        for i, onset in enumerate(onsets):
            if i == 0 or onset['time'] - onsets[i - 1]['time'] > 0.05:
                filtered_onsets.append(onset)
        
        return filtered_onsets
    
    def detect_onsets_energy(self, audio_buffer, threshold=1.5):
        """
        Detect onsets using energy-based method
        
        Args:
            audio_buffer: Audio samples
            threshold: Detection threshold
            
        Returns:
            List of onset dicts
        """
        frame_size = 2048
        hop_size = self.hop_size
        num_frames = int((len(audio_buffer) - frame_size) / hop_size)
        
        # Calculate energy for each frame
        energy = np.zeros(num_frames)
        
        for i in range(num_frames):
            start = i * hop_size
            frame = audio_buffer[start:min(start + frame_size, len(audio_buffer))]
            energy[i] = np.sum(frame ** 2) / len(frame)
        
        # Calculate energy difference
        energy_diff = np.zeros(num_frames)
        for i in range(1, num_frames):
            energy_diff[i] = max(0, energy[i] - energy[i - 1])
        
        # Normalize
        max_diff = np.max(energy_diff)
        if max_diff > 0:
            energy_diff = energy_diff / max_diff
        
        # Find peaks
        onsets = []
        for i in range(1, len(energy_diff) - 1):
            if (energy_diff[i] > threshold and
                energy_diff[i] > energy_diff[i - 1] and
                energy_diff[i] > energy_diff[i + 1]):
                
                time_in_seconds = (i * hop_size) / self.sample_rate
                onsets.append({
                    'time': time_in_seconds,
                    'strength': float(energy_diff[i])
                })
        
        return onsets
    
    def detect_onsets_combined(self, audio_buffer):
        """
        Combine multiple onset detection methods for better accuracy
        
        Args:
            audio_buffer: Audio samples
            
        Returns:
            List of onset dicts
        """
        spectral_onsets = self.detect_onsets(audio_buffer, 0.3)
        energy_onsets = self.detect_onsets_energy(audio_buffer, 1.5)
        
        # Merge onsets that are close to each other (within 20ms)
        merged_onsets = []
        tolerance = 0.02  # 20ms
        used_energy = set()
        
        for onset in spectral_onsets:
            found = False
            for j, e_onset in enumerate(energy_onsets):
                if j not in used_energy and abs(onset['time'] - e_onset['time']) < tolerance:
                    found = True
                    used_energy.add(j)
                    merged_onsets.append({
                        'time': (onset['time'] + e_onset['time']) / 2,
                        'strength': (onset['strength'] + e_onset['strength']) / 2,
                        'method': 'combined'
                    })
                    break
            
            if not found:
                merged_onsets.append({**onset, 'method': 'spectral'})
        
        # Sort by time
        merged_onsets.sort(key=lambda x: x['time'])
        
        return merged_onsets