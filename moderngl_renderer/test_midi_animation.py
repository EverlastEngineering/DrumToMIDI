"""
Tests for MIDI Animation Bridge

Tests the conversion from DrumNote to animation format.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from midi_types import DrumNote, STANDARD_GM_DRUM_MAP
from moderngl_renderer.midi_animation import (
    calculate_lane_x_position,
    calculate_note_width,
    calculate_note_height,
    convert_drum_note_to_animation,
    convert_drum_notes_to_animation,
    get_visible_notes_at_time,
    calculate_note_y_at_time
)


# ============================================================================
# Level 1: Smoke Tests
# ============================================================================

def test_calculate_lane_x_position_basic():
    """Smoke: Lane positions don't crash"""
    # 4 lanes should be evenly distributed
    x0 = calculate_lane_x_position(0, 4)
    x3 = calculate_lane_x_position(3, 4)
    
    assert -1.0 <= x0 <= 1.0
    assert -1.0 <= x3 <= 1.0
    assert x0 < x3  # Lane 0 should be left of lane 3


def test_calculate_note_dimensions():
    """Smoke: Note dimension calculations don't crash"""
    width = calculate_note_width(4)
    height = calculate_note_height(
        fall_duration=1.5,
        pixels_per_second=600.0,
        screen_height=1080
    )
    
    assert width > 0
    assert height > 0
    assert width < 1.0  # Should be less than half screen
    assert height < 0.5  # Should be reasonable


def test_convert_single_drum_note():
    """Smoke: Converting a single drum note doesn't crash"""
    drum_note = DrumNote(
        midi_note=38,  # Snare
        time=1.5,
        velocity=100,
        lane=0,
        color=(255, 100, 100),
        name="Snare"
    )
    
    anim_note = convert_drum_note_to_animation(
        drum_note=drum_note,
        lane_x=-0.5,
        note_width=0.4,
        note_height=0.1,
        fall_duration=1.5,
        strike_line_y=-0.6
    )
    
    assert anim_note.x == -0.5
    assert anim_note.hit_time == 1.5
    assert anim_note.is_kick == False
    assert anim_note.velocity == 100


def test_convert_kick_drum_note():
    """Smoke: Kick drums convert with full width"""
    kick_note = DrumNote(
        midi_note=36,
        time=2.0,
        velocity=127,
        lane=-1,  # Kick drum special lane
        color=(200, 50, 50),
        name="Kick"
    )
    
    anim_note = convert_drum_note_to_animation(
        drum_note=kick_note,
        lane_x=-0.5,  # Will be overridden for kick
        note_width=0.4,
        note_height=0.1,
        fall_duration=1.5
    )
    
    assert anim_note.is_kick == True
    assert anim_note.width == 2.0  # Full screen width
    assert anim_note.x == 0.0  # Centered


# ============================================================================
# Level 2: Property Tests
# ============================================================================

def test_lane_positions_are_ordered():
    """Property: Lanes should be in left-to-right order"""
    positions = [calculate_lane_x_position(i, 5) for i in range(5)]
    
    # Each position should be greater than the previous
    for i in range(len(positions) - 1):
        assert positions[i] < positions[i + 1]


def test_lane_positions_span_screen():
    """Property: Lanes should span from left to right edge"""
    num_lanes = 6
    positions = [calculate_lane_x_position(i, num_lanes) for i in range(num_lanes)]
    
    # Leftmost should be near left edge
    assert positions[0] < -0.5
    # Rightmost should be near right edge
    assert positions[-1] > 0.5


def test_note_width_decreases_with_more_lanes():
    """Property: More lanes = narrower notes"""
    width_4_lanes = calculate_note_width(4)
    width_8_lanes = calculate_note_width(8)
    
    assert width_8_lanes < width_4_lanes


def test_color_conversion_to_normalized():
    """Property: Colors should be converted from 0-255 to 0.0-1.0"""
    drum_note = DrumNote(
        midi_note=42,
        time=1.0,
        velocity=80,
        lane=1,
        color=(255, 128, 64),  # 0-255 range
        name="Hi-Hat"
    )
    
    anim_note = convert_drum_note_to_animation(
        drum_note=drum_note,
        lane_x=0.0,
        note_width=0.4,
        note_height=0.1,
        fall_duration=1.5
    )
    
    # Colors should be in 0.0-1.0 range
    assert all(0.0 <= c <= 1.0 for c in anim_note.color)
    # Red should be 1.0 (255/255)
    assert anim_note.color[0] == pytest.approx(1.0, abs=0.01)
    # Green should be ~0.5 (128/255)
    assert anim_note.color[1] == pytest.approx(0.5, abs=0.01)


