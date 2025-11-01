#!/usr/bin/env python3
"""
Tests for animation system functional core

Tests pure functions for time-based animation calculations.
No GPU operations - only animation math.
"""

import pytest
from typing import List, Dict


class TestFrameGeneration:
    """Test frame generation from note data"""
    
    def test_generate_frame_notes(self):
        """Should filter notes visible at specific frame time"""
        from animation_core import generate_frame_notes
        
        # Notes with timing info
        notes = [
            {'time': 1.0, 'lane': 'hihat', 'velocity': 100},
            {'time': 2.0, 'lane': 'snare', 'velocity': 80},
            {'time': 3.0, 'lane': 'kick', 'velocity': 120},
            {'time': 5.0, 'lane': 'tom', 'velocity': 90},
        ]
        
        # Frame at time=2.5, looking ahead 3 seconds, behind 1 second
        frame_notes = generate_frame_notes(
            all_notes=notes,
            current_time=2.5,
            lookahead_time=3.0,
            lookbehind_time=1.0
        )
        
        # Should include notes from 1.5 to 5.5
        assert len(frame_notes) == 3
        assert frame_notes[0]['time'] == 2.0
        assert frame_notes[1]['time'] == 3.0
        assert frame_notes[2]['time'] == 5.0
    
    def test_note_to_rectangle(self):
        """Should convert note data to rectangle specification"""
        from animation_core import note_to_rectangle
        
        lanes = ['hihat', 'snare', 'kick', 'tom']
        
        note = {
            'time': 2.0,
            'lane': 'snare',
            'velocity': 100,
        }
        
        rect = note_to_rectangle(
            note=note,
            current_time=0.0,
            lanes=lanes,
            strike_line_y=0.7,
            fall_speed=1.0
        )
        
        # Should have correct lane position
        assert rect['x'] is not None
        assert rect['y'] > 0.7  # Above strike line (time=2.0 means 2 seconds before hit, higher Y in OpenGL)
        
        # Should have color based on lane
        assert rect['color'] is not None
        
        # Should have brightness based on velocity (mapped to 0.3-1.0 range)
        assert 0.0 <= rect['brightness'] <= 1.0
        # velocity=100 maps to: 0.3 + (100/127 * 0.7) ≈ 0.85
        expected_brightness = 0.3 + (100.0 / 127.0) * 0.7
        assert rect['brightness'] == pytest.approx(expected_brightness, abs=0.01)
        
        # Should have width based on lane (kick wider)
        assert rect['width'] > 0


class TestTimeCalculations:
    """Test time-based position calculations"""
    
    def test_frame_time_from_number(self):
        """Should calculate time from frame number"""
        from animation_core import frame_time_from_number
        
        # At 60 FPS
        assert frame_time_from_number(0, 60) == pytest.approx(0.0)
        assert frame_time_from_number(60, 60) == pytest.approx(1.0)
        assert frame_time_from_number(120, 60) == pytest.approx(2.0)
        assert frame_time_from_number(30, 60) == pytest.approx(0.5)
        
        # At 30 FPS
        assert frame_time_from_number(30, 30) == pytest.approx(1.0)
        assert frame_time_from_number(60, 30) == pytest.approx(2.0)
    
    def test_total_frames_from_duration(self):
        """Should calculate total frames from duration"""
        from animation_core import total_frames_from_duration
        
        # 3 seconds at 60 FPS
        assert total_frames_from_duration(3.0, 60) == 180
        
        # 1.5 seconds at 30 FPS
        assert total_frames_from_duration(1.5, 30) == 45
        
        # 10 seconds at 24 FPS
        assert total_frames_from_duration(10.0, 24) == 240


class TestNoteVisibilityWindow:
    """Test note visibility window calculations"""
    
    def test_calculate_visibility_window(self):
        """Should calculate time window for visible notes"""
        from animation_core import calculate_visibility_window
        
        # OpenGL coords: top=1.0, bottom=-1.0, strike line=-0.6, fall speed 1.0 unit/sec
        lookahead, lookbehind = calculate_visibility_window(
            strike_line_y=-0.6,
            screen_top=1.0,
            screen_bottom=-1.0,
            fall_speed=1.0
        )
        
        # Lookahead: time for note to travel from top to strike line
        # Distance = 1.0 - (-0.6) = 1.6
        assert lookahead == pytest.approx(1.6)
        
        # Lookbehind: time for note to travel from strike to bottom
        # Distance = -0.6 - (-1.0) = 0.4
        assert lookbehind == pytest.approx(0.4)
    
    def test_is_note_in_window(self):
        """Should determine if note is in visibility window"""
        from animation_core import is_note_in_window
        
        # Note at time 5.0, current time 3.0, window 3s ahead, 1s behind
        assert is_note_in_window(5.0, 3.0, 3.0, 1.0) == True  # 2s ahead
        assert is_note_in_window(2.5, 3.0, 3.0, 1.0) == True  # 0.5s behind
        
        # Outside window
        assert is_note_in_window(10.0, 3.0, 3.0, 1.0) == False  # Too far ahead
        assert is_note_in_window(1.0, 3.0, 3.0, 1.0) == False  # Too far behind


class TestVelocityMapping:
    """Test MIDI velocity to visual property mapping"""
    
    def test_velocity_to_brightness(self):
        """Should map MIDI velocity to brightness"""
        from animation_core import velocity_to_brightness
        
        # Full velocity = full brightness
        assert velocity_to_brightness(127) == pytest.approx(1.0)
        
        # Zero velocity = minimum brightness
        min_brightness = velocity_to_brightness(0)
        assert min_brightness > 0.0  # Never fully transparent
        assert min_brightness < 0.5
        
        # Mid velocity = mid brightness
        mid_brightness = velocity_to_brightness(64)
        assert 0.3 < mid_brightness < 0.7
    
    def test_lane_to_color(self):
        """Should map lane name to RGB color"""
        from animation_core import lane_to_color
        
        # Standard drum colors
        hihat = lane_to_color('hihat')
        snare = lane_to_color('snare')
        kick = lane_to_color('kick')
        tom = lane_to_color('tom')
        
        # All should be valid RGB tuples
        assert len(hihat) == 3
        assert all(0.0 <= c <= 1.0 for c in hihat)
        
        # Should be distinct colors
        colors = [hihat, snare, kick, tom]
        assert len(set(colors)) == 4  # All unique


class TestSceneComposition:
    """Test scene element composition"""
    
    def test_build_frame_scene(self):
        """Should compose complete frame scene"""
        from animation_core import build_frame_scene
        
        lanes = ['hihat', 'snare', 'kick', 'tom']
        notes = [
            {'time': 1.0, 'lane': 'hihat', 'velocity': 100},
            {'time': 1.5, 'lane': 'snare', 'velocity': 80},
        ]
        
        scene = build_frame_scene(
            notes=notes,
            current_time=0.0,
            lanes=lanes,
            strike_line_y=0.7,
            fall_speed=1.0
        )
        
        # Should include backgrounds, markers, strike line, and notes
        assert len(scene) > len(notes)
        
        # Should be list of rectangle specifications
        for element in scene:
            assert 'x' in element
            assert 'y' in element
            assert 'width' in element
            assert 'height' in element
            assert 'color' in element
            assert 'brightness' in element
