#!/usr/bin/env python3
"""
Tests for ModernGL renderer functional core

Tests pure functions that transform data for GPU rendering.
No GPU operations in these tests - only data transformations.
"""

import pytest
import numpy as np
from typing import Tuple


# Tests will drive the design of the functional core
class TestRectangleDataTransformations:
    """Test pure functions for rectangle data preparation"""
    
    def test_apply_brightness_to_color(self):
        """Should multiply RGB values by brightness factor"""
        from moderngl_renderer.core import apply_brightness_to_color
        
        # Full brightness
        assert apply_brightness_to_color((1.0, 0.5, 0.0), 1.0) == (1.0, 0.5, 0.0)
        
        # Half brightness
        assert apply_brightness_to_color((1.0, 0.5, 0.0), 0.5) == (0.5, 0.25, 0.0)
        
        # Zero brightness
        assert apply_brightness_to_color((1.0, 0.5, 0.0), 0.0) == (0.0, 0.0, 0.0)
    
    def test_normalize_coords_topleft_to_bottomleft(self):
        """Should convert top-left origin to bottom-left (OpenGL convention)"""
        from moderngl_renderer.core import normalize_coords_topleft_to_bottomleft
        
        # Top-left: x=0, y=1, w=0.5, h=0.2
        # Bottom-left should be: x=0, y=0.8 (1.0 - 0.2), w=0.5, h=0.2
        result = normalize_coords_topleft_to_bottomleft(0.0, 1.0, 0.5, 0.2)
        assert result == (0.0, 0.8, 0.5, 0.2)
        
        # Center rectangle
        result = normalize_coords_topleft_to_bottomleft(-0.1, 0.1, 0.2, 0.2)
        assert result == (-0.1, -0.1, 0.2, 0.2)
    
    def test_normalized_to_pixel_size(self):
        """Should convert normalized width/height to pixel dimensions"""
        from moderngl_renderer.core import normalized_to_pixel_size
        
        # Full screen width at 1920x1080
        w_px, h_px = normalized_to_pixel_size(2.0, 2.0, 1920, 1080)
        assert w_px == 1920.0
        assert h_px == 1080.0
        
        # Half screen
        w_px, h_px = normalized_to_pixel_size(1.0, 1.0, 1920, 1080)
        assert w_px == 960.0
        assert h_px == 540.0
        
        # Quarter width, half height
        w_px, h_px = normalized_to_pixel_size(0.5, 1.0, 1920, 1080)
        assert w_px == 480.0  # 0.5 / 2.0 * 1920 = 480
        assert h_px == 540.0
    
    def test_prepare_rectangle_instance_data(self):
        """Should prepare all GPU instance data from rectangle spec"""
        from moderngl_renderer.core import prepare_rectangle_instance_data
        
        rect = {
            'x': -0.5, 
            'y': 0.5, 
            'width': 0.2, 
            'height': 0.1,
            'color': (1.0, 0.0, 0.0),
            'brightness': 0.8
        }
        
        result = prepare_rectangle_instance_data(rect, screen_width=1920, screen_height=1080)
        
        # Should contain brightened color
        assert result['color'] == (0.8, 0.0, 0.0)
        
        # Should contain bottom-left coords
        assert result['rect'] == (-0.5, 0.4, 0.2, 0.1)
        
        # Should contain pixel sizes
        assert result['size_pixels'][0] == pytest.approx(192.0)  # 0.2 * 1920 / 2
        assert result['size_pixels'][1] == pytest.approx(54.0)   # 0.1 * 1080 / 2
    
    def test_batch_rectangle_data(self):
        """Should batch multiple rectangles into numpy arrays"""
        from moderngl_renderer.core import batch_rectangle_data
        
        rectangles = [
            {'x': 0, 'y': 0, 'width': 0.1, 'height': 0.1, 
             'color': (1, 0, 0), 'brightness': 1.0},
            {'x': 0.5, 'y': 0.5, 'width': 0.2, 'height': 0.1, 
             'color': (0, 1, 0), 'brightness': 0.5},
        ]
        
        colors, rects, sizes, flags = batch_rectangle_data(rectangles, 1920, 1080)
        
        # Check array shapes
        assert colors.shape == (2, 3)
        assert rects.shape == (2, 4)
        assert sizes.shape == (2, 2)
        assert flags.shape == (2,)
        
        # Check array dtypes
        assert colors.dtype == np.float32
        assert rects.dtype == np.float32
        assert sizes.dtype == np.float32
        assert flags.dtype == np.float32
        
        # Check first rectangle color (full brightness red)
        np.testing.assert_array_equal(colors[0], [1.0, 0.0, 0.0])
        
        # Check second rectangle color (half brightness green)
        np.testing.assert_array_equal(colors[1], [0.0, 0.5, 0.0])


