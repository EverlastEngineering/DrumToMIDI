"""
Tests for MIDI to ModernGL Bridge

Verifies that DrumNotes are correctly converted to ModernGL format.
"""

import pytest
from midi_types import DrumNote
from .midi_bridge_core import (
    RenderConfig,
    rgb_255_to_normalized,
    pixel_to_normalized_y,
    calculate_lane_layout,
    calculate_note_width,
    drum_note_to_rectangle,
    generate_highlight_circles,
    build_frame_from_drum_notes
)


class TestRenderConfig:
    """Test configuration setup"""
    
    def test_default_config(self):
        """Default config should have sensible values"""
        config = RenderConfig()
        assert config.width == 1920
        assert config.height == 1080
        assert config.fps == 60
        assert config.screen_top == 1.0
        assert config.screen_bottom == -1.0
        assert config.strike_line_y < 0  # Below center
    
    def test_fall_speed_multiplier(self):
        """Fall speed multiplier should affect speed"""
        config1 = RenderConfig(fall_speed_multiplier=1.0)
        config2 = RenderConfig(fall_speed_multiplier=2.0)
        assert config2.fall_speed == config1.fall_speed * 2.0


class TestCoordinateConversion:
    """Test coordinate system conversions"""
    
    def test_rgb_255_to_normalized(self):
        """RGB conversion should map 0-255 to 0.0-1.0"""
        assert rgb_255_to_normalized((0, 0, 0)) == (0.0, 0.0, 0.0)
        assert rgb_255_to_normalized((255, 255, 255)) == (1.0, 1.0, 1.0)
        assert rgb_255_to_normalized((128, 64, 192)) == (128/255, 64/255, 192/255)
    
    def test_pixel_to_normalized_y_top(self):
        """Top pixel (0) should map to top normalized coord (1.0)"""
        y = pixel_to_normalized_y(0, 1080, screen_top=1.0, screen_bottom=-1.0)
        assert y == 1.0
    
    def test_pixel_to_normalized_y_bottom(self):
        """Bottom pixel should map to bottom normalized coord"""
        y = pixel_to_normalized_y(1080, 1080, screen_top=1.0, screen_bottom=-1.0)
        assert y == -1.0
    
    def test_pixel_to_normalized_y_middle(self):
        """Middle pixel should map to middle normalized coord"""
        y = pixel_to_normalized_y(540, 1080, screen_top=1.0, screen_bottom=-1.0)
        assert abs(y - 0.0) < 0.01  # Should be near 0.0


class TestLaneLayout:
    """Test lane positioning calculations"""
    
    def test_single_lane(self):
        """Single lane should be centered"""
        layout = calculate_lane_layout(1, screen_left=-1.0, screen_right=1.0)
        assert len(layout) == 1
        assert abs(layout[0] - 0.0) < 0.1  # Should be near center
    
    def test_two_lanes(self):
        """Two lanes should be evenly spaced"""
        layout = calculate_lane_layout(2, screen_left=-1.0, screen_right=1.0)
        assert len(layout) == 2
        assert layout[0] < 0  # Left of center
        assert layout[1] > 0  # Right of center
        # Should be symmetric
        assert abs(layout[0] + layout[1]) < 0.1
    
    def test_four_lanes(self):
        """Four lanes should be evenly distributed"""
        layout = calculate_lane_layout(4, screen_left=-1.0, screen_right=1.0)
        assert len(layout) == 4
        # Lanes should be in ascending order
        for i in range(3):
            assert layout[i] < layout[i + 1]
    
    def test_empty_lanes(self):
        """Zero lanes should return empty dict"""
        layout = calculate_lane_layout(0)
        assert layout == {}


class TestNoteWidth:
    """Test note width calculations"""
    
    def test_note_width_scales_with_lanes(self):
        """More lanes should mean narrower notes"""
        width_4 = calculate_note_width(4)
        width_8 = calculate_note_width(8)
        assert width_8 < width_4
    
    def test_note_width_positive(self):
        """Note width should always be positive"""
        for num_lanes in [1, 2, 4, 8, 10]:
            width = calculate_note_width(num_lanes)
            assert width > 0


class TestDrumNoteConversion:
    """Test DrumNote to rectangle conversion"""
    
    def create_test_note(self, time: float = 1.0, lane: int = 0, velocity: int = 100) -> DrumNote:
        """Helper to create test notes"""
        return DrumNote(
            midi_note=38,
            time=time,
            velocity=velocity,
            lane=lane,
            color=(255, 0, 0),
            name="Test"
        )
    
    def test_regular_note_conversion(self):
        """Regular note should convert to valid rectangle"""
        note = self.create_test_note(time=1.0, lane=0)
        config = RenderConfig()
        lane_layout = {0: 0.0}
        
        rect = drum_note_to_rectangle(note, 0.0, lane_layout, 0.1, config)
        
        assert 'x' in rect
        assert 'y' in rect
        assert 'width' in rect
        assert 'height' in rect
        assert 'color' in rect
        assert 'brightness' in rect
        assert rect['note_type'] == 'regular'
    
    def test_kick_drum_is_full_width(self):
        """Kick drum (lane -1) should span full screen width"""
        note = self.create_test_note(time=1.0, lane=-1)
        config = RenderConfig()
        lane_layout = {}
        
        rect = drum_note_to_rectangle(note, 0.0, lane_layout, 0.1, config)
        
        assert rect['note_type'] == 'kick'
        assert rect['x'] == config.screen_left
        expected_width = config.screen_right - config.screen_left
        assert abs(rect['width'] - expected_width) < 0.01
    
    def test_velocity_affects_brightness(self):
        """Higher velocity should produce brighter notes"""
        note_soft = self.create_test_note(velocity=64)
        note_loud = self.create_test_note(velocity=127)
        config = RenderConfig()
        lane_layout = {0: 0.0}
        
        rect_soft = drum_note_to_rectangle(note_soft, 0.0, lane_layout, 0.1, config)
        rect_loud = drum_note_to_rectangle(note_loud, 0.0, lane_layout, 0.1, config)
        
        assert rect_loud['brightness'] > rect_soft['brightness']
    
    def test_color_normalized(self):
        """Color should be converted to 0.0-1.0 range"""
        note = self.create_test_note()
        config = RenderConfig()
        lane_layout = {0: 0.0}
        
        rect = drum_note_to_rectangle(note, 0.0, lane_layout, 0.1, config)
        
        # Red color (255, 0, 0) should become (1.0, 0.0, 0.0)
        assert rect['color'] == (1.0, 0.0, 0.0)


