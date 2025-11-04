"""
ModernGL MIDI Video Renderer - Imperative Shell

High-performance GPU-accelerated MIDI to video rendering using ModernGL.
Provides the same interface as the PIL renderer but with ~2x real-time speedup.

Architecture:
- Functional core: midi_animation.py (pure functions, coordinate calculations)
- Imperative shell: This file (GPU rendering, FFmpeg encoding, I/O)

Usage:
    from moderngl_renderer.midi_video_moderngl import render_midi_to_video_moderngl
    
    render_midi_to_video_moderngl(
        midi_path="path/to/file.mid",
        output_path="output.mp4",
        audio_path="audio.wav",  # optional
        width=1920,
        height=1080,
        fps=60
    )
"""

from pathlib import Path
import subprocess
import time
from typing import Optional, List, Dict, Any

from midi_shell import parse_midi_file
from midi_types import STANDARD_GM_DRUM_MAP
from moderngl_renderer.midi_animation import (
    convert_drum_notes_to_animation,
    get_visible_notes_at_time,
    calculate_note_y_at_time
)
from moderngl_renderer.shell import ModernGLContext, render_rectangles, render_rectangles_no_glow, render_circles, render_transparent_rectangles, read_framebuffer
from moderngl_renderer.midi_video_core import (
    midi_note_to_rectangle,
    create_strike_line_rectangle,
    create_lane_markers,
    create_hit_indicator_circles,
    create_kick_hit_indicators
)


