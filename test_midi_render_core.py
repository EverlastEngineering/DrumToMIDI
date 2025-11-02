"""
Tests for midi_render_core.py - Pure rendering calculation functions

These tests verify the functional core of the MIDI rendering system.
All functions are pure (no side effects), so tests are straightforward
and don't require mocking or fixtures.
"""

import pytest
from midi_render_core import (
    calculate_note_alpha,
    calculate_brightness,
    apply_brightness_to_color,
    get_brighter_outline_color,
    calculate_note_y_position,
    calculate_highlight_zone,
    is_note_in_highlight_zone,
    calculate_strike_progress,
    calculate_lookahead_time,
    calculate_passthrough_time,
    calculate_used_lanes,
    create_lane_mapping,
    remap_note_lanes,
    filter_and_remap_lanes,
    calculate_kick_strike_pulse,
    calculate_strike_color_mix,
    calculate_strike_glow_size,
    calculate_strike_alpha_boost,
    calculate_strike_outline_width
)
from midi_types import DrumNote


class TestColorBrightness:
    """Test color and brightness calculations"""
    
    def test_calculate_brightness_full(self):
        """Full velocity (127) should give 1.0 brightness"""
        assert calculate_brightness(127) == 1.0
    
    def test_calculate_brightness_half(self):
        """Half velocity should give ~0.5 brightness"""
        assert abs(calculate_brightness(64) - 0.5) < 0.01
    
    def test_calculate_brightness_zero(self):
        """Zero velocity should give 0.0 brightness"""
        assert calculate_brightness(0) == 0.0
    
    def test_apply_brightness_full(self):
        """Full brightness should preserve color"""
        color = (255, 128, 64)
        result = apply_brightness_to_color(color, 1.0)
        assert result == color
    
    def test_apply_brightness_half(self):
        """Half brightness should halve all channels"""
        color = (200, 100, 50)
        result = apply_brightness_to_color(color, 0.5)
        assert result == (100, 50, 25)
    
    def test_apply_brightness_zero(self):
        """Zero brightness should produce black"""
        color = (255, 255, 255)
        result = apply_brightness_to_color(color, 0.0)
        assert result == (0, 0, 0)
    
    def test_get_brighter_outline_color(self):
        """Brighter outline should increase RGB values"""
        base = (100, 100, 100)
        result = get_brighter_outline_color(base, 200)
        # Should brighten by 80% of headroom
        expected_r = int(100 + (255 - 100) * 0.8)
        assert result == (expected_r, expected_r, expected_r, 200)
    
    def test_get_brighter_outline_maxed_color(self):
        """Already-bright colors shouldn't exceed 255"""
        base = (250, 250, 250)
        result = get_brighter_outline_color(base, 255)
        assert all(c <= 255 for c in result[:3])


class TestNoteAlpha:
    """Test note transparency calculations"""
    
    def test_alpha_before_strike(self):
        """Notes before strike line should be fully opaque"""
        alpha = calculate_note_alpha(
            time_until_hit=1.0,  # 1 second before hit
            y_pos=500,
            strike_line_y=900,
            height=1080
        )
        assert alpha == 1.0
    
    def test_alpha_at_strike(self):
        """Note at exact strike line should be fully opaque"""
        alpha = calculate_note_alpha(
            time_until_hit=0.0,
            y_pos=900,
            strike_line_y=900,
            height=1080
        )
        assert alpha == 1.0
    
    def test_alpha_after_strike_starts_fade(self):
        """Notes just past strike line should start fading"""
        alpha = calculate_note_alpha(
            time_until_hit=-0.1,
            y_pos=920,  # 20 pixels past strike line
            strike_line_y=900,
            height=1080
        )
        assert 0.8 < alpha < 1.0  # Should be fading but still mostly visible
    
    def test_alpha_at_bottom(self):
        """Notes at bottom should be 20% alpha"""
        alpha = calculate_note_alpha(
            time_until_hit=-5.0,  # Long after hit
            y_pos=1080,  # At bottom
            strike_line_y=900,
            height=1080
        )
        assert abs(alpha - 0.2) < 0.01