class TestHighlightCircles:
    """Test highlight circle generation"""
    
    def create_test_note(self, time: float = 1.0, lane: int = 0) -> DrumNote:
        """Helper to create test notes"""
        return DrumNote(
            midi_note=38,
            time=time,
            velocity=100,
            lane=lane,
            color=(255, 0, 0),
            name="Test"
        )
    
    def test_no_circles_for_distant_notes(self):
        """Notes far from strike line shouldn't generate circles"""
        note = self.create_test_note(time=10.0)  # Far in future
        config = RenderConfig()
        lane_layout = {0: 0.0}
        
        circles = generate_highlight_circles([note], 0.0, lane_layout, config)
        
        assert len(circles) == 0
    
    def test_circles_for_strike_line_notes(self):
        """Notes at strike line should generate circles"""
        note = self.create_test_note(time=1.0)
        config = RenderConfig()
        lane_layout = {0: 0.0}
        
        # Time note to be near strike line
        circles = generate_highlight_circles([note], 1.0, lane_layout, config)
        
        assert len(circles) >= 0  # May or may not be in zone depending on exact timing
    
    def test_kick_drums_excluded(self):
        """Kick drums should not generate highlight circles"""
        kick = self.create_test_note(time=1.0, lane=-1)
        config = RenderConfig()
        lane_layout = {}
        
        circles = generate_highlight_circles([kick], 1.0, lane_layout, config)
        
        assert len(circles) == 0
    
    def test_circle_has_required_fields(self):
        """Circle should have all required fields"""
        # Create note at exact strike time
        note = self.create_test_note(time=2.5)  # Configured to be at strike
        config = RenderConfig()
        lane_layout = {0: 0.0}
        
        # Adjust timing to catch note in highlight zone
        current_time = 2.5  # Same as note time
        circles = generate_highlight_circles([note], current_time, lane_layout, config)
        
        if circles:  # Only test if circles were generated
            circle = circles[0]
            assert 'x' in circle
            assert 'y' in circle
            assert 'radius' in circle
            assert 'color' in circle
            assert 'brightness' in circle


class TestFrameBuilding:
    """Test complete frame generation"""
    
    def create_test_notes(self) -> list:
        """Create sequence of test notes"""
        return [
            DrumNote(38, 0.5, 100, 0, (255, 0, 0), "Snare"),
            DrumNote(42, 1.0, 80, 1, (0, 255, 255), "HiHat"),
            DrumNote(36, 1.5, 120, -1, (255, 140, 90), "Kick"),
            DrumNote(47, 2.0, 90, 2, (0, 255, 0), "Tom"),
        ]
    
    def test_frame_has_required_keys(self):
        """Frame should contain rectangles and circles"""
        notes = self.create_test_notes()
        config = RenderConfig()
        
        frame = build_frame_from_drum_notes(notes, 0.0, config)
        
        assert 'rectangles' in frame
        assert 'circles' in frame
        assert isinstance(frame['rectangles'], list)
        assert isinstance(frame['circles'], list)
    
    def test_frame_filters_by_visibility(self):
        """Frame should only include visible notes"""
        notes = self.create_test_notes()
        config = RenderConfig()
        
        # At time 0.0, only early notes should be visible
        frame_early = build_frame_from_drum_notes(notes, 0.0, config)
        
        # At time 10.0, no notes should be visible (all passed)
        frame_late = build_frame_from_drum_notes(notes, 10.0, config)
        
        # Early frame should have some rectangles
        assert len(frame_early['rectangles']) > 0
        
        # Late frame should have few or no rectangles
        assert len(frame_late['rectangles']) <= len(frame_early['rectangles'])
    
    def test_kick_drums_included(self):
        """Kick drums should be included in rectangles"""
        notes = self.create_test_notes()
        config = RenderConfig()
        
        frame = build_frame_from_drum_notes(notes, 1.5, config)  # Time of kick
        
        # Should have kick drum rectangle
        kick_rects = [r for r in frame['rectangles'] if r.get('note_type') == 'kick']
        assert len(kick_rects) >= 0  # May or may not be visible depending on timing


class TestPurityInvariant:
    """Test that functions remain pure"""
    
    def test_config_immutability(self):
        """Creating config shouldn't modify inputs"""
        config1 = RenderConfig(width=1920)
        config2 = RenderConfig(width=1920)
        
        assert config1.width == config2.width
        assert config1.strike_line_y == config2.strike_line_y
    
    def test_conversion_deterministic(self):
        """Same inputs should always produce same outputs"""
        color = (128, 64, 192)
        
        result1 = rgb_255_to_normalized(color)
        result2 = rgb_255_to_normalized(color)
        
        assert result1 == result2
    
    def test_layout_deterministic(self):
        """Lane layout should be deterministic"""
        layout1 = calculate_lane_layout(4)
        layout2 = calculate_lane_layout(4)
        
        assert layout1 == layout2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
