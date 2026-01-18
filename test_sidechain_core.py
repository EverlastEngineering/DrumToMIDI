"""
Unit tests for sidechain_core.py - Functional Core

Tests pure audio processing functions with no side effects.
Aims for 95%+ coverage with fast, deterministic tests.
"""

import pytest
import numpy as np
from sidechain_core import (
    envelope_follower,
    calculate_gain_reduction_db,
    sidechain_compress
)


# ============================================================================
# Tests for envelope_follower()
# ============================================================================

class TestEnvelopeFollower:
    """Tests for pure envelope following function"""
    
    def test_mono_audio_passthrough(self):
        """Mono audio should return envelope of same length"""
        audio = np.array([0.1, 0.5, 0.3, 0.1])
        envelope = envelope_follower(audio, sr=44100)
        assert envelope.shape == (4,)
        assert envelope.dtype == audio.dtype
    
    def test_stereo_audio_converted_to_mono(self):
        """Stereo audio should be averaged and return mono envelope"""
        audio = np.array([[0.1, 0.5], [0.3, 0.7]])  # 2 samples, 2 channels
        envelope = envelope_follower(audio, sr=44100)
        assert envelope.shape == (2,)
        # Should be average of channels: (0.1+0.5)/2=0.3, (0.3+0.7)/2=0.5
        assert np.allclose(envelope[0], 0.3, atol=0.01)
    
    def test_envelope_follows_peaks(self):
        """Envelope should track amplitude peaks"""
        # Sustained signal with peak
        audio = np.zeros(200)
        audio[50:60] = 1.0  # Sustained peak for 10 samples
        envelope = envelope_follower(audio, sr=44100, attack_ms=0.5, release_ms=50.0)
        
        # Envelope should be near zero before peak
        assert envelope[45] < 0.1
        # Envelope should rise during sustained peak
        assert envelope[59] > envelope[50]  # Rising during sustained signal
        # Envelope should decay after peak
        assert envelope[70] < envelope[59]
        assert envelope[80] < envelope[70]
    
    def test_fast_attack_slow_release(self):
        """Fast attack should respond quickly, slow release should decay slowly"""
        # Two impulses
        audio = np.zeros(1000)
        audio[100] = 1.0
        audio[500] = 1.0
        
        fast_attack = envelope_follower(audio, sr=44100, attack_ms=1.0, release_ms=100.0)
        slow_attack = envelope_follower(audio, sr=44100, attack_ms=20.0, release_ms=100.0)
        
        # Fast attack should reach peak more quickly
        assert fast_attack[101] > slow_attack[101]
    
    def test_empty_audio_returns_empty(self):
        """Empty audio should return empty envelope"""
        audio = np.array([])
        envelope = envelope_follower(audio, sr=44100)
        assert len(envelope) == 0
    
    def test_single_sample_audio(self):
        """Single sample should return envelope of length 1"""
        audio = np.array([0.5])
        envelope = envelope_follower(audio, sr=44100)
        assert len(envelope) == 1
        assert envelope[0] == 0.5
    
    def test_negative_values_rectified(self):
        """Envelope should track absolute values (rectification)"""
        audio = np.array([-0.5, 0.5, -0.3, 0.3])
        envelope = envelope_follower(audio, sr=44100, attack_ms=0.1, release_ms=10.0)
        # All values should be positive
        assert np.all(envelope >= 0)
    
    def test_different_sample_rates(self):
        """Function should work with different sample rates"""
        audio = np.random.randn(1000) * 0.5
        
        env_44k = envelope_follower(audio, sr=44100)
        env_48k = envelope_follower(audio, sr=48000)
        
        # Both should return same length
        assert len(env_44k) == len(audio)
        assert len(env_48k) == len(audio)
        # Results will differ slightly due to different time constants
        assert not np.allclose(env_44k, env_48k)


# ============================================================================
# Tests for calculate_gain_reduction_db()
# ============================================================================