class TestPositionCalculations:
    """Test note position calculations"""
    
    def test_calculate_note_y_position_at_strike(self):
        """Note at strike time should be at strike line"""
        y_pos = calculate_note_y_position(
            note_time=5.0,
            current_time=5.0,
            strike_line_y=900,
            pixels_per_second=400
        )
        assert y_pos == 900
    
    def test_calculate_note_y_position_before_strike(self):
        """Note 1 second before strike should be above strike line"""
        y_pos = calculate_note_y_position(
            note_time=6.0,
            current_time=5.0,
            strike_line_y=900,
            pixels_per_second=400
        )
        # Should be 400 pixels above strike line
        assert y_pos == 500
    
    def test_calculate_note_y_position_after_strike(self):
        """Note 1 second after strike should be below strike line"""
        y_pos = calculate_note_y_position(
            note_time=4.0,
            current_time=5.0,
            strike_line_y=900,
            pixels_per_second=400
        )
        # Should be 400 pixels below strike line
        assert y_pos == 1300
    
    def test_calculate_highlight_zone_default(self):
        """Highlight zone should be 1.5x note height by default"""
        start, end = calculate_highlight_zone(
            strike_line_y=900,
            note_height=60
        )
        # Zone height should be 90 pixels (60 * 1.5)
        # Centered on 900, so 900 ± 45
        assert start == 855
        assert end == 945
    
    def test_calculate_highlight_zone_custom_multiplier(self):
        """Custom multiplier should adjust zone size"""
        start, end = calculate_highlight_zone(
            strike_line_y=900,
            note_height=60,
            zone_multiplier=2.0
        )
        # Zone height should be 120 pixels (60 * 2.0)
        assert end - start == 120


class TestHighlightDetection:
    """Test highlight zone detection"""
    
    def create_test_note(self, time: float, lane: int = 0) -> DrumNote:
        """Helper to create test notes"""
        return DrumNote(
            midi_note=38,
            time=time,
            velocity=100,
            lane=lane,
            color=(255, 0, 0),
            name="Test"
        )
    
    def test_is_note_in_highlight_zone_at_center(self):
        """Note at exact strike time should be in highlight zone"""
        note = self.create_test_note(time=5.0)
        result = is_note_in_highlight_zone(
            note=note,
            current_time=5.0,
            strike_line_y=900,
            note_height=60,
            pixels_per_second=400
        )
        assert result is True
    
    def test_is_note_in_highlight_zone_entering(self):
        """Note just entering zone should be detected"""
        # Zone is 855-945 (90 pixels, centered on strike line at 900)
        # For note center to be at zone start (855), note bottom should be at 885
        # That's 15 pixels above strike line = 15/400 = 0.0375 seconds before
        note = self.create_test_note(time=5.0375)
        result = is_note_in_highlight_zone(
            note=note,
            current_time=5.0,
            strike_line_y=900,
            note_height=60,
            pixels_per_second=400
        )
        # Note center should be right at zone boundary
        assert result is True
    
    def test_is_note_in_highlight_zone_outside(self):
        """Note far from strike line should not be in zone"""
        note = self.create_test_note(time=10.0)  # 5 seconds in future
        result = is_note_in_highlight_zone(
            note=note,
            current_time=5.0,
            strike_line_y=900,
            note_height=60,
            pixels_per_second=400
        )
        assert result is False
    
    def test_calculate_strike_progress_at_center(self):
        """Progress when note is at strike line"""
        # At exact strike time, note bottom is at strike line (y=900)
        # Note top at 840, center at 870
        # Zone is 855-945 (90 pixels), so center at 870 is at position 15/90 = 0.167
        note = self.create_test_note(time=5.0)
        progress = calculate_strike_progress(
            note=note,
            current_time=5.0,
            strike_line_y=900,
            note_height=60,
            pixels_per_second=400
        )
        # Progress should be around 0.17 (note center near top of zone)
        assert 0.1 < progress < 0.25
    
    def test_calculate_strike_progress_before_zone(self):
        """Progress should be 0.0 before entering zone"""
        note = self.create_test_note(time=10.0)
        progress = calculate_strike_progress(
            note=note,
            current_time=5.0,
            strike_line_y=900,
            note_height=60,
            pixels_per_second=400
        )
        assert progress == 0.0
    
    def test_calculate_strike_progress_after_zone(self):
        """Progress should be 1.0 after leaving zone"""
        note = self.create_test_note(time=1.0)
        progress = calculate_strike_progress(
            note=note,
            current_time=5.0,
            strike_line_y=900,
            note_height=60,
            pixels_per_second=400
        )
        assert progress == 1.0


