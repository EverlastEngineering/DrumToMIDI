"""
Tests for FFmpeg Encoder

Tests the imperative shell that handles video encoding via FFmpeg.
Uses smoke tests to verify FFmpeg integration works.
"""

import pytest
import numpy as np
from pathlib import Path
import subprocess

from .ffmpeg_encoder import FFmpegEncoder, encode_frames_to_video


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_output(tmp_path):
    """Temporary output file path"""
    return str(tmp_path / "test_output.mp4")


@pytest.fixture
def test_frames():
    """Generate simple test frames"""
    def _make_frames(count=10, width=320, height=240):
        """Create test frames with varying colors"""
        for i in range(count):
            # Create a frame with a color gradient
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            intensity = int(255 * (i / count))
            frame[:, :] = [intensity, 128, 255 - intensity]
            yield frame
    return _make_frames


@pytest.fixture
def check_ffmpeg():
    """Skip test if FFmpeg is not installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL,
                      check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("FFmpeg not installed")


# ============================================================================
# Smoke Tests
# ============================================================================

def test_encoder_context_manager(temp_output, test_frames, check_ffmpeg):
    """Smoke test: Encoder context manager should work"""
    with FFmpegEncoder(
        output_path=temp_output,
        width=320,
        height=240,
        fps=30,
        verbose=False
    ) as encoder:
        for frame in test_frames(count=10):
            encoder.write_frame(frame)
    
    # Output file should exist
    assert Path(temp_output).exists()
    assert Path(temp_output).stat().st_size > 0


def test_encode_frames_convenience_function(temp_output, test_frames, check_ffmpeg):
    """Smoke test: Convenience function should work"""
    success = encode_frames_to_video(
        frames=test_frames(count=10),
        output_path=temp_output,
        width=320,
        height=240,
        fps=30,
        verbose=False
    )
    
    assert success
    assert Path(temp_output).exists()


def test_encoder_manual_lifecycle(temp_output, test_frames, check_ffmpeg):
    """Smoke test: Manual start/write/finish should work"""
    encoder = FFmpegEncoder(
        output_path=temp_output,
        width=320,
        height=240,
        fps=30,
        verbose=False
    )
    
    encoder.start()
    
    for frame in test_frames(count=10):
        encoder.write_frame(frame)
    
    success, stderr = encoder.finish()
    
    assert success
    assert Path(temp_output).exists()


def test_different_resolutions(tmp_path, check_ffmpeg):
    """Property test: Different resolutions should encode correctly"""
    resolutions = [(640, 480), (1280, 720), (1920, 1080)]
    
    for width, height in resolutions:
        output_path = str(tmp_path / f"test_{width}x{height}.mp4")
        
        # Generate frames
        def frames():
            for i in range(5):
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:, :] = [i * 50, 128, 255 - i * 50]
                yield frame
        
        success = encode_frames_to_video(
            frames=frames(),
            output_path=output_path,
            width=width,
            height=height,
            fps=30,
            verbose=False
        )
        
        assert success
        assert Path(output_path).exists()


def test_different_fps_values(tmp_path, check_ffmpeg):
    """Property test: Different FPS values should work"""
    fps_values = [24, 30, 60]
    
    for fps in fps_values:
        output_path = str(tmp_path / f"test_{fps}fps.mp4")
        
        def frames():
            for i in range(10):
                frame = np.zeros((240, 320, 3), dtype=np.uint8)
                frame[:, :] = [100, 150, 200]
                yield frame
        
        success = encode_frames_to_video(
            frames=frames(),
            output_path=output_path,
            width=320,
            height=240,
            fps=fps,
            verbose=False
        )
        
        assert success


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_encoder_not_started_error(temp_output):
    """Error handling: Writing without starting should raise error"""
    encoder = FFmpegEncoder(
        output_path=temp_output,
        width=320,
        height=240,
        fps=30,
        verbose=False
    )
    
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    
    with pytest.raises(RuntimeError, match="not started"):
        encoder.write_frame(frame)


def test_wrong_frame_shape_error(temp_output, check_ffmpeg):
    """Error handling: Wrong frame shape should raise error"""
    with FFmpegEncoder(
        output_path=temp_output,
        width=320,
        height=240,
        fps=30,
        verbose=False
    ) as encoder:
        # Wrong shape
        wrong_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with pytest.raises(ValueError, match="shape mismatch"):
            encoder.write_frame(wrong_frame)


def test_wrong_frame_dtype_error(temp_output, check_ffmpeg):
    """Error handling: Wrong frame dtype should raise error"""
    with FFmpegEncoder(
        output_path=temp_output,
        width=320,
        height=240,
        fps=30,
        verbose=False
    ) as encoder:
        # Wrong dtype
        wrong_frame = np.zeros((240, 320, 3), dtype=np.float32)
        
        with pytest.raises(ValueError, match="dtype must be uint8"):
            encoder.write_frame(wrong_frame)


def test_double_start_error(temp_output, check_ffmpeg):
    """Error handling: Starting twice should raise error"""
    encoder = FFmpegEncoder(
        output_path=temp_output,
        width=320,
        height=240,
        fps=30,
        verbose=False
    )
    
    encoder.start()
    
    with pytest.raises(RuntimeError, match="already started"):
        encoder.start()
    
    encoder.finish()


def test_missing_audio_file_error(temp_output, check_ffmpeg):
    """Error handling: Missing audio file should raise error"""
    with pytest.raises(FileNotFoundError, match="Audio file not found"):
        encoder = FFmpegEncoder(
            output_path=temp_output,
            width=320,
            height=240,
            fps=30,
            audio_path="/nonexistent/audio.mp3",
            verbose=False
        )
        encoder.start()


# ============================================================================
# Command Building Tests (Pure Function)
# ============================================================================

def test_build_command_without_audio(temp_output):
    """Pure function test: Command building without audio"""
    encoder = FFmpegEncoder(
        output_path=temp_output,
        width=1920,
        height=1080,
        fps=60,
        preset="fast",
        crf=20,
        verbose=False
    )
    
    cmd = encoder._build_ffmpeg_command()
    
    # Check key components
    assert 'ffmpeg' in cmd
    assert '-s' in cmd
    assert '1920x1080' in cmd
    assert '-r' in cmd
    assert '60' in cmd
    assert '-preset' in cmd
    assert 'fast' in cmd
    assert '-crf' in cmd
    assert '20' in cmd
    assert '-an' in cmd  # No audio
    assert temp_output in cmd


def test_frames_written_counter(temp_output, test_frames, check_ffmpeg):
    """Property test: Frame counter should track writes"""
    encoder = FFmpegEncoder(
        output_path=temp_output,
        width=320,
        height=240,
        fps=30,
        verbose=False
    )
    
    assert encoder.frames_written == 0
    
    encoder.start()
    
    frame_count = 15
    for frame in test_frames(count=frame_count):
        encoder.write_frame(frame)
    
    assert encoder.frames_written == frame_count
    
    encoder.finish()
    
    # Counter should reset after finish
    assert encoder.frames_written == 0
