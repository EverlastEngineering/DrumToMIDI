"""
Tests for MIDI Video Core - Functional Core

Tests pure functions in midi_video_core.py.
All functions are pure (no side effects), so tests are deterministic.
"""

import pytest
from moderngl_renderer.midi_video_core import (
    calculate_strike_effect,
    calculate_note_fade,
    midi_note_to_rectangle,
    create_strike_line_rectangle,
    create_lane_markers
)


# ============================================================================
# Strike Effect Tests
# ============================================================================

class TestStrikeEffect:
    """Test strike effect calculations"""
    
    def test_far_from_strike_line_no_effect(self):
        """Notes far from strike line have no effect"""
        scale, flash, brightness = calculate_strike_effect(
            y_center=0.5,
            strike_line_y=-0.6,
            strike_window=0.04
        )
        
        assert scale == 1.0
        assert flash == 0.0
        assert brightness == 0.0
    
    def test_at_strike_line_max_effect(self):
        """Notes at strike line have maximum effect"""
        scale, flash, brightness = calculate_strike_effect(
            y_center=-0.6,
            strike_line_y=-0.6,
            strike_window=0.04
        )
        
        assert scale > 1.0  # Enlarged
        assert flash > 0.0  # Flash present
        assert brightness > 0.0  # Brighter
        
        # Check actual values match spec
        assert scale == pytest.approx(1.7, abs=0.01)  # 1.0 + 0.7 = 1.7
        assert flash > 1.0  # Can exceed 1.0 for strong flash
        assert brightness == pytest.approx(0.7, abs=0.01)
    
    def test_within_strike_window_gradual_effect(self):
        """Effect gradually increases as note approaches strike line"""
        # Just entered window (top edge)
        scale1, flash1, brightness1 = calculate_strike_effect(
            y_center=-0.56,  # 0.04 above strike line
            strike_line_y=-0.6,
            strike_window=0.04
        )
        
        # Halfway to strike line
        scale2, flash2, brightness2 = calculate_strike_effect(
            y_center=-0.58,  # 0.02 above strike line
            strike_line_y=-0.6,
            strike_window=0.04
        )
        
        # At strike line
        scale3, flash3, brightness3 = calculate_strike_effect(
            y_center=-0.6,
            strike_line_y=-0.6,
            strike_window=0.04
        )
        
        # Should increase monotonically
        assert scale1 < scale2 < scale3
        assert flash1 < flash2 < flash3
        assert brightness1 < brightness2 < brightness3
    
    def test_symmetric_above_and_below(self):
        """Effect is symmetric above and below strike line"""
        above_scale, above_flash, above_brightness = calculate_strike_effect(
            y_center=-0.58,  # 0.02 above
            strike_line_y=-0.6,
            strike_window=0.04
        )
        
        below_scale, below_flash, below_brightness = calculate_strike_effect(
            y_center=-0.62,  # 0.02 below
            strike_line_y=-0.6,
            strike_window=0.04
        )
        
        assert above_scale == pytest.approx(below_scale, abs=0.001)
        assert above_flash == pytest.approx(below_flash, abs=0.001)
        assert above_brightness == pytest.approx(below_brightness, abs=0.001)


# ============================================================================
# Note Fade Tests
# ============================================================================

class TestNoteFade:
    """Test note fade calculations"""
    
    def test_above_strike_line_no_fade(self):
        """Notes above strike line have no fade"""
        fade = calculate_note_fade(
            y_center=-0.5,
            strike_line_y=-0.6,
            fade_distance=0.3
        )
        assert fade == 1.0
    
    def test_at_strike_line_no_fade(self):
        """Notes at strike line have no fade"""
        fade = calculate_note_fade(
            y_center=-0.6,
            strike_line_y=-0.6,
            fade_distance=0.3
        )
        assert fade == 1.0
    
    def test_below_strike_line_gradual_fade(self):
        """Notes below strike line fade gradually"""
        # Just below strike line
        fade1 = calculate_note_fade(-0.61, -0.6, 0.3)
        
        # Halfway through fade distance
        fade2 = calculate_note_fade(-0.75, -0.6, 0.3)
        
        # At full fade distance
        fade3 = calculate_note_fade(-0.9, -0.6, 0.3)
        
        # Should decrease monotonically
        assert 1.0 > fade1 > fade2 > fade3
        assert fade3 == pytest.approx(0.0, abs=0.01)
    
    def test_beyond_fade_distance_fully_faded(self):
        """Notes beyond fade distance are fully faded"""
        fade = calculate_note_fade(-1.0, -0.6, 0.3)
        assert fade == 0.0