class TestCalculateGainReduction:
    """Tests for compression curve calculation"""
    
    def test_below_threshold_no_reduction(self):
        """Signals below threshold should have no gain reduction"""
        sidechain_db = np.array([-50.0, -40.0, -35.0])  # All below -30dB
        gain_reduction = calculate_gain_reduction_db(
            sidechain_db,
            threshold_db=-30.0,
            ratio=10.0,
            knee_db=3.0
        )
        # Should be all zeros (threshold - knee = -33dB, all samples below)
        assert np.allclose(gain_reduction, 0.0)
    
    def test_above_threshold_has_reduction(self):
        """Signals above threshold should have gain reduction"""
        sidechain_db = np.array([-20.0, -10.0, 0.0])  # All above -30dB
        gain_reduction = calculate_gain_reduction_db(
            sidechain_db,
            threshold_db=-30.0,
            ratio=10.0,
            knee_db=3.0
        )
        # All values should be negative (reduction)
        assert np.all(gain_reduction < 0)
    
    def test_higher_ratio_more_reduction(self):
        """Higher compression ratio should produce more gain reduction"""
        sidechain_db = np.array([-20.0, -10.0, 0.0])
        
        ratio_2_reduction = calculate_gain_reduction_db(
            sidechain_db, threshold_db=-30.0, ratio=2.0, knee_db=0.0
        )
        ratio_10_reduction = calculate_gain_reduction_db(
            sidechain_db, threshold_db=-30.0, ratio=10.0, knee_db=0.0
        )
        
        # Higher ratio should reduce more (more negative)
        assert np.all(ratio_10_reduction <= ratio_2_reduction)
    
    def test_soft_knee_smooth_transition(self):
        """Soft knee should create smooth transition at threshold"""
        # Samples around threshold
        sidechain_db = np.linspace(-35.0, -25.0, 100)  # threshold = -30dB
        
        hard_knee = calculate_gain_reduction_db(
            sidechain_db, threshold_db=-30.0, ratio=10.0, knee_db=0.1
        )
        soft_knee = calculate_gain_reduction_db(
            sidechain_db, threshold_db=-30.0, ratio=10.0, knee_db=5.0
        )
        
        # Soft knee should have smoother gradient (less abrupt changes)
        hard_knee_diff = np.diff(hard_knee)
        soft_knee_diff = np.diff(soft_knee)
        
        # Maximum change should be smaller for soft knee
        assert np.max(np.abs(soft_knee_diff)) < np.max(np.abs(hard_knee_diff))
    
    def test_reduction_always_negative_or_zero(self):
        """Gain reduction should never amplify (always <= 0)"""
        sidechain_db = np.linspace(-60.0, 0.0, 1000)
        gain_reduction = calculate_gain_reduction_db(
            sidechain_db, threshold_db=-30.0, ratio=10.0, knee_db=3.0
        )
        assert np.all(gain_reduction <= 0.0)
    
    def test_ratio_of_one_no_compression(self):
        """Ratio of 1.0 should produce no compression"""
        sidechain_db = np.array([-20.0, -10.0, 0.0])
        gain_reduction = calculate_gain_reduction_db(
            sidechain_db, threshold_db=-30.0, ratio=1.0, knee_db=0.0
        )
        # ratio=1.0 means (1 - 1/1.0) = 0, so no reduction
        assert np.allclose(gain_reduction, 0.0)


# ============================================================================
# Tests for sidechain_compress()
# ============================================================================

