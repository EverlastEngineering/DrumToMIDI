#!/usr/bin/env python3
"""
Tests for ModernGL renderer functional core

Tests pure functions that transform data for GPU rendering.
No GPU operations in these tests - only data transformations.
"""

import pytest
import numpy as np


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


class TestEndingImageAlpha:
    """Test ending image fade-in alpha calculation with hold period"""
    
    def test_before_fade_invisible(self):
        """Before fade starts, alpha should be 0.0"""
        from moderngl_renderer.core import calculate_ending_image_alpha
        # Fade starts at 10 - 4 - 1 = 5.0, so at 3.0 it's invisible
        alpha = calculate_ending_image_alpha(
            current_time=3.0,
            duration=10.0,
            fade_duration=4.0,
            hold_duration=1.0
        )
        assert alpha == 0.0
    
    def test_at_fade_start(self):
        """At fade start, alpha should be 0.0"""
        from moderngl_renderer.core import calculate_ending_image_alpha
        # Fade starts at 10 - 4 - 1 = 5.0
        alpha = calculate_ending_image_alpha(
            current_time=5.0,
            duration=10.0,
            fade_duration=4.0,
            hold_duration=1.0
        )
        assert alpha == 0.0
    
    def test_middle_of_fade(self):
        """Middle of fade should be 50% alpha"""
        from moderngl_renderer.core import calculate_ending_image_alpha
        # Fade from 5.0 to 9.0, middle is 7.0
        alpha = calculate_ending_image_alpha(
            current_time=7.0,
            duration=10.0,
            fade_duration=4.0,
            hold_duration=1.0
        )
        assert alpha == pytest.approx(0.5, abs=0.01)
    
    def test_end_of_fade_fully_visible(self):
        """At end of fade, alpha should be 1.0"""
        from moderngl_renderer.core import calculate_ending_image_alpha
        # Fade ends at 10 - 1 = 9.0
        alpha = calculate_ending_image_alpha(
            current_time=9.0,
            duration=10.0,
            fade_duration=4.0,
            hold_duration=1.0
        )
        assert alpha == 1.0
    
    def test_during_hold_period(self):
        """During hold period, alpha should remain 1.0"""
        from moderngl_renderer.core import calculate_ending_image_alpha
        # Hold period is 9.0 to 10.0
        alpha = calculate_ending_image_alpha(
            current_time=9.5,
            duration=10.0,
            fade_duration=4.0,
            hold_duration=1.0
        )
        assert alpha == 1.0
    
    def test_at_duration_end(self):
        """At end of duration, alpha should be 1.0"""
        from moderngl_renderer.core import calculate_ending_image_alpha
        alpha = calculate_ending_image_alpha(
            current_time=10.0,
            duration=10.0,
            fade_duration=4.0,
            hold_duration=1.0
        )
        assert alpha == 1.0
    
    def test_linear_fade_progression(self):
        """Fade should progress linearly"""
        from moderngl_renderer.core import calculate_ending_image_alpha
        duration = 10.0
        fade_duration = 4.0
        hold_duration = 1.0
        # Fade: 5.0 to 9.0
        
        alpha_at_0_pct = calculate_ending_image_alpha(5.0, duration, fade_duration, hold_duration)
        alpha_at_25_pct = calculate_ending_image_alpha(6.0, duration, fade_duration, hold_duration)
        alpha_at_50_pct = calculate_ending_image_alpha(7.0, duration, fade_duration, hold_duration)
        alpha_at_75_pct = calculate_ending_image_alpha(8.0, duration, fade_duration, hold_duration)
        alpha_at_100_pct = calculate_ending_image_alpha(9.0, duration, fade_duration, hold_duration)
        
        assert alpha_at_0_pct == pytest.approx(0.0, abs=0.01)
        assert alpha_at_25_pct == pytest.approx(0.25, abs=0.01)
        assert alpha_at_50_pct == pytest.approx(0.5, abs=0.01)
        assert alpha_at_75_pct == pytest.approx(0.75, abs=0.01)
        assert alpha_at_100_pct == pytest.approx(1.0, abs=0.01)
    
    def test_short_video_with_defaults(self):
        """Test with a short video duration"""
        from moderngl_renderer.core import calculate_ending_image_alpha
        # 6 second video: fade 1.0-5.0, hold 5.0-6.0
        alpha_before = calculate_ending_image_alpha(0.5, 6.0, 4.0, 1.0)
        alpha_at_start = calculate_ending_image_alpha(1.0, 6.0, 4.0, 1.0)
        alpha_middle = calculate_ending_image_alpha(3.0, 6.0, 4.0, 1.0)
        alpha_at_hold = calculate_ending_image_alpha(5.5, 6.0, 4.0, 1.0)
        
        assert alpha_before == 0.0
        assert alpha_at_start == 0.0
        assert alpha_middle == pytest.approx(0.5, abs=0.01)
        assert alpha_at_hold == 1.0