# ============================================================================
# Rectangle Conversion Tests
# ============================================================================

class TestMidiNoteToRectangle:
    """Test MIDI note to rectangle conversion"""
    
    def test_basic_conversion(self):
        """Basic note conversion without effects"""
        rect = midi_note_to_rectangle(
            x=0.0,
            y_center=0.5,  # Far from strike line
            width=0.3,
            height=0.1,
            color=(1.0, 0.0, 0.0),
            velocity=100,
            is_kick=False
        )
        
        # Should have all required keys
        assert 'x' in rect
        assert 'y' in rect
        assert 'width' in rect
        assert 'height' in rect
        assert 'color' in rect
        assert 'no_outline' in rect
        
        # Width should be unchanged
        assert rect['width'] == 0.3
        
        # Height should be unchanged (no strike effect)
        assert rect['height'] == 0.1
        
        # Color should be dimmed based on velocity
        # velocity=100 → brightness ≈ 0.3 + (100/127)*0.7 ≈ 0.85
        assert rect['color'][0] > 0.8  # Red channel high
        assert rect['color'][1] == 0.0  # Green channel zero
        assert rect['color'][2] == 0.0  # Blue channel zero
    
    def test_velocity_affects_brightness(self):
        """Higher velocity produces brighter colors"""
        rect_low = midi_note_to_rectangle(
            x=0.0, y_center=0.5, width=0.3, height=0.1,
            color=(1.0, 0.0, 0.0), velocity=50, is_kick=False
        )
        
        rect_high = midi_note_to_rectangle(
            x=0.0, y_center=0.5, width=0.3, height=0.1,
            color=(1.0, 0.0, 0.0), velocity=120, is_kick=False
        )
        
        assert rect_high['color'][0] > rect_low['color'][0]
    
    def test_strike_line_enlarges_note(self):
        """Notes at strike line are enlarged"""
        rect = midi_note_to_rectangle(
            x=0.0,
            y_center=-0.6,  # At strike line
            width=0.3,
            height=0.1,
            color=(1.0, 0.0, 0.0),
            velocity=100,
            is_kick=False,
            strike_line_y=-0.6
        )
        
        # Height should be enlarged (width unchanged)
        assert rect['width'] == 0.3
        assert rect['height'] > 0.1
    
    def test_fade_after_strike_line(self):
        """Notes below strike line fade out"""
        rect_above = midi_note_to_rectangle(
            x=0.0, y_center=-0.5, width=0.3, height=0.1,
            color=(1.0, 0.0, 0.0), velocity=100, is_kick=False,
            strike_line_y=-0.6
        )
        
        rect_below = midi_note_to_rectangle(
            x=0.0, y_center=-0.8, width=0.3, height=0.1,
            color=(1.0, 0.0, 0.0), velocity=100, is_kick=False,
            strike_line_y=-0.6, fade_distance=0.3
        )
        
        # Below strike line should be dimmer
        assert rect_below['color'][0] < rect_above['color'][0]
    
    def test_kick_drum_has_no_outline(self):
        """Kick drum notes should skip outline"""
        rect_kick = midi_note_to_rectangle(
            x=0.0, y_center=0.5, width=0.3, height=0.1,
            color=(1.0, 0.0, 0.0), velocity=100, is_kick=True
        )
        
        rect_normal = midi_note_to_rectangle(
            x=0.0, y_center=0.5, width=0.3, height=0.1,
            color=(1.0, 0.0, 0.0), velocity=100, is_kick=False
        )
        
        assert rect_kick['no_outline'] is True
        assert rect_normal['no_outline'] is False
    
    def test_coordinates_are_top_left(self):
        """Rectangle coordinates should be top-left corner"""
        rect = midi_note_to_rectangle(
            x=0.5,  # Center X
            y_center=0.2,  # Center Y
            width=0.4,
            height=0.1,
            color=(1.0, 0.0, 0.0),
            velocity=100,
            is_kick=False
        )
        
        # X should be left edge (center - width/2)
        assert rect['x'] == pytest.approx(0.5 - 0.4/2, abs=0.001)
        
        # Y should be top edge (center + height/2 in OpenGL coords)
        assert rect['y'] == pytest.approx(0.2 + 0.1/2, abs=0.001)


# ============================================================================
# UI Element Tests
# ============================================================================

