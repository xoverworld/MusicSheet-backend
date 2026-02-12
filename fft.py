"""
Fast Fourier Transform Implementation
Used for converting time-domain audio signals to frequency domain
"""

import numpy as np
from scipy import fft as scipy_fft

# Toggle for performance: use scipy's highly optimized FFT (True) or custom implementation (False)
USE_SCIPY_FFT = True


class FFT:
    def __init__(self, size):
        """
        Initialize FFT with given size (must be power of 2)
        
        Args:
            size: FFT size (power of 2)
        """
        self.size = size
        
        # Precompute bit reversal table
        self.reverse_table = self._bit_reverse_table(size)
        
        # Precompute twiddle factors
        self.twiddle_real = np.cos(-np.pi * np.arange(size) / size)
        self.twiddle_imag = np.sin(-np.pi * np.arange(size) / size)
    
    def _bit_reverse_table(self, size):
        """Generate bit reversal table"""
        reverse_table = np.zeros(size, dtype=np.uint32)
        limit = 1
        bit = size >> 1
        
        while limit < size:
            for i in range(limit):
                reverse_table[i + limit] = reverse_table[i] + bit
            limit = limit << 1
            bit = bit >> 1
        
        return reverse_table
    
    def forward(self, input_signal):
        """
        Perform FFT on real-valued input
        
        Args:
            input_signal: Real-valued input array
            
        Returns:
            dict with 'real' and 'imag' arrays
        """
        # Use scipy's optimized FFT if enabled (much faster)
        if USE_SCIPY_FFT:
            # Pad input to FFT size
            signal = np.zeros(self.size, dtype=np.float64)
            input_len = min(len(input_signal), self.size)
            signal[:input_len] = input_signal[:input_len]
            
            # Use scipy's FFT (C-optimized, very fast)
            fft_result = scipy_fft.fft(signal)
            
            return {
                'real': np.real(fft_result),
                'imag': np.imag(fft_result)
            }
        
        # Otherwise use custom implementation
        # Pad input to FFT size
        signal = np.zeros(self.size, dtype=np.float64)
        input_len = min(len(input_signal), self.size)
        signal[:input_len] = input_signal[:input_len]
        
        # Initialize real and imaginary parts
        real = np.zeros(self.size, dtype=np.float64)
        imag = np.zeros(self.size, dtype=np.float64)
        
        # Bit reversal (vectorized)
        real[self.reverse_table] = signal
        
        # Cooley-Tukey FFT
        half_size = 1
        
        while half_size < self.size:
            phase_shift_step_real = self.twiddle_real[half_size]
            phase_shift_step_imag = self.twiddle_imag[half_size]
            
            current_phase_shift_real = 1.0
            current_phase_shift_imag = 0.0
            
            for fft_step in range(half_size):
                i = fft_step
                
                while i < self.size:
                    off = i + half_size
                    
                    tr = (current_phase_shift_real * real[off] - 
                          current_phase_shift_imag * imag[off])
                    ti = (current_phase_shift_real * imag[off] + 
                          current_phase_shift_imag * real[off])
                    
                    real[off] = real[i] - tr
                    imag[off] = imag[i] - ti
                    real[i] += tr
                    imag[i] += ti
                    
                    i += half_size << 1
                
                tmp_real = current_phase_shift_real
                current_phase_shift_real = (tmp_real * phase_shift_step_real - 
                                           current_phase_shift_imag * phase_shift_step_imag)
                current_phase_shift_imag = (tmp_real * phase_shift_step_imag + 
                                           current_phase_shift_imag * phase_shift_step_real)
            
            half_size = half_size << 1
        
        return {'real': real, 'imag': imag}
    
    def magnitude(self, fft_result):
        """
        Calculate magnitude spectrum from FFT result
        
        Args:
            fft_result: Dictionary with 'real' and 'imag' arrays
            
        Returns:
            Magnitude array (first half of spectrum)
        """
        real = fft_result['real']
        imag = fft_result['imag']
        
        magnitude = np.sqrt(real**2 + imag**2)
        
        # Return only first half (positive frequencies)
        return magnitude[:self.size // 2]


def apply_hamming_window(signal):
    """
    Apply Hamming window to reduce spectral leakage
    
    Args:
        signal: Input signal array
        
    Returns:
        Windowed signal
    """
    N = len(signal)
    window = 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(N) / (N - 1))
    return signal * window


def next_power_of_2(n):
    """
    Get next power of 2 for FFT size
    
    Args:
        n: Input number
        
    Returns:
        Next power of 2
    """
    return int(2 ** np.ceil(np.log2(n)))