"""
Pitch Detection using Autocorrelation (YIN algorithm inspired)
and Spectral Peak Analysis
"""

import numpy as np
from fft import FFT, apply_hamming_window, next_power_of_2


class PitchDetector:
    def __init__(self, sample_rate):
        """
        Initialize pitch detector
        
        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.min_frequency = 27.5  # A0 (lowest piano key)
        self.max_frequency = 4186.0  # C8 (highest piano key)
    
    def detect_pitch(self, audio_frame):
        """
        Detect pitch using autocorrelation method
        
        Args:
            audio_frame: Audio samples
            
        Returns:
            dict with 'frequency' and 'confidence', or None
        """
        threshold = 0.1
        
        # Apply windowing
        windowed = apply_hamming_window(audio_frame)
        
        # Calculate autocorrelation
        correlation = self._autocorrelation(windowed)
        
        # Find first minimum
        tau_min = int(self.sample_rate / self.max_frequency)
        tau_max = int(self.sample_rate / self.min_frequency)
        
        # Cumulative mean normalized difference
        cmndf = np.zeros(len(correlation))
        cmndf[0] = 1
        
        running_sum = 0
        for tau in range(1, len(correlation)):
            running_sum += correlation[tau]
            cmndf[tau] = correlation[tau] / (running_sum / tau)
        
        # Find first tau where cmndf drops below threshold
        tau = tau_min
        while tau < tau_max:
            if cmndf[tau] < threshold:
                while tau + 1 < tau_max and cmndf[tau + 1] < cmndf[tau]:
                    tau += 1
                break
            tau += 1
        
        if tau >= tau_max or cmndf[tau] >= threshold:
            return None  # No pitch detected
        
        # Parabolic interpolation for better accuracy
        better_tau = tau
        if tau > 0 and tau < len(cmndf) - 1:
            s0 = cmndf[tau - 1]
            s1 = cmndf[tau]
            s2 = cmndf[tau + 1]
            better_tau = tau + (s2 - s0) / (2 * (2 * s1 - s2 - s0))
        
        frequency = self.sample_rate / better_tau
        confidence = 1 - cmndf[tau]
        
        return {'frequency': frequency, 'confidence': confidence}
    
    def _autocorrelation(self, signal):
        """
        Calculate autocorrelation (optimized with NumPy)
        
        Args:
            signal: Input signal
            
        Returns:
            Autocorrelation array
        """
        size = len(signal)
        result = np.zeros(size)
        
        # Vectorized implementation - much faster!
        for tau in range(size):
            delta = signal[:size-tau] - signal[tau:size]
            result[tau] = np.sum(delta * delta)
        
        return result
    
    def detect_pitch_spectral(self, audio_frame):
        """
        Detect pitch using spectral analysis (FFT-based)
        
        Args:
            audio_frame: Audio samples
            
        Returns:
            dict with 'frequency', 'confidence', and 'harmonics', or None
        """
        fft_size = next_power_of_2(len(audio_frame))
        fft = FFT(fft_size)
        
        windowed = apply_hamming_window(audio_frame)
        fft_result = fft.forward(windowed)
        magnitude = fft.magnitude(fft_result)
        
        # Find peaks in spectrum
        peaks = self._find_spectral_peaks(magnitude)
        
        if len(peaks) == 0:
            return None
        
        # Convert bin to frequency
        def bin_to_freq(bin_idx):
            return bin_idx * self.sample_rate / fft_size
        
        # Get fundamental frequency (lowest significant peak)
        fundamental_bin = peaks[0]['bin']
        frequency = bin_to_freq(fundamental_bin)
        
        # Check if frequency is in piano range
        if frequency < self.min_frequency or frequency > self.max_frequency:
            return None
        
        harmonics = [bin_to_freq(p['bin']) for p in peaks[1:5]]
        
        return {
            'frequency': frequency,
            'confidence': peaks[0]['magnitude'],
            'harmonics': harmonics
        }
    
    def _find_spectral_peaks(self, magnitude):
        """
        Find spectral peaks
        
        Args:
            magnitude: Magnitude spectrum
            
        Returns:
            List of peaks with 'bin' and 'magnitude'
        """
        peaks = []
        threshold = np.max(magnitude) * 0.1  # 10% of max
        
        for i in range(1, len(magnitude) - 1):
            if (magnitude[i] > magnitude[i - 1] and 
                magnitude[i] > magnitude[i + 1] and
                magnitude[i] > threshold):
                peaks.append({'bin': i, 'magnitude': magnitude[i]})
        
        # Sort by magnitude
        peaks.sort(key=lambda x: x['magnitude'], reverse=True)
        
        return peaks
    
    def frequency_to_midi(self, frequency):
        """
        Convert frequency to MIDI note number
        
        Args:
            frequency: Frequency in Hz
            
        Returns:
            MIDI note number
        """
        return round(12 * np.log2(frequency / 440.0) + 69)
    
    def midi_to_note_name(self, midi):
        """
        Convert MIDI note to note name
        
        Args:
            midi: MIDI note number
            
        Returns:
            Note name (e.g., 'C4', 'A#3')
        """
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = int(midi / 12) - 1
        note = note_names[midi % 12]
        return f"{note}{octave}"