class TestImageDimensionsWithAspectRatio:
    """Test image scaling with aspect ratio preservation and margins"""
    
    def test_wide_image_limited_by_width(self):
        """Wide image should be constrained by width"""
        from moderngl_renderer.core import calculate_image_dimensions_with_aspect_ratio
        # 2000x1000 image (2:1 ratio) in 1920x1080 canvas with 30% margins
        # Available space: 1920*0.4 = 768w, 1080*0.4 = 432h
        # Image aspect 2:1 > available aspect 768/432=1.78, so width-limited
        w, h, x, y = calculate_image_dimensions_with_aspect_ratio(2000, 1000, 1920, 1080, 0.30)
        
        # Should scale to fit width: 768w, 384h
        assert w == 768
        assert h == 384
        # Centered: x=(1920-768)/2=576, y=(1080-384)/2=348
        assert x == 576
        assert y == 348
    
    def test_tall_image_limited_by_height(self):
        """Tall image should be constrained by height"""
        from moderngl_renderer.core import calculate_image_dimensions_with_aspect_ratio
        # 1000x2000 image (1:2 ratio) in 1920x1080 canvas with 30% margins
        # Available space: 768w, 432h
        # Image aspect 0.5 < available aspect 1.78, so height-limited
        w, h, x, y = calculate_image_dimensions_with_aspect_ratio(1000, 2000, 1920, 1080, 0.30)
        
        # Should scale to fit height: 216w, 432h
        assert w == 216
        assert h == 432
        # Centered: x=(1920-216)/2=852, y=(1080-432)/2=324
        assert x == 852
        assert y == 324
    
    def test_square_image(self):
        """Square image should scale uniformly"""
        from moderngl_renderer.core import calculate_image_dimensions_with_aspect_ratio
        # 1000x1000 square image in 1920x1080 canvas with 30% margins
        w, h, x, y = calculate_image_dimensions_with_aspect_ratio(1000, 1000, 1920, 1080, 0.30)
        
        # Height is limiting factor (432 < 768)
        assert w == 432
        assert h == 432
        assert x == (1920 - 432) // 2
        assert y == (1080 - 432) // 2
    
    def test_different_margin_percentage(self):
        """Test with 20% margins instead of 30%"""
        from moderngl_renderer.core import calculate_image_dimensions_with_aspect_ratio
        # With 20% margins, available space is 60% of canvas
        w, h, x, y = calculate_image_dimensions_with_aspect_ratio(1000, 1000, 1000, 1000, 0.20)
        
        # Available: 600x600, square fits exactly
        assert w == 600
        assert h == 600
        assert x == 200  # (1000-600)/2
        assert y == 200
    
    def test_aspect_ratio_preserved(self):
        """Verify aspect ratio is maintained"""
        from moderngl_renderer.core import calculate_image_dimensions_with_aspect_ratio
        original_w, original_h = 1920, 1080
        original_aspect = original_w / original_h
        
        w, h, x, y = calculate_image_dimensions_with_aspect_ratio(
            original_w, original_h, 800, 600, 0.25
        )
        
        result_aspect = w / h
        assert abs(result_aspect - original_aspect) < 0.01