class TestNotePositionCalculations:
    """Test pure functions for note positioning in falling animation"""
    
    def test_calculate_note_y_position(self):
        """Should calculate Y position based on time until hit - notes fall DOWN from top"""
        from moderngl_renderer.core import calculate_note_y_position
        
        # Note hits at strike line (y=0.7), falls at 1.0 units/second
        # 2 seconds before hit should be ABOVE strike line (higher Y value)
        y_pos = calculate_note_y_position(
            time_until_hit=2.0,
            strike_line_y=0.7,
            fall_speed=1.0
        )
        assert y_pos == pytest.approx(2.7)  # 0.7 + 2.0 (above)
        
        # At strike line (time=0)
        y_pos = calculate_note_y_position(0.0, 0.7, 1.0)
        assert y_pos == pytest.approx(0.7)
        
        # After hit (continues falling down, below strike line)
        y_pos = calculate_note_y_position(-1.0, 0.7, 1.0)
        assert y_pos == pytest.approx(-0.3)  # 0.7 - 1.0 (below)
    
    def test_calculate_note_alpha_fade(self):
        """Should calculate alpha based on position after strike - OpenGL coords"""
        from moderngl_renderer.core import calculate_note_alpha_fade
        
        strike_line_y = -0.6
        screen_bottom = -1.0
        
        # At strike line: full opacity
        alpha = calculate_note_alpha_fade(-0.6, strike_line_y, screen_bottom)
        assert alpha == pytest.approx(1.0)
        
        # Halfway to bottom: faded to 0.6
        alpha = calculate_note_alpha_fade(-0.8, strike_line_y, screen_bottom)
        assert alpha == pytest.approx(0.6)
        
        # At bottom: minimum opacity (0.2)
        alpha = calculate_note_alpha_fade(-1.0, strike_line_y, screen_bottom)
        assert alpha == pytest.approx(0.2)
        
        # Above strike line: always 1.0
        alpha = calculate_note_alpha_fade(0.5, strike_line_y, screen_bottom)
        assert alpha == pytest.approx(1.0)
    
    def test_is_note_visible(self):
        """Should determine if note is in visible range"""
        from moderngl_renderer.core import is_note_visible
        
        # Note visible if y between -1.0 and 1.0 (normalized coords)
        assert is_note_visible(0.0) == True
        assert is_note_visible(0.9) == True
        assert is_note_visible(-0.9) == True
        
        # Outside visible range
        assert is_note_visible(1.1) == False
        assert is_note_visible(-1.1) == False
        assert is_note_visible(2.0) == False


class TestLaneCalculations:
    """Test pure functions for drum lane positioning"""
    
    def test_get_lane_x_position(self):
        """Should return X position for drum lane"""
        from moderngl_renderer.core import get_lane_x_position
        
        # 4 lanes equally spaced
        lanes = ['hihat', 'snare', 'kick', 'tom']
        positions = [get_lane_x_position(lane, lanes) for lane in lanes]
        
        # Should be evenly distributed
        assert len(set(positions)) == 4  # All unique
        assert positions == sorted(positions)  # Ascending order
        
        # Hihat should be leftmost, tom rightmost
        assert positions[0] < positions[-1]
    
    def test_get_note_width_for_type(self):
        """Should return appropriate width for note type"""
        from moderngl_renderer.core import get_note_width_for_type
        
        # Kick notes are wider
        kick_width = get_note_width_for_type('kick')
        snare_width = get_note_width_for_type('snare')
        
        assert kick_width > snare_width
        
        # All other notes same width
        hihat_width = get_note_width_for_type('hihat')
        tom_width = get_note_width_for_type('tom')
        
        assert hihat_width == snare_width == tom_width


class TestStrikeLineAndMarkers:
    """Test pure functions for strike line and lane marker generation"""
    
    def test_create_strike_line(self):
        """Should create strike line rectangle specification"""
        from moderngl_renderer.core import create_strike_line
        
        strike_line = create_strike_line(
            y_position=0.7,
            color=(1.0, 1.0, 1.0),
            thickness=0.01
        )
        
        # Should span full screen width
        assert strike_line['x'] == pytest.approx(-1.0)
        assert strike_line['width'] == pytest.approx(2.0)
        
        # Should be at correct position with correct thickness
        assert strike_line['y'] == pytest.approx(0.7)
        assert strike_line['height'] == pytest.approx(0.01)
        
        # Should have correct color and full brightness
        assert strike_line['color'] == (1.0, 1.0, 1.0)
        assert strike_line['brightness'] == 1.0
    
    def test_create_lane_markers(self):
        """Should create lane divider rectangles"""
        from moderngl_renderer.core import create_lane_markers
        
        lanes = ['hihat', 'snare', 'kick', 'tom']
        markers = create_lane_markers(
            lanes=lanes,
            color=(0.3, 0.3, 0.3),
            thickness=0.005
        )
        
        # Should have one less marker than lanes (dividers between lanes)
        assert len(markers) == 3
        
        # All markers should be vertical (tall)
        for marker in markers:
            assert marker['height'] == pytest.approx(2.0)  # Full screen height
            assert marker['width'] == pytest.approx(0.005)  # Thin divider
        
        # All markers should have same color
        for marker in markers:
            assert marker['color'] == (0.3, 0.3, 0.3)
            assert marker['brightness'] == 1.0
    
    def test_create_background_lanes(self):
        """Should create background rectangles for each lane"""
        from moderngl_renderer.core import create_background_lanes
        
        lanes = ['hihat', 'snare', 'kick', 'tom']
        backgrounds = create_background_lanes(
            lanes=lanes,
            colors={
                'hihat': (0.0, 0.1, 0.1),
                'snare': (0.1, 0.0, 0.0),
                'kick': (0.1, 0.05, 0.0),
                'tom': (0.0, 0.1, 0.0)
            }
        )
        
        # Should have one background per lane
        assert len(backgrounds) == 4
        
        # All backgrounds should be full screen height
        for bg in backgrounds:
            assert bg['height'] == pytest.approx(2.0)
        
        # Each should have distinct color
        colors = [bg['color'] for bg in backgrounds]
        assert len(set(colors)) == 4  # All unique
        
        # Background should have low brightness
        for bg in backgrounds:
            assert bg['brightness'] == pytest.approx(0.3)
    
    def test_create_lane_markers_single_lane(self):
        """Should return empty list for single lane (no dividers needed)"""
        from moderngl_renderer.core import create_lane_markers
        
        markers = create_lane_markers(
            lanes=['kick'],
            color=(1.0, 1.0, 1.0),
            thickness=0.003
        )
        
        assert markers == []