class TestSidechainCompress:
    """Tests for complete sidechain compression function"""
    
    def test_mono_compression_basic(self):
        """Basic mono compression should work"""
        main = np.ones(1000) * 0.5  # Constant kick
        sidechain = np.zeros(1000)
        sidechain[500:520] = 1.0  # Snare hit
        
        compressed, stats = sidechain_compress(
            main, sidechain, sr=44100,
            threshold_db=-20.0, ratio=10.0
        )
        
        # Output should be same shape as input
        assert compressed.shape == main.shape
        # Stats should be present
        assert 'max_gain_reduction_db' in stats
        assert 'samples_compressed' in stats
        # Some compression should have occurred
        assert stats['samples_compressed'] > 0
    
    def test_stereo_compression_basic(self):
        """Basic stereo compression should work"""
        main = np.ones((1000, 2)) * 0.5  # Stereo kick
        sidechain = np.zeros((1000, 2))
        sidechain[500:520, :] = 1.0  # Stereo snare hit
        
        compressed, stats = sidechain_compress(
            main, sidechain, sr=44100,
            threshold_db=-20.0, ratio=10.0
        )
        
        # Output should maintain stereo shape
        assert compressed.shape == main.shape
        # Both channels should be affected equally
        assert np.allclose(compressed[:, 0], compressed[:, 1])
    
    def test_compression_reduces_amplitude(self):
        """Compression should reduce amplitude when triggered"""
        main = np.ones(1000) * 0.5
        sidechain = np.zeros(1000)
        sidechain[100:200] = 1.0  # Strong trigger
        
        compressed, stats = sidechain_compress(
            main, sidechain, sr=44100,
            threshold_db=-30.0, ratio=10.0, makeup_gain_db=0.0
        )
        
        # Compressed regions should have lower amplitude
        uncompressed_power = np.mean(main[:50] ** 2)
        compressed_power = np.mean(compressed[120:180] ** 2)
        assert compressed_power < uncompressed_power
    
    def test_makeup_gain_increases_output(self):
        """Makeup gain should increase overall output level"""
        main = np.ones(1000) * 0.1
        sidechain = np.zeros(1000)
        
        no_makeup, _ = sidechain_compress(
            main, sidechain, sr=44100, makeup_gain_db=0.0
        )
        with_makeup, _ = sidechain_compress(
            main, sidechain, sr=44100, makeup_gain_db=6.0
        )
        
        # With makeup gain should have higher RMS
        assert np.sqrt(np.mean(with_makeup**2)) > np.sqrt(np.mean(no_makeup**2))
    
    def test_no_sidechain_signal_no_compression(self):
        """Silent sidechain should result in no compression"""
        main = np.ones(1000) * 0.5
        sidechain = np.zeros(1000)  # Silent
        
        compressed, stats = sidechain_compress(
            main, sidechain, sr=44100,
            threshold_db=-30.0, ratio=10.0
        )
        
        # Should be very little compression (sidechain is silent)
        assert stats['compression_percentage'] < 5.0
    
    def test_stats_calculation(self):
        """Statistics should be calculated correctly"""
        main = np.ones(1000) * 0.5
        sidechain = np.zeros(1000)
        sidechain[100:200] = 1.0
        
        compressed, stats = sidechain_compress(
            main, sidechain, sr=44100,
            threshold_db=-20.0, ratio=10.0
        )
        
        # All stat keys should be present
        assert 'max_gain_reduction_db' in stats
        assert 'avg_gain_reduction_db' in stats
        assert 'samples_compressed' in stats
        assert 'compression_percentage' in stats
        
        # Max reduction should be negative
        assert stats['max_gain_reduction_db'] < 0
        # Percentage should be between 0 and 100
        assert 0 <= stats['compression_percentage'] <= 100
    
    def test_attack_release_affect_timing(self):
        """Attack and release times should affect compression timing"""
        main = np.ones(1000) * 0.5
        sidechain = np.zeros(1000)
        sidechain[500:510] = 1.0  # Brief hit
        
        fast_attack, _ = sidechain_compress(
            main, sidechain, sr=44100,
            attack_ms=0.1, release_ms=50.0
        )
        slow_attack, _ = sidechain_compress(
            main, sidechain, sr=44100,
            attack_ms=10.0, release_ms=50.0
        )
        
        # Fast attack should show more immediate reduction
        assert np.mean(fast_attack[500:510]) < np.mean(slow_attack[500:510])
    
    def test_threshold_controls_when_compression_starts(self):
        """Lower threshold should compress more samples"""
        main = np.ones(1000) * 0.5
        sidechain = np.random.randn(1000) * 0.1  # Moderate noise
        
        _, stats_high_thresh = sidechain_compress(
            main, sidechain, sr=44100,
            threshold_db=-10.0, ratio=10.0  # High threshold
        )
        _, stats_low_thresh = sidechain_compress(
            main, sidechain, sr=44100,
            threshold_db=-40.0, ratio=10.0  # Low threshold
        )
        
        # Lower threshold should compress more samples
        assert stats_low_thresh['samples_compressed'] > stats_high_thresh['samples_compressed']
    
    def test_empty_audio_handled(self):
        """Empty audio arrays should be handled gracefully"""
        main = np.array([])
        sidechain = np.array([])
        
        compressed, stats = sidechain_compress(main, sidechain, sr=44100)
        
        assert len(compressed) == 0
        assert stats['samples_compressed'] == 0
    
    def test_deterministic_output(self):
        """Same inputs should produce same outputs (no randomness)"""
        main = np.random.randn(1000) * 0.3
        sidechain = np.random.randn(1000) * 0.2
        
        compressed1, stats1 = sidechain_compress(main, sidechain, sr=44100)
        compressed2, stats2 = sidechain_compress(main, sidechain, sr=44100)
        
        assert np.allclose(compressed1, compressed2)
        assert stats1 == stats2


