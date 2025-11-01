#!/usr/bin/env python3
"""
Animated Falling Notes Demo

Creates a short video demonstrating the animation system.
Uses test note data to show GPU-accelerated rendering in action.
"""

import numpy as np
from pathlib import Path
from moderngl_shell import render_frames_to_array, ModernGLContext, render_rectangles, read_framebuffer
from animation_core import (
    build_frame_scene,
    frame_time_from_number,
    total_frames_from_duration,
    calculate_visibility_window
)


def create_test_notes():
    """Create test note sequence"""
    lanes = ['hihat', 'snare', 'kick', 'tom']
    notes = []
    
    # Create a drum pattern
    # Hihat on every beat
    for i in range(8):
        notes.append({
            'time': i * 0.5,
            'lane': 'hihat',
            'velocity': 80 + (i % 2) * 20
        })
    
    # Snare on 2 and 4
    for i in [2, 6]:
        notes.append({
            'time': i * 0.5,
            'lane': 'snare',
            'velocity': 100
        })
    
    # Kick on 1 and 3
    for i in [0, 4]:
        notes.append({
            'time': i * 0.5,
            'lane': 'kick',
            'velocity': 120
        })
    
    # Some tom fills
    for i in [3, 7]:
        notes.append({
            'time': i * 0.5,
            'lane': 'tom',
            'velocity': 90
        })
    
    return sorted(notes, key=lambda n: n['time'])


def render_animation_to_frames(
    notes,
    duration=5.0,
    fps=60,
    width=1920,
    height=1080
):
    """Render animation to frame array"""
    
    lanes = ['hihat', 'snare', 'kick', 'tom']
    total_frames = total_frames_from_duration(duration, fps)
    
    print(f"\nRendering {total_frames} frames @ {fps} FPS...")
    print(f"Duration: {duration}s")
    print(f"Notes: {len(notes)}")
    
    # Calculate visibility window (add note height buffer so notes appear from above screen)
    note_height = 0.06
    lookahead, lookbehind = calculate_visibility_window(
        strike_line_y=-0.6,
        screen_top=1.0 + note_height,  # Start notes with bottom edge at screen top
        screen_bottom=-1.0,
        fall_speed=1.0
    )
    
    print(f"Visibility window: +{lookahead:.1f}s / -{lookbehind:.1f}s")
    
    # Generate frame scenes
    print("Generating frame data...")
    frame_scenes = []
    
    for frame_num in range(total_frames):
        current_time = frame_time_from_number(frame_num, fps)
        
        # Filter notes visible at this time
        visible_notes = [
            note for note in notes
            if (note['time'] - current_time) <= lookahead
            and (note['time'] - current_time) >= -lookbehind
        ]
        
        # Build scene
        scene = build_frame_scene(
            notes=visible_notes,
            current_time=current_time,
            lanes=lanes,
            strike_line_y=-0.6,
            fall_speed=1.0,
            screen_bottom=-1.0
        )
        
        frame_scenes.append(scene)
        
        if (frame_num + 1) % 60 == 0:
            print(f"  Generated frame {frame_num + 1}/{total_frames}")
    
    # Render all frames on GPU
    print(f"\nRendering to GPU...")
    import time
    start = time.perf_counter()
    
    frames = render_frames_to_array(
        frames=frame_scenes,
        width=width,
        height=height,
        corner_radius=12.0
    )
    
    end = time.perf_counter()
    elapsed = end - start
    fps_achieved = total_frames / elapsed
    
    print(f"\n✓ Rendering complete!")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  FPS: {fps_achieved:.1f}")
    print(f"  Speedup vs PIL: ~{fps_achieved/40:.1f}x")
    
    return frames


def save_sample_frames(frames, output_dir="animation_samples"):
    """Save sample frames for inspection"""
    
    from PIL import Image
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save first, middle, and last frames
    sample_indices = [0, len(frames) // 2, len(frames) - 1]
    
    print(f"\nSaving sample frames to {output_dir}/...")
    for idx in sample_indices:
        img = Image.fromarray(frames[idx], 'RGB')
        filename = output_path / f"frame_{idx:04d}.png"
        img.save(filename)
        print(f"  Saved {filename}")


def create_video(frames, output_file="animation_demo.mp4", fps=60):
    """Create video from frames using FFmpeg"""
    
    import subprocess
    
    height, width = frames[0].shape[:2]
    
    print(f"\nCreating video: {output_file}")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")
    print(f"  Frames: {len(frames)}")
    
    # FFmpeg command
    cmd = [
        'ffmpeg',
        '-y',  # Overwrite
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{width}x{height}',
        '-pix_fmt', 'rgb24',
        '-r', str(fps),
        '-i', '-',  # stdin
        '-an',  # no audio
        '-vcodec', 'libx264',
        '-crf', '18',  # High quality
        '-preset', 'medium',
        '-pix_fmt', 'yuv420p',
        output_file
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Write frames
        for frame in frames:
            process.stdin.write(frame.tobytes())
        
        process.stdin.close()
        process.wait()
        
        if process.returncode == 0:
            print(f"✓ Video created successfully!")
            return True
        else:
            print(f"✗ FFmpeg error:")
            print(process.stderr.read().decode())
            return False
            
    except FileNotFoundError:
        print("✗ FFmpeg not found. Install with: brew install ffmpeg")
        return False


def main():
    """Create animated demo"""
    
    print("="*60)
    print("Animated Falling Notes Demo - Phase 3")
    print("="*60)
    
    # Create test notes
    notes = create_test_notes()
    
    # Render animation
    frames = render_animation_to_frames(
        notes=notes,
        duration=5.0,
        fps=60,
        width=1920,
        height=1080
    )
    
    # Save samples
    save_sample_frames(frames)
    
    # Create video
    video_created = create_video(frames, output_file="animation_demo.mp4", fps=60)
    
    print("\n" + "="*60)
    if video_created:
        print("SUCCESS! Animation demo complete!")
        print(f"  • Watch: animation_demo.mp4")
        print(f"  • Samples: animation_samples/")
    else:
        print("Animation frames rendered successfully!")
        print("  • Samples: animation_samples/")
        print("  • Install ffmpeg to create video")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