class TestTimingCalculations:
    """Test lookahead and passthrough time calculations"""
    
    def test_calculate_lookahead_time(self):
        """Lookahead should be time for note to fall from top to strike line"""
        lookahead = calculate_lookahead_time(
            strike_line_y=900,
            pixels_per_second=400
        )
        # 900 pixels / 400 pixels/sec = 2.25 seconds
        assert lookahead == 2.25
    
    def test_calculate_passthrough_time(self):
        """Passthrough should be time for note to fall from strike to off-screen"""
        passthrough = calculate_passthrough_time(
            height=1080,
            strike_line_y=900,
            note_height=60,
            pixels_per_second=400
        )
        # (180 + 60) pixels / 400 pixels/sec = 0.6 seconds
        assert passthrough == 0.6


class TestLaneManagement:
    """Test lane filtering and remapping"""
    
    def create_note_at_lane(self, lane: int, time: float = 1.0) -> DrumNote:
        """Helper to create test notes at specific lanes"""
        return DrumNote(
            midi_note=38,
            time=time,
            velocity=100,
            lane=lane,
            color=(255, 0, 0),
            name=f"Lane{lane}"
        )
    
    def test_calculate_used_lanes_simple(self):
        """Should extract set of used lane numbers"""
        notes = [
            self.create_note_at_lane(0),
            self.create_note_at_lane(2),
            self.create_note_at_lane(2),  # Duplicate lane
            self.create_note_at_lane(5)
        ]
        used = calculate_used_lanes(notes)
        assert used == {0, 2, 5}
    
    def test_calculate_used_lanes_excludes_special(self):
        """Should exclude special lanes (negative values)"""
        notes = [
            self.create_note_at_lane(0),
            self.create_note_at_lane(-1),  # Kick drum
            self.create_note_at_lane(2)
        ]
        used = calculate_used_lanes(notes)
        assert used == {0, 2}
    
    def test_create_lane_mapping(self):
        """Should map sparse lanes to consecutive positions"""
        used_lanes = {0, 3, 7, 9}
        mapping = create_lane_mapping(used_lanes)
        assert mapping == {0: 0, 3: 1, 7: 2, 9: 3}
    
    def test_remap_note_lanes(self):
        """Should remap note lanes using mapping"""
        notes = [
            self.create_note_at_lane(0, time=1.0),
            self.create_note_at_lane(5, time=2.0),
            self.create_note_at_lane(-1, time=3.0)  # Special lane
        ]
        mapping = {0: 0, 5: 1}
        
        remapped = remap_note_lanes(notes, mapping)
        
        assert remapped[0].lane == 0  # 0 -> 0
        assert remapped[1].lane == 1  # 5 -> 1
        assert remapped[2].lane == -1  # Special lane preserved
        
        # Verify other properties preserved
        assert remapped[0].time == 1.0
        assert remapped[1].time == 2.0
        assert remapped[2].time == 3.0
    
    def test_remap_note_lanes_immutability(self):
        """Should create new instances, not modify originals"""
        original = self.create_note_at_lane(5)
        mapping = {5: 1}
        
        remapped = remap_note_lanes([original], mapping)
        
        assert original.lane == 5  # Original unchanged
        assert remapped[0].lane == 1  # New instance modified
        assert remapped[0] is not original  # Different objects
    
    def test_filter_and_remap_lanes_complete_pipeline(self):
        """Should filter and remap in one call"""
        notes = [
            self.create_note_at_lane(0),
            self.create_note_at_lane(3),
            self.create_note_at_lane(7),
            self.create_note_at_lane(-1)  # Kick
        ]
        
        remapped, num_lanes = filter_and_remap_lanes(notes)
        
        # Should use 3 regular lanes (0, 3, 7)
        assert num_lanes == 3
        
        # Lanes should be remapped to 0, 1, 2
        regular_lanes = [n.lane for n in remapped if n.lane >= 0]
        assert set(regular_lanes) == {0, 1, 2}
        
        # Special lane preserved
        special_notes = [n for n in remapped if n.lane == -1]
        assert len(special_notes) == 1
    
    def test_filter_and_remap_lanes_empty(self):
        """Should handle case with no regular lanes"""
        notes = [self.create_note_at_lane(-1)]  # Only kick
        
        remapped, num_lanes = filter_and_remap_lanes(notes)
        
        assert num_lanes == 0
        assert remapped == notes  # Unchanged