def test_start_time_before_hit_time():
    """Property: Notes should start appearing before they hit"""
    drum_note = DrumNote(
        midi_note=38,
        time=5.0,
        velocity=100,
        lane=0,
        color=(255, 255, 255),
        name="Snare"
    )
    
    anim_note = convert_drum_note_to_animation(
        drum_note=drum_note,
        lane_x=0.0,
        note_width=0.4,
        note_height=0.1,
        fall_duration=2.0
    )
    
    assert anim_note.start_time < anim_note.hit_time
    # Should start fall_duration seconds before hit
    assert anim_note.start_time == pytest.approx(3.0, abs=0.01)  # 5.0 - 2.0


def test_note_y_position_interpolates_correctly():
    """Property: Note Y should move linearly from top to strike line"""
    drum_note = DrumNote(
        midi_note=38,
        time=2.0,
        velocity=100,
        lane=0,
        color=(255, 255, 255),
        name="Snare"
    )
    
    anim_note = convert_drum_note_to_animation(
        drum_note=drum_note,
        lane_x=0.0,
        note_width=0.4,
        note_height=0.1,
        fall_duration=1.0
    )
    
    # At start time, should be at top
    y_at_start = calculate_note_y_at_time(anim_note, anim_note.start_time, -0.6)
    assert y_at_start == pytest.approx(1.0, abs=0.01)
    
    # At hit time, should be at strike line
    y_at_hit = calculate_note_y_at_time(anim_note, anim_note.hit_time, -0.6)
    assert y_at_hit == pytest.approx(-0.6, abs=0.01)
    
    # Halfway through, should be halfway down
    y_at_half = calculate_note_y_at_time(anim_note, anim_note.start_time + 0.5, -0.6)
    expected_half = 1.0 + (-0.6 - 1.0) * 0.5  # = 0.2
    assert y_at_half == pytest.approx(expected_half, abs=0.01)


def test_convert_multiple_notes_with_different_lanes():
    """Property: Notes in different lanes should have different X positions"""
    drum_notes = [
        DrumNote(38, 1.0, 100, 0, (255, 0, 0), "Snare"),
        DrumNote(42, 1.5, 90, 1, (0, 255, 0), "Hi-Hat"),
        DrumNote(49, 2.0, 85, 2, (0, 0, 255), "Crash"),
    ]
    
    anim_notes = convert_drum_notes_to_animation(drum_notes)
    
    # Should have converted all notes
    assert len(anim_notes) == 3
    
    # All X positions should be different
    x_positions = [n.x for n in anim_notes]
    assert len(set(x_positions)) == 3  # All unique


def test_visibility_window():
    """Property: Only notes near current time should be visible"""
    drum_note = DrumNote(38, 5.0, 100, 0, (255, 255, 255), "Snare")
    anim_note = convert_drum_note_to_animation(
        drum_note, 0.0, 0.4, 0.1, 2.0
    )
    
    # Before start time: not visible
    visible_early = get_visible_notes_at_time([anim_note], 2.0)
    assert len(visible_early) == 0
    
    # During fall: visible
    visible_during = get_visible_notes_at_time([anim_note], 4.0)
    assert len(visible_during) == 1
    
    # Right at hit time: visible
    visible_at_hit = get_visible_notes_at_time([anim_note], 5.0)
    assert len(visible_at_hit) == 1
    
    # Just after hit (within lookbehind): visible
    visible_after = get_visible_notes_at_time([anim_note], 5.3)
    assert len(visible_after) == 1
    
    # Well after hit (past lookbehind): not visible
    visible_late = get_visible_notes_at_time([anim_note], 6.0)
    assert len(visible_late) == 0


# ============================================================================
# Integration Test with Real Data
# ============================================================================

def test_convert_notes_from_project_13():
    """Integration: Convert notes that would come from project 13"""
    # Simulate some notes from a real MIDI file
    drum_notes = [
        DrumNote(36, 0.5, 120, -1, (200, 50, 50), "Kick"),  # Kick drum
        DrumNote(38, 1.0, 100, 0, (255, 100, 100), "Snare"),
        DrumNote(42, 1.25, 80, 1, (150, 150, 255), "Hi-Hat Closed"),
        DrumNote(38, 2.0, 110, 0, (255, 100, 100), "Snare"),
        DrumNote(42, 2.25, 85, 1, (150, 150, 255), "Hi-Hat Closed"),
    ]
    
    anim_notes = convert_drum_notes_to_animation(
        drum_notes,
        screen_width=1920,
        screen_height=1080,
        pixels_per_second=600.0,
        strike_line_percent=0.85
    )
    
    # Should convert all notes
    assert len(anim_notes) == 5
    
    # Kick drum should be full width
    kick = [n for n in anim_notes if n.is_kick][0]
    assert kick.width == pytest.approx(2.0, abs=0.01)
    assert kick.x == 0.0
    
    # Regular notes should have reasonable positions
    regular = [n for n in anim_notes if not n.is_kick]
    assert all(-1.0 <= n.x <= 1.0 for n in regular)
    assert all(n.width < 1.0 for n in regular)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
