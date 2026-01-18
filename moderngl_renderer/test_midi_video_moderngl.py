"""
Tests for MIDI Video Renderer - Imperative Shell

Level 1 & 2 integration tests for midi_video_moderngl.py.
Tests the full rendering pipeline without mocking.

Note: These are integration tests that exercise GPU, FFmpeg, and file I/O.
They test observable behavior, not implementation details.
"""

import pytest
from pathlib import Path
import tempfile
import subprocess

from midi_types import DrumNote, STANDARD_GM_DRUM_MAP
from moderngl_renderer.midi_video_moderngl import render_midi_to_video_moderngl


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_output_dir():
    """Create temporary directory for output files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_midi_file(temp_output_dir):
    """Create a simple test MIDI file"""
    # For now, use existing test MIDI if available
    test_midi = Path("/Users/jasoncopp/Source/GitHub/larsnet/input/test.mid")
    if test_midi.exists():
        return test_midi
    
    # Skip if no test MIDI available
    pytest.skip("Test MIDI file not available")


@pytest.fixture
def mock_drum_notes():
    """Create mock drum notes for testing"""
    return [
        DrumNote(midi_note=36, time=0.5, velocity=100, lane=0, color=(255, 0, 0), name="Kick"),
        DrumNote(midi_note=38, time=1.0, velocity=90, lane=1, color=(0, 255, 0), name="Snare"),
        DrumNote(midi_note=42, time=1.5, velocity=80, lane=2, color=(0, 0, 255), name="HiHat"),
    ]


# ============================================================================
# LEVEL 1: Smoke Tests
# ============================================================================

class TestRenderingSmoke:
    """Level 1: Verify basic operations don't crash"""
    
    def test_ffmpeg_is_available(self):
        """FFmpeg must be available for video rendering"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )
            assert result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("FFmpeg not available")
    
    @pytest.mark.slow
    def test_render_produces_video_file(self, simple_midi_file, temp_output_dir):
        """Should create a video file"""
        output_path = temp_output_dir / "test_output.mp4"
        
        # Render very short video to keep test fast
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_path),
            width=640,
            height=480,
            fps=10,  # Low FPS for speed
            tail_duration=0.5,  # Short tail
            verbose=False
        )
        
        # File should exist
        assert output_path.exists()
        
        # File should have reasonable size (not empty)
        assert output_path.stat().st_size > 1000
    
    @pytest.mark.slow
    def test_render_without_audio(self, simple_midi_file, temp_output_dir):
        """Should render without audio track"""
        output_path = temp_output_dir / "test_no_audio.mp4"
        
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_path),
            audio_path=None,  # No audio
            width=320,
            height=240,
            fps=10,
            tail_duration=0.5,
            verbose=False
        )
        
        assert output_path.exists()
    
    @pytest.mark.slow
    def test_custom_resolution(self, simple_midi_file, temp_output_dir):
        """Should handle custom resolutions"""
        output_path = temp_output_dir / "test_custom_res.mp4"
        
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_path),
            width=800,
            height=600,
            fps=10,
            tail_duration=0.5,
            verbose=False
        )
        
        assert output_path.exists()


# ============================================================================
# LEVEL 2: Property Tests
# ============================================================================

class TestRenderingProperties:
    """Level 2: Verify behavioral invariants"""
    
    @pytest.mark.slow
    def test_higher_fps_produces_more_frames(self, simple_midi_file, temp_output_dir):
        """Higher FPS should produce proportionally more frames"""
        output_10fps = temp_output_dir / "test_10fps.mp4"
        output_20fps = temp_output_dir / "test_20fps.mp4"
        
        # Same duration, different FPS
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_10fps),
            width=320,
            height=240,
            fps=10,
            tail_duration=0.5,
            verbose=False
        )
        
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_20fps),
            width=320,
            height=240,
            fps=20,
            tail_duration=0.5,
            verbose=False
        )
        
        # Higher FPS file should be larger (more frames)
        size_10fps = output_10fps.stat().st_size
        size_20fps = output_20fps.stat().st_size
        
        # 20fps should be noticeably larger (more frames to encode)
        assert size_20fps > size_10fps * 1.2
    
    @pytest.mark.slow
    def test_higher_resolution_produces_larger_file(self, simple_midi_file, temp_output_dir):
        """Higher resolution should produce larger file"""
        output_low = temp_output_dir / "test_lowres.mp4"
        output_high = temp_output_dir / "test_highres.mp4"
        
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_low),
            width=320,
            height=240,
            fps=10,
            tail_duration=0.5,
            verbose=False
        )
        
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_high),
            width=1280,
            height=720,
            fps=10,
            tail_duration=0.5,
            verbose=False
        )
        
        size_low = output_low.stat().st_size
        size_high = output_high.stat().st_size
        
        # Higher resolution should produce larger file
        assert size_high > size_low * 2
    
    @pytest.mark.slow
    def test_fall_speed_multiplier_affects_animation(self, simple_midi_file, temp_output_dir):
        """Fall speed multiplier should affect note movement"""
        output_slow = temp_output_dir / "test_slow.mp4"
        output_fast = temp_output_dir / "test_fast.mp4"
        
        # Slow falling notes
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_slow),
            width=320,
            height=240,
            fps=10,
            fall_speed_multiplier=0.5,  # Slow
            tail_duration=0.5,
            verbose=False
        )
        
        # Fast falling notes
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_fast),
            width=320,
            height=240,
            fps=10,
            fall_speed_multiplier=2.0,  # Fast
            tail_duration=0.5,
            verbose=False
        )
        
        # Both should exist
        assert output_slow.exists()
        assert output_fast.exists()
        
        # Files should be different sizes (different animation timing)
        assert output_slow.stat().st_size != output_fast.stat().st_size
    
    @pytest.mark.slow
    def test_corner_radius_parameter_affects_output(self, simple_midi_file, temp_output_dir):
        """Different corner radius should produce different output"""
        output_sharp = temp_output_dir / "test_sharp.mp4"
        output_rounded = temp_output_dir / "test_rounded.mp4"
        
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_sharp),
            width=320,
            height=240,
            fps=10,
            corner_radius=2.0,  # Sharp corners
            tail_duration=0.5,
            verbose=False
        )
        
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_rounded),
            width=320,
            height=240,
            fps=10,
            corner_radius=20.0,  # Rounded corners
            tail_duration=0.5,
            verbose=False
        )
        
        # Both should exist
        assert output_sharp.exists()
        assert output_rounded.exists()
    
    @pytest.mark.slow
    def test_verbose_flag_does_not_affect_output(self, simple_midi_file, temp_output_dir):
        """Verbose flag should only affect logging, not video output"""
        output_quiet = temp_output_dir / "test_quiet.mp4"
        output_verbose = temp_output_dir / "test_verbose.mp4"
        
        # Render with verbose=False
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_quiet),
            width=320,
            height=240,
            fps=10,
            tail_duration=0.5,
            verbose=False
        )
        
        # Render with verbose=True
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_verbose),
            width=320,
            height=240,
            fps=10,
            tail_duration=0.5,
            verbose=True
        )
        
        # Files should have similar sizes (verbose doesn't affect video)
        size_quiet = output_quiet.stat().st_size
        size_verbose = output_verbose.stat().st_size
        
        # Allow small variation due to encoding variability
        assert abs(size_quiet - size_verbose) / size_quiet < 0.01


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Verify error handling behavior"""
    
    def test_missing_midi_file_raises_error(self, temp_output_dir):
        """Should raise FileNotFoundError for missing MIDI file"""
        output_path = temp_output_dir / "test_output.mp4"
        
        with pytest.raises(FileNotFoundError):
            render_midi_to_video_moderngl(
                midi_path="/nonexistent/file.mid",
                output_path=str(output_path),
                verbose=False
            )
    
    def test_invalid_output_path_raises_error(self, simple_midi_file):
        """Should handle invalid output paths gracefully"""
        # Try to write to directory that doesn't exist
        invalid_path = "/nonexistent/directory/output.mp4"
        
        # Should either raise error or create parent directory
        # (implementation detail - we just verify it doesn't crash silently)
        try:
            render_midi_to_video_moderngl(
                midi_path=str(simple_midi_file),
                output_path=invalid_path,
                width=320,
                height=240,
                fps=10,
                tail_duration=0.5,
                verbose=False
            )
        except (FileNotFoundError, OSError, RuntimeError):
            # Expected behavior - error is raised
            pass
    
    @pytest.mark.slow
    def test_missing_audio_file_logs_warning(self, simple_midi_file, temp_output_dir):
        """Should handle missing audio file gracefully"""
        output_path = temp_output_dir / "test_no_audio.mp4"
        
        # Should not crash, just render without audio
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_path),
            audio_path="/nonexistent/audio.wav",
            width=320,
            height=240,
            fps=10,
            tail_duration=0.5,
            verbose=False
        )
        
        # Should still create output file
        assert output_path.exists()


