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
from moderngl_renderer.shell import ModernGLContext, render_rectangles, render_rectangles_no_glow, render_circles, render_transparent_rectangles, blit_texture, read_framebuffer, AsyncFramebufferReader
from moderngl_renderer.midi_video_core import (
    midi_note_to_rectangle,
    create_strike_line_rectangle,
    create_lane_markers,
    create_hit_indicator_circles,
    create_kick_hit_indicators,
    create_progress_bar
)
from moderngl_renderer.core import calculate_ending_image_alpha, calculate_image_dimensions_with_aspect_ratio
from moderngl_renderer.text_overlay import create_lane_labels_overlay
from PIL import Image


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
    verbose: bool = True,
    enable_timing: bool = False
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
        enable_timing: Enable detailed performance timing (default False)
        
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
            '-shortest'  # End video when shortest stream (usually MIDI) ends
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
        glow_offset_pixels=0.0,  # Shift glow up by 3 pixels
        enable_timing=enable_timing
    ) as ctx:
            if verbose:
                print("✓ GPU ready, rendering...")
                print()
            
            # Pre-build static elements (rendered once, reused every frame)
            lane_markers = create_lane_markers(num_lanes)
            strike_line = create_strike_line_rectangle()
            
            # Create text overlay for lane labels (render once, upload to GPU)
            if verbose:
                print("Creating lane label overlay...")
            text_overlay_pil = create_lane_labels_overlay(
                width=width,
                height=height,
                drum_map=STANDARD_GM_DRUM_MAP,
                num_lanes=num_lanes,
                drum_notes=drum_notes,  # Filter to only show drums that appear in MIDI
                font_size=int(height * 0.0176)  # 1.76% of screen height (30% bigger)
            )
            # Convert PIL image to bytes and upload as GPU texture
            text_overlay_bytes = text_overlay_pil.tobytes()
            text_texture = ctx.ctx.texture((width, height), 4, text_overlay_bytes)
            text_texture.filter = (ctx.ctx.LINEAR, ctx.ctx.LINEAR)
            
            if verbose:
                print("✓ Text overlay ready")
            
            # Load and prepare ending image (render once, upload to GPU)
            if verbose:
                print("Loading ending image...")
            ending_image_path = Path(__file__).parent / "large_logo3b@2x.png"
            ending_image_original = Image.open(ending_image_path).convert("RGBA")
            
            # Calculate dimensions to maintain aspect ratio with 30% margins
            img_w, img_h, x_offset, y_offset = calculate_image_dimensions_with_aspect_ratio(
                image_width=ending_image_original.width,
                image_height=ending_image_original.height,
                canvas_width=width,
                canvas_height=height,
                margin_percent=0.30
            )
            
            # Create a transparent canvas and paste the scaled image centered
            ending_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            ending_image_scaled = ending_image_original.resize((img_w, img_h), Image.LANCZOS)
            ending_canvas.paste(ending_image_scaled, (x_offset, y_offset))
            
            # Upload to GPU texture
            ending_image_bytes = ending_canvas.tobytes()
            ending_texture = ctx.ctx.texture((width, height), 4, ending_image_bytes)
            ending_texture.filter = (ctx.ctx.LINEAR, ctx.ctx.LINEAR)
            
            if verbose:
                print(f"✓ Ending image ready ({ending_image_original.width}x{ending_image_original.height} → {img_w}x{img_h} with margins)")
                print()
            
            # Initialize async framebuffer reader for better performance
            async_reader = AsyncFramebufferReader(ctx)
            
            for frame_num in range(total_frames):
                frame_start = time.perf_counter() if enable_timing else None
                
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
                
                # Layer 6: Progress bar (top overlay)
                progress = current_time / duration if duration > 0 else 0.0
                progress_bar = create_progress_bar(progress)
                render_rectangles_no_glow(ctx, [progress_bar], time=current_time)
                
                # Layer 7: Text overlay (lane labels, static texture blit with fade)
                # Fade out after 5 seconds: full opacity 0-5s, fade over 3s (5-8s), invisible after 8s
                if current_time < 5.0:
                    text_alpha = 1.0  # Full opacity
                elif current_time < 8.0:
                    # Linear fade over 3 seconds
                    fade_progress = (current_time - 5.0) / 3.0
                    text_alpha = 1.0 - fade_progress
                else:
                    text_alpha = 0.0  # Fully transparent
                
                if text_alpha > 0.0:
                    blit_texture(ctx, text_texture, alpha=text_alpha)
                
                # Layer 8: Ending image (fade in over 4s, hold for 1s)
                ending_alpha = calculate_ending_image_alpha(
                    current_time=current_time,
                    duration=duration,
                    fade_duration=4.0,
                    hold_duration=1.0
)
                if ending_alpha > 0.0:
                    blit_texture(ctx, ending_texture, alpha=ending_alpha)
                
                # === Async PBO Pipeline ===
                # Start async read of current frame (frame N) to PBO
                async_reader.start_read()
                
                # Get previous frame (frame N-1) from PBO and write to FFmpeg
                # This overlaps GPU→CPU transfer of frame N with encoding of frame N-1
                frame = async_reader.get_previous_frame()
                
                # Write frame N-1 to FFmpeg (if available, skips first frame)
                if frame is not None:
                    try:
                        process.stdin.write(frame.tobytes())
                    except BrokenPipeError:
                        # FFmpeg process died
                        stderr_output = process.stderr.read().decode('utf-8') if process.stderr else ''
                        raise RuntimeError(f"FFmpeg pipe broken. FFmpeg error: {stderr_output[-500:]}")
                    
                    frames_rendered += 1
                
                # Swap PBOs for next iteration
                async_reader.swap_buffers()
                
                if enable_timing and frame_start is not None:
                    frame_time = time.perf_counter() - frame_start
                    if ctx.timings:
                        ctx.timings.record('full_frame', frame_time)
                
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
            
            # Write the final frame (still in current PBO)
            final_frame = async_reader.finalize()
            try:
                process.stdin.write(final_frame.tobytes())
                frames_rendered += 1
            except BrokenPipeError:
                # FFmpeg process died
                stderr_output = process.stderr.read().decode('utf-8') if process.stderr else ''
                raise RuntimeError(f"FFmpeg pipe broken. FFmpeg error: {stderr_output[-500:]}")
            
            # Cleanup PBO resources
            async_reader.cleanup()
            
            # Print timing summary if enabled
            if enable_timing:
                ctx.print_timing_summary("ModernGL Render Performance (with PBO Async)")
    
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
