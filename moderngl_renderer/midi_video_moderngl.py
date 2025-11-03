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
from moderngl_renderer.shell import ModernGLContext, render_rectangles, read_framebuffer


def _midi_note_to_rectangle(
    anim_note: Any,
    current_time: float,
    strike_line_y: float = -0.6
) -> Dict[str, Any]:
    """Convert MidiAnimationNote to rectangle format for rendering
    
    Args:
        anim_note: MidiAnimationNote from midi_animation.py
        current_time: Current playback time in seconds
        strike_line_y: Strike line Y position in normalized coords
    
    Returns:
        Rectangle dict with x, y, width, height, color
        
    Note:
        shell.py expects 'y' to be the TOP-LEFT corner in OpenGL coords
        (higher Y = top of screen), and converts to bottom-left internally.
    """
    y_center = calculate_note_y_at_time(anim_note, current_time, strike_line_y)
    
    # Base brightness from velocity
    base_brightness = 0.3 + (anim_note.velocity / 127.0) * 0.7
    
    # Fade out after passing strike line
    if y_center < strike_line_y:
        # Note has passed strike line (y_center is below strike_line_y)
        # In OpenGL: lower Y = further down screen
        distance_past_strike = strike_line_y - y_center
        
        # Fade over 0.3 normalized units (~15% of screen height)
        fade_distance = 0.3
        fade_factor = 1.0 - min(distance_past_strike / fade_distance, 1.0)
        
        brightness = base_brightness * fade_factor
    else:
        brightness = base_brightness
    
    color = tuple(c * brightness for c in anim_note.color)
    
    # Calculate top-left corner from center position
    # In OpenGL: higher Y = top, so top = center + height/2
    y_top = y_center + anim_note.height / 2.0
    x_left = anim_note.x - anim_note.width / 2.0
    
    return {
        'x': x_left,
        'y': y_top,
        'width': anim_note.width,
        'height': anim_note.height,
        'color': color
    }


def _add_strike_line_rectangle(
    strike_line_y: float = -0.6,
    thickness: float = 0.01
) -> Dict[str, Any]:
    """Create strike line rectangle
    
    Args:
        strike_line_y: Y position in normalized coords
        thickness: Line thickness in normalized coords
    
    Returns:
        Rectangle dict for strike line
    """
    return {
        'x': -1.0,
        'y': strike_line_y - thickness / 2.0,
        'width': 2.0,
        'height': thickness,
        'color': (1.0, 1.0, 1.0)  # White
    }


def _add_lane_markers(num_lanes: int = 3) -> List[Dict[str, Any]]:
    """Create vertical lane marker rectangles
    
    Args:
        num_lanes: Number of lanes (determines marker spacing)
    
    Returns:
        List of rectangle dicts for lane markers
    """
    markers = []
    lane_width = 2.0 / num_lanes
    
    for i in range(num_lanes + 1):
        x = -1.0 + i * lane_width
        markers.append({
            'x': x - 0.005,
            'y': 1.0,  # Top of screen
            'width': 0.01,
            'height': 2.0,
            'color': (0.3, 0.3, 0.3)  # Dark gray
        })
    
    return markers


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
            ffmpeg_cmd.extend(['-c:a', 'aac', '-b:a', '192k'])
        elif verbose:
            print(f"⚠️  Warning: Audio file not found: {audio_path}")
    
    # Output settings
    ffmpeg_cmd.extend([
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '18',
        '-pix_fmt', 'yuv420p',
        str(output_path)
    ])
    
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
        with ModernGLContext(width, height, corner_radius=corner_radius) as ctx:
            if verbose:
                print("✓ GPU ready, rendering...")
                print()
            
            # Pre-build static elements (rendered once, reused every frame)
            lane_markers = _add_lane_markers(num_lanes)
            strike_line = _add_strike_line_rectangle()
            
            for frame_num in range(total_frames):
                current_time = frame_num / fps
                
                # Build rectangles for this frame
                rectangles = []
                
                # Background elements (static)
                rectangles.extend(lane_markers)
                
                # Notes (dynamic - visible notes change each frame)
                visible = get_visible_notes_at_time(anim_notes, current_time)
                for note in visible:
                    rect = _midi_note_to_rectangle(note, current_time)
                    rectangles.append(rect)
                
                # Foreground elements
                rectangles.append(strike_line)
                
                # Render frame
                ctx.ctx.clear(0.0, 0.0, 0.0)  # Black background
                render_rectangles(ctx, rectangles)
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
