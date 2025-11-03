"""
Demo: Render MIDI notes to video using ModernGL

Demonstrates the complete pipeline:
1. Create test DrumNotes
2. Use midi_bridge to generate frames
3. Save as video (or images for inspection)
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from midi_types import DrumNote
from moderngl_renderer.midi_bridge_shell import render_midi_to_frames
from moderngl_renderer.shell import ModernGLContext
import numpy as np


def create_test_drum_pattern():
    """Create a simple 4-beat drum pattern
    
    Returns:
        List[DrumNote]: Test drum sequence
    """
    notes = []
    
    # Define drum kit
    kick_drum = (36, -1, (255, 100, 100), "Kick")      # lane=-1 for full-width bar
    snare_drum = (38, 0, (100, 255, 100), "Snare")    # lane=0
    hihat_closed = (42, 1, (100, 100, 255), "HH Closed")  # lane=1
    hihat_open = (46, 2, (150, 150, 255), "HH Open")     # lane=2
    
    # 4 beats, 120 BPM = 0.5 seconds per beat
    beat_duration = 0.5
    
    for beat in range(4):
        t = beat * beat_duration
        
        # Kick on beats 1 and 3
        if beat in [0, 2]:
            midi_note, lane, color, name = kick_drum
            notes.append(DrumNote(midi_note, t, 100, lane, color, name))
        
        # Snare on beats 2 and 4
        if beat in [1, 3]:
            midi_note, lane, color, name = snare_drum
            notes.append(DrumNote(midi_note, t, 90, lane, color, name))
        
        # Hi-hat on every beat (alternating closed/open)
        if beat % 2 == 0:
            midi_note, lane, color, name = hihat_closed
            notes.append(DrumNote(midi_note, t, 80, lane, color, name))
        else:
            midi_note, lane, color, name = hihat_open
            notes.append(DrumNote(midi_note, t, 70, lane, color, name))
        
        # Hi-hat 8th notes (halfway between beats)
        t_eighth = t + beat_duration / 2
        midi_note, lane, color, name = hihat_closed
        notes.append(DrumNote(midi_note, t_eighth, 60, lane, color, name))
    
    return notes


def save_frame_as_image(frame: np.ndarray, filepath: str):
    """Save a frame as PNG image
    
    Args:
        frame: RGB numpy array (height, width, 3)
        filepath: Output path for PNG
    """
    from PIL import Image
    img = Image.fromarray(frame)
    img.save(filepath)
    print(f"Saved frame to {filepath}")


def main():
    """Run the demo"""
    print("ModernGL MIDI Renderer Demo")
    print("=" * 50)
    
    # Create test pattern
    print("\n1. Creating test drum pattern...")
    notes = create_test_drum_pattern()
    print(f"   Created {len(notes)} notes")
    
    # Generate frames
    print("\n2. Rendering frames...")
    frames = list(render_midi_to_frames(
        notes,
        width=1920,
        height=1080,
        fps=60,
        duration=3.0,  # 3 seconds total (includes tail time)
        corner_radius=12.0,
        blur_radius=5.0,
        glow_strength=0.5,
        fall_speed_multiplier=1.0,
        clear_color=(0.0, 0.0, 0.0)  # Black background
    ))
    print(f"   Generated {len(frames)} frames")
    
    # Save sample frames
    print("\n3. Saving sample frames...")
    output_dir = Path("moderngl_renderer/test_artifacts/midi_demo")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save frames at interesting times
    frame_indices = [
        0,      # Start (no notes visible yet)
        30,     # 0.5s - first beat
        90,     # 1.5s - third beat
        150,    # 2.5s - notes falling
        179     # Last frame
    ]
    
    for idx in frame_indices:
        if idx < len(frames):
            time = idx / 60.0
            filepath = output_dir / f"frame_{idx:04d}_t{time:.2f}s.png"
            save_frame_as_image(frames[idx], str(filepath))
    
    print(f"\n✓ Demo complete! Check {output_dir} for output images.")
    print("\nNext steps:")
    print("  - Add circle rendering for strike line highlights")
    print("  - Add FFmpeg video encoding")
    print("  - Extract MIDI parsing from render_midi_to_video.py")


if __name__ == "__main__":
    main()