class TestEasingFunctions:
    """Test easing functions for animations"""
    
    def test_ease_out_cubic_boundaries(self):
        """Ease-out cubic should map 0.0->0.0 and 1.0->1.0"""
        from moderngl_renderer.core import ease_out_cubic
        assert ease_out_cubic(0.0) == 0.0
        assert ease_out_cubic(1.0) == 1.0
    
    def test_ease_out_cubic_midpoint(self):
        """Ease-out cubic at 0.5 should be > 0.5 (faster start)"""
        from moderngl_renderer.core import ease_out_cubic
        result = ease_out_cubic(0.5)
        assert result > 0.5  # Should be ahead of linear at midpoint
        assert result == pytest.approx(0.875, abs=0.01)
    
    def test_ease_out_cubic_monotonic(self):
        """Ease-out cubic should be monotonically increasing"""
        from moderngl_renderer.core import ease_out_cubic
        values = [ease_out_cubic(t) for t in [0.0, 0.25, 0.5, 0.75, 1.0]]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1]


class TestEndingImageScrollPosition:
    """Test ending image Y position calculation with easing"""
    
    def test_before_animation_starts(self):
        """Before animation, image should be above screen"""
        from moderngl_renderer.core import calculate_ending_image_y_position
        # Duration 10s, fade 4s, hold 1s: animation starts at 5s
        y_pos = calculate_ending_image_y_position(3.0, 10.0, 4.0, 1.0, 0.5)
        # Should be at start position: 1.0 + 0.25 = 1.25 (above screen in OpenGL)
        assert y_pos == pytest.approx(1.25, abs=0.01)
    
    def test_at_animation_start(self):
        """At start of animation, should be at start position"""
        from moderngl_renderer.core import calculate_ending_image_y_position
        y_pos = calculate_ending_image_y_position(5.0, 10.0, 4.0, 1.0, 0.5)
        assert y_pos == pytest.approx(1.25, abs=0.01)
    
    def test_during_animation_moving_down(self):
        """During animation, should be moving toward center"""
        from moderngl_renderer.core import calculate_ending_image_y_position
        # At 7s (halfway through 4s animation from 5s to 9s)
        y_pos = calculate_ending_image_y_position(7.0, 10.0, 4.0, 1.0, 0.5)
        # Should be between start (1.25) and end (0.0)
        # With ease-out, should be most of the way there
        assert 0.0 < y_pos < 1.25
        assert y_pos < 0.5  # More than halfway due to ease-out
    
    def test_at_center(self):
        """At end of animation, should be centered"""
        from moderngl_renderer.core import calculate_ending_image_y_position
        # At 9s, animation complete (fade ends, hold starts)
        y_pos = calculate_ending_image_y_position(9.0, 10.0, 4.0, 1.0, 0.5)
        assert y_pos == pytest.approx(0.0, abs=0.01)
    
    def test_during_hold_stays_centered(self):
        """During hold period, should stay at center"""
        from moderngl_renderer.core import calculate_ending_image_y_position
        y_pos = calculate_ending_image_y_position(9.5, 10.0, 4.0, 1.0, 0.5)
        assert y_pos == pytest.approx(0.0, abs=0.01)
    
    def test_different_image_sizes(self):
        """Larger images should start further above screen"""
        from moderngl_renderer.core import calculate_ending_image_y_position
        # Small image (0.3 normalized height)
        y_small = calculate_ending_image_y_position(3.0, 10.0, 4.0, 1.0, 0.3)
        # Large image (0.8 normalized height)
        y_large = calculate_ending_image_y_position(3.0, 10.0, 4.0, 1.0, 0.8)
        # Larger image should start higher up (more positive in OpenGL)
        assert y_large > y_small
