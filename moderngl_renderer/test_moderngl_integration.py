#!/usr/bin/env python3
"""
Quick test to verify ModernGL integration with render_midi_to_video.py
Renders just 10 frames of a MIDI file to verify the pipeline works.
"""

import sys
from pathlib import Path
# Add parent directory to path to import from root
sys.path.insert(0, str(Path(__file__).parent.parent))
from render_midi_to_video import MidiVideoRenderer

def test_moderngl_integration():
    """Test ModernGL rendering integration"""
    
    # Use project 1 MIDI file (relative to root)
    midi_file = Path(__file__).parent.parent / "user_files/1 - The Fate Of Ophelia/midi/The Fate Of Ophelia.mid"
    
    if not midi_file.exists():
        print(f"ERROR: Test MIDI file not found: {midi_file}")
        return False
    
    print("="*60)
    print("Testing ModernGL Integration")
    print("="*60)
    print(f"MIDI: {midi_file}")
    print(f"Test: Render 10 frames only (skip video encoding)")
    print()
    
    try:
        # Create renderer
        print("Initializing renderer...")
        renderer = MidiVideoRenderer(width=1920, height=1080, fps=60)
        print("✓ ModernGL context created successfully")
        
        # Parse MIDI
        print("\nParsing MIDI...")
        notes, duration = renderer.parse_midi(str(midi_file))
        print(f"✓ Found {len(notes)} notes, duration {duration:.2f}s")
        
        # Render a few frames to test the pipeline
        print("\nRendering test frames...")
        lookahead_time = renderer.strike_line_y / renderer.pixels_per_second
        passthrough_time = (renderer.height - renderer.strike_line_y + renderer.note_height) / renderer.pixels_per_second
        
        note_index = 0
        for frame_num in range(10):
            current_time = frame_num / renderer.fps
            frame_bgr, note_index = renderer.render_frame_with_moderngl(
                notes, current_time, lookahead_time, passthrough_time, note_index
            )
            
            # Verify frame shape and type
            assert frame_bgr.shape == (renderer.height, renderer.width, 3), \
                f"Wrong frame shape: {frame_bgr.shape}"
            assert frame_bgr.dtype.name == 'uint8', \
                f"Wrong frame dtype: {frame_bgr.dtype}"
            
            if frame_num == 0:
                print(f"  Frame 0: shape={frame_bgr.shape}, dtype={frame_bgr.dtype}")
        
        print(f"✓ Rendered 10 frames successfully")
        
        print("\n" + "="*60)
        print("✅ ModernGL Integration Test PASSED")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_moderngl_integration()
    sys.exit(0 if success else 1)
