"""
Sidechain Compression - Functional Core

Pure audio processing functions for envelope following and sidechain compression.
No side effects: no printing, no file I/O, no logging.

Architecture: Functional core (this file) called by imperative shell (sidechain_shell.py)
"""

import numpy as np  # type: ignore
from typing import Tuple


def envelope_follower(
    audio: np.ndarray,
    sr: int,
    attack_ms: float = 5.0,
    release_ms: float = 50.0
) -> np.ndarray:
    """
    Create an envelope follower for the audio signal.
    
    Pure function - no side effects. Takes audio and parameters, returns envelope.
    
    Args:
        audio: Input audio (mono or stereo). If stereo, will be converted to mono.
        sr: Sample rate in Hz
        attack_ms: Attack time in milliseconds (how quickly envelope rises)
        release_ms: Release time in milliseconds (how quickly envelope falls)
    
    Returns:
        Envelope of the audio signal as 1D numpy array (mono)
    
    Examples:
        >>> audio = np.array([0.1, 0.5, 0.3, 0.1])
        >>> envelope = envelope_follower(audio, sr=44100, attack_ms=5.0, release_ms=50.0)
        >>> envelope.shape
        (4,)
    """
    # Convert to mono if stereo
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)
    
    # Handle empty array
    if len(audio) == 0:
        return np.array([])
    
    # Get absolute values (rectify)
    rectified = np.abs(audio)
    
    # Calculate coefficients for exponential smoothing
    attack_coef = np.exp(-1.0 / (sr * attack_ms / 1000.0))
    release_coef = np.exp(-1.0 / (sr * release_ms / 1000.0))
    
    # Apply envelope follower with separate attack/release
    envelope = np.zeros_like(rectified)
    envelope[0] = rectified[0]
    
    for i in range(1, len(rectified)):
        if rectified[i] > envelope[i-1]:
            # Attack phase - signal increasing
            envelope[i] = attack_coef * envelope[i-1] + (1 - attack_coef) * rectified[i]
        else:
            # Release phase - signal decreasing
            envelope[i] = release_coef * envelope[i-1] + (1 - release_coef) * rectified[i]
    
    return envelope


def calculate_gain_reduction_db(
    sidechain_db: np.ndarray,
    threshold_db: float,
    ratio: float,
    knee_db: float
) -> np.ndarray:
    """
    Calculate gain reduction curve for compression.
    
    Pure function implementing compression curve with soft knee.
    
    Args:
        sidechain_db: Sidechain signal level in dB
        threshold_db: Compression threshold in dB
        ratio: Compression ratio (e.g., 10.0 for 10:1)
        knee_db: Soft knee width in dB (smooth transition at threshold)
    
    Returns:
        Gain reduction in dB (always <= 0)
    
    Notes:
        - Above threshold + knee: Full compression
        - Within knee range: Smooth transition (quadratic curve)
        - Below threshold - knee: No compression
    """
    gain_reduction_db = np.zeros_like(sidechain_db)
    
    for i in range(len(sidechain_db)):
        if sidechain_db[i] > threshold_db + knee_db:
            # Above knee - full compression
            over_threshold = sidechain_db[i] - threshold_db
            gain_reduction_db[i] = -over_threshold * (1 - 1/ratio)
        elif sidechain_db[i] > threshold_db - knee_db:
            # In knee - soft compression (quadratic curve for smooth transition)
            over_threshold = sidechain_db[i] - threshold_db + knee_db
            gain_reduction_db[i] = -over_threshold**2 * (1 - 1/ratio) / (4 * knee_db)
        # else: below threshold, no gain reduction (already zero)
    
    return gain_reduction_db


def sidechain_compress(
    main_audio: np.ndarray,
    sidechain_audio: np.ndarray,
    sr: int,
    threshold_db: float = -30.0,
    ratio: float = 10.0,
    attack_ms: float = 1.0,
    release_ms: float = 100.0,
    makeup_gain_db: float = 0.0,
    knee_db: float = 3.0
) -> Tuple[np.ndarray, dict]:
    """
    Apply sidechain compression to main audio based on sidechain audio.
    
    Pure function - no side effects. Returns compressed audio and processing stats.
    
    Typical use case: Reduce snare bleed from kick track by using snare as sidechain trigger.
    
    Args:
        main_audio: Audio to be compressed (e.g., kick track). Shape: (samples,) or (samples, 2)
        sidechain_audio: Audio that triggers compression (e.g., snare track). Shape: (samples,) or (samples, 2)
        sr: Sample rate in Hz
        threshold_db: Threshold in dB below which no compression occurs
        ratio: Compression ratio (higher = more aggressive ducking). E.g., 10.0 = 10:1
        attack_ms: How quickly compression kicks in when sidechain hits (milliseconds)
        release_ms: How quickly compression releases after sidechain stops (milliseconds)
        makeup_gain_db: Gain to apply after compression (dB). Use to restore volume if needed.
        knee_db: Soft knee width in dB (smooth transition around threshold)
    
    Returns:
        Tuple of:
        - compressed: Compressed audio with same shape as main_audio
        - stats: Dictionary with processing statistics
            - max_gain_reduction_db: Maximum gain reduction applied
            - avg_gain_reduction_db: Average gain reduction
            - samples_compressed: Number of samples where gain reduction occurred
    
    Examples:
        >>> kick = np.random.randn(44100)  # 1 second of kick
        >>> snare = np.random.randn(44100)  # 1 second of snare
        >>> compressed, stats = sidechain_compress(kick, snare, sr=44100)
        >>> compressed.shape
        (44100,)
        >>> 'max_gain_reduction_db' in stats
        True
    """
    # Handle empty arrays
    if len(main_audio) == 0:
        return np.array([]), {
            'max_gain_reduction_db': 0.0,
            'avg_gain_reduction_db': 0.0,
            'samples_compressed': 0,
            'compression_percentage': 0.0
        }
    
    # Get envelope of sidechain (e.g., snare triggers compression)
    sidechain_envelope = envelope_follower(sidechain_audio, sr, attack_ms, release_ms)
    
    # Convert envelope to dB
    epsilon = 1e-10  # Prevent log(0)
    sidechain_db = 20 * np.log10(sidechain_envelope + epsilon)
    
    # Calculate gain reduction using compression curve
    gain_reduction_db = calculate_gain_reduction_db(
        sidechain_db,
        threshold_db,
        ratio,
        knee_db
    )
    
    # Convert gain reduction to linear scale
    gain_linear = 10 ** (gain_reduction_db / 20.0)
    
    # Apply makeup gain (compensate for volume loss from compression)
    makeup_gain_linear = 10 ** (makeup_gain_db / 20.0)
    gain_linear *= makeup_gain_linear
    
    # Apply gain reduction to main audio
    if main_audio.ndim == 2:
        # Stereo - apply same gain to both channels
        compressed = main_audio * gain_linear[:, np.newaxis]
    else:
        # Mono - direct multiplication
        compressed = main_audio * gain_linear
    
    # Calculate statistics for reporting
    samples_compressed = np.sum(gain_reduction_db < 0)
    stats = {
        'max_gain_reduction_db': float(np.min(gain_reduction_db)),  # Most negative value
        'avg_gain_reduction_db': float(np.mean(gain_reduction_db[gain_reduction_db < 0])) if samples_compressed > 0 else 0.0,
        'samples_compressed': int(samples_compressed),
        'compression_percentage': float(samples_compressed / len(gain_reduction_db) * 100)
    }
    
    return compressed, stats
