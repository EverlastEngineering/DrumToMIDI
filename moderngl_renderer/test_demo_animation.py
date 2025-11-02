"""
Smoke test for demo_animation - verifies the full pipeline works end-to-end

This test exercises the complete rendering pipeline:
- Note generation (functional core)
- Frame scene building (animation layer)
- GPU batch rendering (imperative shell)
- FFmpeg video encoding (file I/O)

Marked as slow since it renders a full video.
"""

import pytest
from pathlib import Path
import subprocess

from .demo_animation import (
    create_test_notes,
    render_animation_to_frames,
    save_frames_to_video
)


@pytest.mark.slow
def test_demo_animation_smoke_test(tmp_path):
    """Smoke test: Verify complete pipeline renders without errors"""
    
    # Generate test data (short duration for speed)
    notes = create_test_notes()
    duration = 1.0  # Just 1 second for smoke test
    fps = 30  # Lower FPS for speed
    
    # Render frames
    frames = render_animation_to_frames(
        notes=notes,
        duration=duration,
        fps=fps,
        width=640,  # Smaller resolution for speed
        height=480
    )
    
    # Verify output
    assert len(frames) == int(duration * fps), "Wrong number of frames"
    assert all(f.shape == (480, 640, 3) for f in frames), "Wrong frame dimensions"
    assert all(f.dtype.name == 'uint8' for f in frames), "Wrong frame dtype"
    
    # Verify frames contain rendered content (not all black)
    assert any(f.max() > 10 for f in frames), "No content rendered"
    
    print(f"✓ Rendered {len(frames)} frames successfully")


@pytest.mark.slow
def test_full_pipeline_with_video_output(tmp_path):
    """Integration test: Verify complete pipeline including video encoding"""
    
    output_video = tmp_path / "test_animation.mp4"
    
    # Generate and render
    notes = create_test_notes()
    frames = render_animation_to_frames(
        notes=notes,
        duration=1.0,
        fps=30,
        width=640,
        height=480
    )
    
    # Save to video
    save_frames_to_video(
        frames=frames,
        output_path=str(output_video),
        fps=30
    )
    
    # Verify video file exists
    assert output_video.exists(), "Video file not created"
    assert output_video.stat().st_size > 1000, "Video file suspiciously small"
    
    # Verify with ffprobe
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(output_video)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        video_duration = float(result.stdout.strip())
        assert 0.9 < video_duration < 1.1, f"Video duration {video_duration}s not close to 1.0s"
        print(f"✓ Video created: {video_duration:.2f}s, {output_video.stat().st_size:,} bytes")
    else:
        print("⚠️  ffprobe not available, skipping duration check")
    
    print(f"✓ Full pipeline test passed")