class TestStrikeLineCreation:
    """Test strike line rectangle creation"""
    
    def test_creates_valid_rectangle(self):
        """Should create valid rectangle dict"""
        rect = create_strike_line_rectangle()
        
        assert 'x' in rect
        assert 'y' in rect
        assert 'width' in rect
        assert 'height' in rect
        assert 'color' in rect
        assert 'no_outline' in rect
    
    def test_spans_full_width(self):
        """Strike line should span full screen width"""
        rect = create_strike_line_rectangle()
        
        assert rect['x'] == -1.0
        assert rect['width'] == 2.0
    
    def test_is_white(self):
        """Strike line should be white"""
        rect = create_strike_line_rectangle()
        assert rect['color'] == (1.0, 1.0, 1.0)
    
    def test_has_no_outline(self):
        """Strike line should skip outline"""
        rect = create_strike_line_rectangle()
        assert rect['no_outline'] is True
    
    def test_thickness_parameter(self):
        """Thickness parameter should affect height"""
        rect1 = create_strike_line_rectangle(thickness=0.01)
        rect2 = create_strike_line_rectangle(thickness=0.02)
        
        assert rect2['height'] == rect1['height'] * 2


class TestLaneMarkerCreation:
    """Test lane marker creation"""
    
    def test_creates_correct_number(self):
        """Should create num_lanes + 1 markers"""
        markers = create_lane_markers(3)
        assert len(markers) == 4
        
        markers = create_lane_markers(5)
        assert len(markers) == 6
    
    def test_markers_are_valid_rectangles(self):
        """Each marker should be a valid rectangle"""
        markers = create_lane_markers(3)
        
        for marker in markers:
            assert 'x' in marker
            assert 'y' in marker
            assert 'width' in marker
            assert 'height' in marker
            assert 'color' in marker
            assert 'no_outline' in marker
    
    def test_markers_span_full_height(self):
        """Markers should span full screen height"""
        markers = create_lane_markers(3)
        
        for marker in markers:
            assert marker['y'] == 1.0
            assert marker['height'] == 2.0
    
    def test_markers_evenly_spaced(self):
        """Markers should be evenly spaced"""
        markers = create_lane_markers(3)
        
        # Extract X positions (center of marker)
        positions = [m['x'] + 0.005 for m in markers]  # Adjust for half-width
        
        # Should be evenly spaced from -1.0 to 1.0
        expected = [-1.0, -1.0 + 2.0/3, -1.0 + 4.0/3, 1.0]
        
        for pos, exp in zip(positions, expected):
            assert pos == pytest.approx(exp, abs=0.01)
    
    def test_markers_are_gray(self):
        """Markers should be dark gray"""
        markers = create_lane_markers(3)
        
        for marker in markers:
            assert marker['color'] == (0.3, 0.3, 0.3)
    
    def test_markers_have_no_outline(self):
        """Markers should skip outline"""
        markers = create_lane_markers(3)
        
        for marker in markers:
            assert marker['no_outline'] is True


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Test interactions between functions"""
    
    def test_full_note_pipeline(self):
        """Test complete note transformation pipeline"""
        # Simulate a note approaching and passing strike line
        positions = [0.5, 0.0, -0.6, -0.8, -1.0]  # Above → at → below strike
        
        for y_pos in positions:
            rect = midi_note_to_rectangle(
                x=0.0,
                y_center=y_pos,
                width=0.3,
                height=0.1,
                color=(1.0, 0.0, 0.0),
                velocity=100,
                is_kick=False
            )
            
            # All rectangles should be valid
            assert rect['width'] > 0
            assert rect['height'] > 0
            assert 0 <= rect['color'][0] <= 2.0  # Allow flash effect > 1.0
    
    def test_scene_composition(self):
        """Test composing a complete scene"""
        # Create a basic scene with notes and UI elements
        notes = [
            midi_note_to_rectangle(
                x=-0.5, y_center=0.0, width=0.3, height=0.1,
                color=(1.0, 0.0, 0.0), velocity=100, is_kick=False
            ),
            midi_note_to_rectangle(
                x=0.0, y_center=-0.6, width=0.3, height=0.1,
                color=(0.0, 1.0, 0.0), velocity=120, is_kick=False
            ),
            midi_note_to_rectangle(
                x=0.5, y_center=-0.3, width=0.3, height=0.1,
                color=(0.0, 0.0, 1.0), velocity=80, is_kick=False
            ),
        ]
        
        strike_line = create_strike_line_rectangle()
        lane_markers = create_lane_markers(3)
        
        # All elements should be valid rectangles
        all_elements = notes + [strike_line] + lane_markers
        
        for elem in all_elements:
            assert 'x' in elem
            assert 'y' in elem
            assert 'width' in elem
            assert 'height' in elem
            assert 'color' in elem