def render_midi_to_video_moderngl(
    midi_path: str,
    output_path: str,
    audio_path: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 60,
    corner_radius: float = 8.0,
    tail_duration: float = 3.0,
    fall_speed_multiplier: float = 1.0,
    verbose: bool = True
) -> None:
    """Render MIDI file to video using ModernGL GPU acceleration
    
    Args:
        midi_path: Path to MIDI file
        output_path: Output video path (.mp4)
        audio_path: Optional audio track to include
        width: Video width in pixels
        height: Video height in pixels
        fps: Frames per second
        corner_radius: Rounded corner radius for notes (pixels)
        tail_duration: Extra time after last note (seconds)
        fall_speed_multiplier: Speed multiplier for falling notes (1.0 = default, 0.5 = half speed, 2.0 = double speed)
        verbose: Print progress information
        
    Raises:
        FileNotFoundError: If MIDI file not found
        RuntimeError: If rendering fails
        
    Performance:
        Typically achieves 100+ FPS on modern hardware (1.7-2x real-time speedup)
    """
    midi_path = Path(midi_path)
    output_path = Path(output_path)
    
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")
    
    if verbose:
        print("=" * 60)
        print("Rendering MIDI to Video (ModernGL)")
        print("=" * 60)
        print(f"MIDI: {midi_path}")
        print(f"Output: {output_path}")
        print(f"Resolution: {width}x{height} @ {fps} FPS")
        if audio_path:
            print(f"Audio: {audio_path}")
        print()
    
    # Parse MIDI
    if verbose:
        print("Loading MIDI...")
    
    try:
        drum_notes, duration = parse_midi_file(
            midi_path=str(midi_path),
            drum_map=STANDARD_GM_DRUM_MAP,
            tail_duration=tail_duration
        )
    except Exception as e:
        raise RuntimeError(f"Failed to parse MIDI file: {e}")
    
    if verbose:
        print(f"✓ {len(drum_notes)} notes, duration {duration:.2f}s")
    
    # Convert to animation format
    if verbose:
        print("Converting to animation format...")
    
    # Calculate pixels per second with fall speed multiplier
    # Default is 600 pixels/second (height * 0.4 for 1080p at 1.0x speed)
    base_pixels_per_second = height * 0.4
    pixels_per_second = base_pixels_per_second * fall_speed_multiplier
    
    anim_notes = convert_drum_notes_to_animation(
        drum_notes,
        screen_width=width,
        screen_height=height,
        pixels_per_second=pixels_per_second
    )
    
    if verbose:
        print(f"✓ {len(anim_notes)} animation notes")
    
    # Count lanes for markers
    lanes = set(n.lane for n in drum_notes if n.lane >= 0)
    num_lanes = len(lanes) if lanes else 3
    
    if verbose:
        print(f"✓ {num_lanes} lanes detected")
    
    # Calculate frame count
    total_frames = int(duration * fps)
    
    if verbose:
        print(f"\nRendering {total_frames} frames...")
    
    # Setup output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Setup FFmpeg
    ffmpeg_cmd = [
        'ffmpeg',
        '-y',  # Overwrite output
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{width}x{height}',
        '-pix_fmt', 'rgb24',
        '-r', str(fps),
        '-i', '-',  # Read from stdin
    ]
    
    # Add audio if provided
    if audio_path:
        audio_path = Path(audio_path)
        if audio_path.exists():
            ffmpeg_cmd.extend(['-i', str(audio_path)])
        elif verbose:
            print(f"⚠️  Warning: Audio file not found: {audio_path}")
    
    # Output settings - Use VideoToolbox hardware encoder on macOS
    ffmpeg_cmd.extend([
        '-c:v', 'h264_videotoolbox',
        '-b:v', '2M',  # 2 Mbps bitrate (high quality)
        '-pix_fmt', 'yuv420p'
    ])
    
    # Add audio encoding settings if audio is present
    if audio_path and Path(audio_path).exists():
        ffmpeg_cmd.extend([
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest'  # Match video duration
        ])
    
    ffmpeg_cmd.append(str(output_path))
    
    if verbose:
        print("Starting FFmpeg...")
    
    try:
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE if verbose else subprocess.DEVNULL
        )
    except Exception as e:
        raise RuntimeError(f"Failed to start FFmpeg: {e}")
    
    # Initialize GPU context and render
    if verbose:
        print("Initializing GPU context...")
    
    start_time = time.time()
    frames_rendered = 0
    last_progress_time = start_time
    
    try:
        with ModernGLContext(
        width, 
        height, 
        corner_radius=corner_radius,
        blur_radius=8.0,         # More prominent glow
        glow_strength=0.8,       # Stronger glow intensity
        glow_offset_pixels=0.0   # Shift glow up by 3 pixels
    ) as ctx:
            if verbose:
                print("✓ GPU ready, rendering...")
                print()
            
            # Pre-build static elements (rendered once, reused every frame)
            lane_markers = create_lane_markers(num_lanes)
            strike_line = create_strike_line_rectangle()
            
            for frame_num in range(total_frames):
                current_time = frame_num / fps
                
                # Build notes with glow effect
                note_rectangles = []
                visible = get_visible_notes_at_time(anim_notes, current_time)
                for note in visible:
                    # Calculate Y position
                    y_center = calculate_note_y_at_time(note, current_time)
                    
                    # Convert to rectangle using functional core
                    rect = midi_note_to_rectangle(
                        x=note.x,
                        y_center=y_center,
                        width=note.width,
                        height=note.height,
                        color=note.color,
                        velocity=note.velocity,
                        is_kick=note.is_kick
                    )
                    note_rectangles.append(rect)
                
                # Render in layers: background -> lane markers -> notes -> UI
                ctx.ctx.clear(0.0, 0.0, 0.0)  # Black background
                
                # Layer 1: Lane markers (behind everything)
                render_rectangles_no_glow(ctx, lane_markers, time=current_time)
                
                # Layer 2: Notes (including kick drum)
                render_rectangles_no_glow(ctx, note_rectangles, time=current_time)
                
                # Layer 3: Strike line (on top)
                render_rectangles_no_glow(ctx, [strike_line], time=current_time)
                
                # Layer 4: Kick hit indicators (expanding rectangles for kick drum)
                kick_indicators = create_kick_hit_indicators(anim_notes, current_time)
                if kick_indicators:
                    render_transparent_rectangles(ctx, kick_indicators)
                
                # Layer 5: Hit indicator circles (expanding burst effect for regular notes)
                hit_circles = create_hit_indicator_circles(anim_notes, current_time)
                if hit_circles:
                    render_circles(ctx, hit_circles)
                
                frame = read_framebuffer(ctx)
                
                # Write to FFmpeg
                try:
                    process.stdin.write(frame.tobytes())
                except BrokenPipeError:
                    # FFmpeg process died
                    stderr_output = process.stderr.read().decode('utf-8') if process.stderr else ''
                    raise RuntimeError(f"FFmpeg pipe broken. FFmpeg error: {stderr_output[-500:]}")
                
                frames_rendered += 1
                
                # Progress update every second
                if verbose:
                    current_elapsed = time.time()
                    if current_elapsed - last_progress_time >= 1.0:
                        elapsed = current_elapsed - start_time
                        progress_pct = (frame_num / total_frames) * 100
                        fps_actual = frames_rendered / elapsed if elapsed > 0 else 0
                        eta = ((total_frames - frame_num) / fps_actual) if fps_actual > 0 else 0
                        
                        print(f"  Progress: {progress_pct:5.1f}% | "
                              f"Frame {frame_num}/{total_frames} | "
                              f"FPS: {fps_actual:6.1f} | "
                              f"ETA: {eta:5.1f}s")
                        
                        last_progress_time = current_elapsed
    
    except Exception as e:
        # Clean up FFmpeg process
        try:
            process.stdin.close()
            process.terminate()
            process.wait(timeout=5)
        except:
            pass
        raise RuntimeError(f"Rendering failed: {e}")
    
    # Close FFmpeg
    try:
        process.stdin.close()
        return_code = process.wait(timeout=60)
        
        if return_code != 0:
            stderr_output = process.stderr.read().decode('utf-8') if process.stderr else ''
            raise RuntimeError(f"FFmpeg encoding failed (code {return_code}): {stderr_output[-500:]}")
    
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("FFmpeg encoding timed out after 60 seconds")
    
    # Final stats
    elapsed = time.time() - start_time
    fps_actual = total_frames / elapsed if elapsed > 0 else 0
    
    if verbose:
        print()
        print("=" * 60)
        print("✓ Rendering complete!")
        print("=" * 60)
        print(f"  Time: {elapsed:.2f}s")
        print(f"  FPS: {fps_actual:.1f}")
        print(f"  Speedup vs real-time: {fps_actual / fps:.1f}x")
        print(f"  Output: {output_path}")
        print()
