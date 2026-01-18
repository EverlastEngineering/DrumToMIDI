"""
Simple test: Render one frame from project 13 MIDI

Loads project 13 MIDI, converts to animation format,
then renders a single frame using shell.py to verify integration.
"""

import sys
from pathlib import Path

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
    
    Args:
        anim_note: MidiAnimationNote from midi_animation.py
        current_time: Current playback time
        strike_line_y: Strike line Y position
    
    Returns:
        Rectangle dict for render_rectangles()
    """
    # Calculate current Y position
    y = calculate_note_y_at_time(anim_note, current_time, strike_line_y)
    
    # Calculate brightness from velocity (0-127 -> 0.3-1.0)
    brightness = 0.3 + (anim_note.velocity / 127.0) * 0.7
    
    # Apply brightness to color
    color = tuple(c * brightness for c in anim_note.color)
    
    return {
        'x': anim_note.x - anim_note.width / 2.0,  # Center on X position
        'y': y - anim_note.height / 2.0,  # Center on Y position
        'width': anim_note.width,
        'height': anim_note.height,
        'color': color
    }


def add_strike_line_rectangle(strike_line_y=-0.6, thickness=0.01):
    """Create a rectangle for the strike line
    
    Args:
        strike_line_y: Y position of strike line (normalized coords)
        thickness: Height of the line (normalized coords)
    
    Returns:
        Rectangle dict for render_rectangles()
    """
    return {
        'x': -1.0,  # Full width
        'y': strike_line_y - thickness / 2.0,  # Center on strike line
        'width': 2.0,  # Full screen width
        'height': thickness,
        'color': (1.0, 1.0, 1.0)  # White line
    }


def add_lane_markers(num_lanes=3):
    """Create rectangles for vertical lane markers
    
    Args:
        num_lanes: Number of lanes
    
    Returns:
        List of rectangle dicts for render_rectangles()
    """
    markers = []
    lane_width = 2.0 / num_lanes
    
    # Add vertical lines between lanes
    for i in range(num_lanes + 1):
        x = -1.0 + i * lane_width
        markers.append({
            'x': x - 0.005,  # 0.01 wide line
            'y': -1.0,
            'width': 0.01,
            'height': 2.0,
            'color': (0.3, 0.3, 0.3)  # Dark gray
        })
    
    return markers


def main():
    print("=" * 60)
    print("Simple MIDI Render Test - Project 13")
    print("=" * 60)
    print()
    
    # Load MIDI
    midi_path = "user_files/13 - srdrums/midi/srdrums.mid"
    print(f"Loading MIDI: {midi_path}")
    
    drum_notes, duration = parse_midi_file(
        midi_path=midi_path,
        drum_map=STANDARD_GM_DRUM_MAP,
        tail_duration=3.0
    )
    
    print(f"✓ Loaded {len(drum_notes)} notes, duration {duration:.2f}s")
    
    # Convert to animation format
    print("Converting to animation format...")
    anim_notes = convert_drum_notes_to_animation(drum_notes)
    print(f"✓ Converted {len(anim_notes)} animation notes")
    
    # Render a frame at 2.0 seconds
    test_time = 2.0
    print(f"\nRendering frame at t={test_time}s")
    
    # Get visible notes
    visible = get_visible_notes_at_time(anim_notes, test_time)
    print(f"  • {len(visible)} notes visible")
    
    # Convert to rectangles
    rectangles = []
    
    # Add lane markers first (background)
    rectangles.extend(add_lane_markers(num_lanes=3))
    
    # Add notes
    for note in visible:
        rect = midi_note_to_rectangle(note, test_time)
        rectangles.append(rect)
    
    # Add strike line last (foreground)
    rectangles.append(add_strike_line_rectangle())
    
    print(f"  • {len(rectangles)} total rectangles (lanes + notes + strike line)")
    
    # Render with ModernGL
    print("\nInitializing GPU context...")
    width, height = 1920, 1080
    
    with ModernGLContext(width, height, corner_radius=8.0) as ctx:
        print("✓ GPU context ready")
        print(f"Rendering {width}x{height} frame...")
        
        # Clear to black
        ctx.ctx.clear(0.0, 0.0, 0.0)
        
        # Render rectangles
        render_rectangles(ctx, rectangles)
        
        # Read back framebuffer
        frame = read_framebuffer(ctx)
        
        print(f"✓ Rendered frame shape: {frame.shape}")
        print(f"  • Data type: {frame.dtype}")
        print(f"  • Value range: {frame.min()} to {frame.max()}")
        
        # Save to file
        from PIL import Image
        output_path = Path("moderngl_renderer/test_artifacts/project13_frame_test.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        img = Image.fromarray(frame)
        img.save(output_path)
        
        print(f"\n✓ Saved frame: {output_path}")
        print()
        print("=" * 60)
        print("✓ Rendering successful!")
        print("=" * 60)
        print()
        print(f"Check the output: {output_path}")


if __name__ == "__main__":
    main()
