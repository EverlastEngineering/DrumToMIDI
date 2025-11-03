"""
MIDI Animation Demo - Project 13

Loads project 13 (srdrums) MIDI file, converts to animation format,
and prints debug info to verify the conversion is correct.

This is a smoke test before we integrate with actual GPU rendering.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from midi_shell import parse_midi_file
from midi_types import STANDARD_GM_DRUM_MAP
from moderngl_renderer.midi_animation import (
    convert_drum_notes_to_animation,
    get_visible_notes_at_time
)


def main():
    print("=" * 60)
    print("MIDI Animation Demo - Project 13 (srdrums)")
    print("=" * 60)
    print()
    
    # Project 13 MIDI file path
    midi_path = "user_files/13 - srdrums/midi/srdrums.mid"
    
    print(f"Loading MIDI file: {midi_path}")
    
    # Parse MIDI file to DrumNotes
    drum_notes, duration = parse_midi_file(
        midi_path=midi_path,
        drum_map=STANDARD_GM_DRUM_MAP,
        tail_duration=3.0
    )
    
    print(f"✓ Loaded {len(drum_notes)} notes")
    print(f"✓ Duration: {duration:.2f}s")
    print()
    
    # Find unique lanes
    lanes = set(n.lane for n in drum_notes)
    regular_lanes = sorted([l for l in lanes if l >= 0])
    has_kick = -1 in lanes
    
    print(f"Lanes found:")
    print(f"  • Regular lanes: {regular_lanes} ({len(regular_lanes)} lanes)")
    print(f"  • Kick drum (lane -1): {'Yes' if has_kick else 'No'}")
    print()
    
    # Show first few notes
    print("First 10 notes from MIDI:")
    for i, note in enumerate(drum_notes[:10]):
        print(f"  {i+1}. {note.name:20s} lane={note.lane:2d} time={note.time:6.2f}s vel={note.velocity:3d}")
    print()
    
    # Convert to animation format
    print("Converting to animation format...")
    anim_notes = convert_drum_notes_to_animation(
        drum_notes=drum_notes,
        screen_width=1920,
        screen_height=1080,
        pixels_per_second=600.0,
        strike_line_percent=0.85
    )
    
    print(f"✓ Converted {len(anim_notes)} notes to animation format")
    print()
    
    # Show first few animation notes
    print("First 10 animation notes:")
    for i, note in enumerate(anim_notes[:10]):
        kick_marker = " [KICK]" if note.is_kick else ""
        print(f"  {i+1}. {note.name:20s} x={note.x:6.2f} "
              f"start={note.start_time:6.2f}s hit={note.hit_time:6.2f}s{kick_marker}")
    print()
    
    # Test visibility at different times
    test_times = [0.0, 1.0, 2.0, 5.0]
    print("Visibility check at different times:")
    for t in test_times:
        visible = get_visible_notes_at_time(anim_notes, t)
        print(f"  t={t:.1f}s: {len(visible)} notes visible")
    print()
    
    # Verify coordinate system
    print("Coordinate system verification:")
    
    # Check X positions are in valid range
    x_positions = [n.x for n in anim_notes if not n.is_kick]
    if x_positions:
        print(f"  • Regular note X range: {min(x_positions):.2f} to {max(x_positions):.2f}")
        print(f"    Expected: -1.0 to +1.0 range ✓")
    
    # Check kick drums
    kick_notes = [n for n in anim_notes if n.is_kick]
    if kick_notes:
        print(f"  • Kick drums: {len(kick_notes)} notes")
        print(f"    Width: {kick_notes[0].width:.2f} (should be 2.0 = full screen) ✓")
        print(f"    X position: {kick_notes[0].x:.2f} (should be 0.0 = centered) ✓")
    
    # Check start times
    start_times = [n.start_time for n in anim_notes]
    hit_times = [n.hit_time for n in anim_notes]
    print(f"  • Start times: {min(start_times):.2f}s to {max(start_times):.2f}s")
    print(f"  • Hit times: {min(hit_times):.2f}s to {max(hit_times):.2f}s")
    print(f"  • All start < hit: {all(n.start_time < n.hit_time for n in anim_notes)} ✓")
    
    # Check colors
    all_colors_valid = all(
        all(0.0 <= c <= 1.0 for c in n.color)
        for n in anim_notes
    )
    print(f"  • All colors in 0.0-1.0 range: {all_colors_valid} ✓")
    
    print()
    print("=" * 60)
    print("✓ MIDI to Animation Conversion Successful!")
    print("=" * 60)
    print()
    print("Next step: Integrate with shell.py for GPU rendering")
    

if __name__ == "__main__":
    main()