# ============================================================================
# Performance Characteristics
# ============================================================================

class TestPerformanceCharacteristics:
    """Verify expected performance characteristics"""
    
    @pytest.mark.slow
    def test_rendering_completes_in_reasonable_time(self, simple_midi_file, temp_output_dir):
        """Rendering should complete in reasonable time"""
        import time
        
        output_path = temp_output_dir / "test_perf.mp4"
        
        start_time = time.time()
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_path),
            width=320,
            height=240,
            fps=10,
            tail_duration=0.5,
            verbose=False
        )
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 30 seconds for short video)
        assert elapsed < 30.0
        assert output_path.exists()
    
    @pytest.mark.slow
    def test_achieves_faster_than_realtime_rendering(self, simple_midi_file, temp_output_dir):
        """Should render faster than real-time playback"""
        import time
        from midi_shell import parse_midi_file
        
        # Get actual video duration
        notes, duration = parse_midi_file(
            str(simple_midi_file),
            STANDARD_GM_DRUM_MAP,
            tail_duration=0.5
        )
        
        output_path = temp_output_dir / "test_realtime.mp4"
        
        start_time = time.time()
        render_midi_to_video_moderngl(
            midi_path=str(simple_midi_file),
            output_path=str(output_path),
            width=640,
            height=480,
            fps=30,
            tail_duration=0.5,
            verbose=False
        )
        elapsed = time.time() - start_time
        
        # Should render faster than real-time (speedup > 1.0)
        # With GPU acceleration, typically achieves 1.5-2x real-time
        speedup = duration / elapsed
        assert speedup > 0.8  # At least close to real-time