class TestStrikeAnimations:
    """Test strike animation calculations"""
    
    def test_calculate_kick_strike_pulse_at_center(self):
        """Pulse should be maximum at exact strike time"""
        pulse = calculate_kick_strike_pulse(0.0, strike_window=0.08)
        assert pulse == 1.0
    
    def test_calculate_kick_strike_pulse_at_edge(self):
        """Pulse should be near zero at window edge"""
        pulse = calculate_kick_strike_pulse(0.08, strike_window=0.08)
        assert pulse < 0.1
    
    def test_calculate_kick_strike_pulse_outside_window(self):
        """Pulse should be zero outside strike window"""
        pulse = calculate_kick_strike_pulse(0.1, strike_window=0.08)
        assert pulse == 0.0
    
    def test_calculate_kick_strike_pulse_symmetric(self):
        """Pulse should be symmetric around strike time"""
        pulse_before = calculate_kick_strike_pulse(-0.04, strike_window=0.08)
        pulse_after = calculate_kick_strike_pulse(0.04, strike_window=0.08)
        assert abs(pulse_before - pulse_after) < 0.01
    
    def test_calculate_strike_color_mix_no_pulse(self):
        """No pulse should return original color"""
        color = (100, 150, 200)
        result = calculate_strike_color_mix(color, pulse=0.0)
        assert result == color
    
    def test_calculate_strike_color_mix_full_pulse(self):
        """Full pulse should brighten significantly"""
        color = (100, 100, 100)
        result = calculate_strike_color_mix(color, pulse=1.0, white_mix_factor=0.5)
        # Should be 50% brighter: 100 + (255-100)*0.5 = 177.5
        assert all(c > 170 for c in result)
    
    def test_calculate_strike_color_mix_preserves_white(self):
        """White color should stay white"""
        color = (255, 255, 255)
        result = calculate_strike_color_mix(color, pulse=1.0)
        assert result == (255, 255, 255)
    
    def test_calculate_strike_glow_size_no_pulse(self):
        """No pulse should give zero size increase"""
        size = calculate_strike_glow_size(10, pulse=0.0)
        assert size == 0
    
    def test_calculate_strike_glow_size_full_pulse(self):
        """Full pulse should give maximum size increase"""
        size = calculate_strike_glow_size(10, pulse=1.0, size_multiplier=8.0)
        assert size == 8
    
    def test_calculate_strike_alpha_boost_no_pulse(self):
        """No pulse should give minimum boost"""
        alpha = calculate_strike_alpha_boost(200, pulse=0.0, min_factor=0.8)
        assert alpha == 160  # 200 * 0.8
    
    def test_calculate_strike_alpha_boost_full_pulse(self):
        """Full pulse should give maximum boost"""
        alpha = calculate_strike_alpha_boost(200, pulse=1.0, max_factor=1.0)
        assert alpha == 200  # 200 * 1.0
    
    def test_calculate_strike_outline_width_no_pulse(self):
        """No pulse should return base width"""
        width = calculate_strike_outline_width(2, pulse=0.0)
        assert width == 2
    
    def test_calculate_strike_outline_width_full_pulse(self):
        """Full pulse should add width increase"""
        width = calculate_strike_outline_width(2, pulse=1.0, width_increase=2)
        assert width == 4


class TestPurityInvariant:
    """Test that all functions are truly pure (no side effects)"""
    
    def test_functions_are_deterministic(self):
        """Same inputs should always produce same outputs"""
        # Test a few key functions
        assert calculate_brightness(64) == calculate_brightness(64)
        assert apply_brightness_to_color((255, 128, 64), 0.5) == \
               apply_brightness_to_color((255, 128, 64), 0.5)
        
        assert calculate_note_y_position(5.0, 3.0, 900, 400) == \
               calculate_note_y_position(5.0, 3.0, 900, 400)
        
        # Test strike animation functions
        assert calculate_kick_strike_pulse(0.04, 0.08) == calculate_kick_strike_pulse(0.04, 0.08)
        assert calculate_strike_color_mix((100, 100, 100), 0.5) == \
               calculate_strike_color_mix((100, 100, 100), 0.5)
    
    def test_functions_dont_modify_inputs(self):
        """Functions should not modify their input parameters"""
        color = (255, 128, 64)
        original_color = color
        _ = apply_brightness_to_color(color, 0.5)
        assert color == original_color
        
        _ = calculate_strike_color_mix(color, 0.5)
        assert color == original_color
        
        note = DrumNote(38, 1.0, 100, 0, (255, 0, 0), "Test")
        original_lane = note.lane
        _ = is_note_in_highlight_zone(note, 0.5, 900, 60, 400)
        assert note.lane == original_lane  # Immutable


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
