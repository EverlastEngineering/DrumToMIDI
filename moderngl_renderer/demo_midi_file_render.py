"""
Demo: Render real MIDI file to video using ModernGL

End-to-end pipeline demonstration:
1. Parse MIDI file → DrumNotes (using midi_parser)
2. Generate video frames (using midi_bridge)
3. Save frames as images or encode to video

This demonstrates the complete integration of all components.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from midi_parser import parse_midi_file
from midi_types import STANDARD_GM_DRUM_MAP
from moderngl_renderer.midi_bridge_shell import render_midi_to_frames


def render_midi_to_images(
    midi_path: str,
    output_dir: str,
    width: int = 1920,
    height: int = 1080,
    fps: int = 60,
    sample_every_n_frames: int = 30
):
    """Render MIDI file to sample PNG images
    
    Args:
        midi_path: Path to MIDI file
        output_dir: Directory to save images
        width: Frame width
        height: Frame height
        fps: Frames per second
        sample_every_n_frames: Save every Nth frame (default 30 = 1 per second at 60fps)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Parsing MIDI file: {midi_path}")
    notes, total_duration = parse_midi_file(
        midi_path,
        drum_map=STANDARD_GM_DRUM_MAP,
        tail_duration=2.0
    )
    print(f"  Found {len(notes)} notes, duration: {total_duration:.2f}s")
    
    print(f"\nRendering frames ({width}x{height} @ {fps}fps)...")
    frame_count = 0
    saved_count = 0
    
    for frame in render_midi_to_frames(
        notes,
        width=width,
        height=height,
        fps=fps,
        duration=total_duration,
        corner_radius=12.0,
        blur_radius=5.0,
        glow_strength=0.5
    ):
        # Save every Nth frame
        if frame_count % sample_every_n_frames == 0:
            from PIL import Image
            time = frame_count / fps
            filename = f"frame_{frame_count:06d}_t{time:.2f}s.png"
            filepath = output_path / filename
            
            img = Image.fromarray(frame)
            img.save(filepath)
            saved_count += 1
            print(f"  Saved: {filename}")
        
        frame_count += 1
    
    print(f"\n✓ Rendered {frame_count} frames, saved {saved_count} samples")
    print(f"  Output directory: {output_dir}")


def main():
    """Run the demo"""
    print("=" * 70)
    print("ModernGL MIDI File Renderer Demo")
    print("=" * 70)
    
    # Find a test MIDI file
    project_root = Path(__file__).parent.parent
    
    # Look for MIDI files in common locations
    midi_candidates = [
        project_root / "input" / "test.mid",
        project_root / "input" / "drums.mid",
        project_root / "separated_stems" / "test.mid",
    ]
    
    # Also search input directory for any .mid files
    input_dir = project_root / "input"
    if input_dir.exists():
        midi_candidates.extend(list(input_dir.glob("*.mid")))
    
    # Find first existing MIDI file
    midi_path = None
    for candidate in midi_candidates:
        if candidate.exists():
            midi_path = str(candidate)
            break
    
    if not midi_path:
        print("\n⚠ No MIDI files found in input/ directory")
        print("\nTo use this demo:")
        print("  1. Place a MIDI file (with drums) in the input/ directory")
        print("  2. Run this script again")
        print("\nExample:")
        print("  cp your_drums.mid input/test.mid")
        print("  python moderngl_renderer/demo_midi_file_render.py")
        return
    
    # Render to images
    output_dir = "moderngl_renderer/test_artifacts/midi_file_demo"
    
    try:
        render_midi_to_images(
            midi_path=midi_path,
            output_dir=output_dir,
            width=1920,
            height=1080,
            fps=60,
            sample_every_n_frames=30  # Save 1 frame per second
        )
        
        print("\n" + "=" * 70)
        print("Next steps:")
        print("  - Add FFmpeg encoding for actual video output")
        print("  - Integrate with project_manager for audio sync")
        print("  - Add configuration UI for visual settings")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
