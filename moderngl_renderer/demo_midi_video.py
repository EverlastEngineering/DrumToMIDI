"""
MIDI Video Renderer Demo - Project 13

Renders a complete video from project 13 MIDI file using ModernGL.
This is Phase 1 complete - working MIDI to video pipeline.
"""

import sys
from pathlib import Path
import numpy as np
import subprocess
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from midi_shell import parse_midi_file
from midi_types import STANDARD_GM_DRUM_MAP
from moderngl_renderer.midi_animation import (
    convert_drum_notes_to_animation,
    get_visible_notes_at_time,
    calculate_note_y_at_time
)
from moderngl_renderer.shell import ModernGLContext, render_rectangles, read_framebuffer


def midi_note_to_rectangle(anim_note, current_time, strike_line_y=-0.6):
    """Convert MidiAnimationNote to rectangle format for shell.py
    
    Note: shell.py expects 'y' to be the TOP-LEFT corner in OpenGL coords
    (higher Y = top of screen), and it will convert to bottom-left internally.
    """
    y_center = calculate_note_y_at_time(anim_note, current_time, strike_line_y)
    
    # Base brightness from velocity
    base_brightness = 0.3 + (anim_note.velocity / 127.0) * 0.7
    
    # Fade out after passing strike line
    # Calculate fade based on distance past strike line
    if y_center < strike_line_y:
        # Note has passed strike line (y_center is below/less than strike_line_y)
        # In OpenGL: lower Y = further down screen
        distance_past_strike = strike_line_y - y_center  # positive value
        
        # Fade over a distance (e.g., 0.3 normalized units = ~15% of screen)
        fade_distance = 0.3
        fade_factor = 1.0 - min(distance_past_strike / fade_distance, 1.0)
        
        # Apply fade to brightness
        brightness = base_brightness * fade_factor
    else:
        # Note hasn't reached strike line yet
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


def add_strike_line_rectangle(strike_line_y=-0.6, thickness=0.01):
    """Create strike line rectangle"""
    return {
        'x': -1.0,
        'y': strike_line_y - thickness / 2.0,
        'width': 2.0,
        'height': thickness,
        'color': (1.0, 1.0, 1.0)  # White
    }


def add_lane_markers(num_lanes=3):
    """Create vertical lane marker rectangles"""
    markers = []
    lane_width = 2.0 / num_lanes
    
    for i in range(num_lanes + 1):
        x = -1.0 + i * lane_width
        markers.append({
            'x': x - 0.005,
            'y': 1.0,  # Top of screen (will be converted to bottom-left internally)
            'width': 0.01,
            'height': 2.0,
            'color': (0.3, 0.3, 0.3)  # Dark gray
        })
    
    return markers


def render_midi_to_video(
    midi_path: str,
    output_path: str,
    audio_path: str = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 60
):
    """Render MIDI file to video
    
    Args:
        midi_path: Path to MIDI file
        output_path: Output video path
        audio_path: Optional audio track to include
        width: Video width
        height: Video height
        fps: Frames per second
    """
    print("=" * 60)
    print(f"Rendering MIDI to Video")
    print("=" * 60)
    print(f"MIDI: {midi_path}")
    print(f"Output: {output_path}")
    print(f"Resolution: {width}x{height} @ {fps} FPS")
    print()
    
    # Parse MIDI
    print("Loading MIDI...")
    drum_notes, duration = parse_midi_file(
        midi_path=midi_path,
        drum_map=STANDARD_GM_DRUM_MAP,
        tail_duration=3.0
    )
    print(f"✓ {len(drum_notes)} notes, duration {duration:.2f}s")
    
    # Convert to animation format
    print("Converting to animation format...")
    anim_notes = convert_drum_notes_to_animation(drum_notes)
    print(f"✓ {len(anim_notes)} animation notes")
    
    # Count lanes for markers
    lanes = set(n.lane for n in drum_notes if n.lane >= 0)
    num_lanes = len(lanes) if lanes else 3
    print(f"✓ {num_lanes} lanes detected")
    
    # Calculate frame count
    total_frames = int(duration * fps)
    print(f"\nRendering {total_frames} frames...")
    
    # Setup FFmpeg
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
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
    if audio_path and Path(audio_path).exists():
        ffmpeg_cmd.extend(['-i', audio_path])
        ffmpeg_cmd.extend(['-c:a', 'aac', '-b:a', '192k'])
    
    # Output settings
    ffmpeg_cmd.extend([
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '18',
        '-pix_fmt', 'yuv420p',
        str(output_path)
    ])
    
    print(f"Starting FFmpeg...")
    process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Initialize GPU context
    print("Initializing GPU context...")
    start_time = time.time()
    frames_rendered = 0
    last_progress_time = start_time
    
    with ModernGLContext(width, height, corner_radius=8.0) as ctx:
        print("✓ GPU ready, rendering...")
        print()
        
        # Pre-build lane markers (static across all frames)
        lane_markers = add_lane_markers(num_lanes)
        strike_line = add_strike_line_rectangle()
        
        for frame_num in range(total_frames):
            current_time = frame_num / fps
            
            # Build rectangles for this frame
            rectangles = []
            
            # Background elements (static)
            rectangles.extend(lane_markers)
            
            # Notes (dynamic)
            visible = get_visible_notes_at_time(anim_notes, current_time)
            for note in visible:
                rect = midi_note_to_rectangle(note, current_time)
                rectangles.append(rect)
            
            # Foreground elements
            rectangles.append(strike_line)
            
            # Render frame
            ctx.ctx.clear(0.0, 0.0, 0.0)  # Black background
            render_rectangles(ctx, rectangles)
            frame = read_framebuffer(ctx)
            
            # Write to FFmpeg
            process.stdin.write(frame.tobytes())
            
            frames_rendered += 1
            
            # Progress update every second
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
    
    # Close FFmpeg
    process.stdin.close()
    process.wait()
    
    # Final stats
    elapsed = time.time() - start_time
    fps_actual = total_frames / elapsed
    
    print()
    print("=" * 60)
    print("✓ Rendering complete!")
    print("=" * 60)
    print(f"  Time: {elapsed:.2f}s")
    print(f"  FPS: {fps_actual:.1f}")
    print(f"  Speedup vs real-time: {fps_actual / fps:.1f}x")
    print(f"  Output: {output_path}")
    print()
    

def main():
    # Project 13 paths
    midi_path = "user_files/13 - srdrums/midi/srdrums.mid"
    audio_path = "user_files/13 - srdrums/srdrums.wav"
    output_path = "moderngl_renderer/test_artifacts/project13_moderngl.mp4"
    # midi_path = "user_files/1 - The Fate Of Ophelia/midi/The Fate Of Ophelia.mid"
    # audio_path = "user_files/1 - The Fate Of Ophelia/The Fate Of Ophelia.wav"
    # output_path = "moderngl_renderer/test_artifacts/project13_moderngl2.mp4"
    
    render_midi_to_video(
        midi_path=midi_path,
        output_path=output_path,
        audio_path=audio_path,
        width=1920,
        height=1080,
        fps=60
    )


if __name__ == "__main__":
    main()