# ============================================================================
# Integration Tests
# ============================================================================

class TestSidechainIntegration:
    """Integration tests combining multiple functions"""
    
    def test_real_world_kick_snare_scenario(self):
        """Simulate real-world kick cleanup with snare bleed"""
        sr = 44100
        duration = 1.0
        samples = int(sr * duration)
        
        # Create synthetic kick (low freq burst at t=0.2s)
        t = np.linspace(0, duration, samples)
        kick = np.sin(2 * np.pi * 60 * t) * np.exp(-t * 10) * 0.5
        
        # Create synthetic snare bleed in kick track (high freq at t=0.5s)
        snare_bleed = np.sin(2 * np.pi * 2000 * t) * np.exp(-(t - 0.5)**2 * 100) * 0.3
        
        # Main audio = kick + snare bleed
        main = kick + snare_bleed
        
        # Sidechain = isolated snare
        sidechain = snare_bleed * 2  # Stronger signal
        
        # Apply sidechain compression
        compressed, stats = sidechain_compress(
            main, sidechain, sr=sr,
            threshold_db=-30.0, ratio=10.0,
            attack_ms=1.0, release_ms=100.0
        )
        
        # Verify compression occurred
        assert stats['samples_compressed'] > 0
        
        # Verify snare region (around t=0.5s) is reduced
        snare_region_start = int(0.45 * sr)
        snare_region_end = int(0.55 * sr)
        
        main_snare_power = np.mean(main[snare_region_start:snare_region_end] ** 2)
        compressed_snare_power = np.mean(compressed[snare_region_start:snare_region_end] ** 2)
        
        # Compressed version should have less power in snare region
        assert compressed_snare_power < main_snare_power
    
    def test_envelope_to_compression_chain(self):
        """Test that envelope_follower output feeds correctly into compression"""
        audio = np.random.randn(1000) * 0.5
        sr = 44100
        
        # Manual chain
        envelope = envelope_follower(audio, sr, attack_ms=5.0, release_ms=50.0)
        assert len(envelope) == len(audio)
        assert np.all(envelope >= 0)  # Envelope should be positive
        
        # Use in compression
        main = np.ones(1000) * 0.3
        compressed, stats = sidechain_compress(
            main, audio, sr,
            attack_ms=5.0, release_ms=50.0
        )
        
        # Should complete without error
        assert len(compressed) == len(main)
        assert 'max_gain_reduction_db' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
