"""
ModernGL Renderer - Functional Core

Pure functions for data transformations.
No side effects, no GPU operations - only calculations.

Follows functional core, imperative shell pattern:
- This module: Pure transformations (testable, predictable)
- moderngl_shell.py: GPU operations (side effects)
"""

import numpy as np
from typing import Tuple, List, Dict, Any


# ============================================================================
# Color and Brightness Transformations
# ============================================================================

def apply_brightness_to_color(color: Tuple[float, float, float], brightness: float) -> Tuple[float, float, float]:
    """Pure function: Apply brightness multiplier to RGB color
    
    Args:
        color: RGB tuple (0.0 to 1.0 per channel)
        brightness: Multiplier (0.0 to 1.0)
    
    Returns:
        Brightened RGB tuple
    """
    return tuple(c * brightness for c in color)


# ============================================================================
# Coordinate System Transformations
# ============================================================================

def normalize_coords_topleft_to_bottomleft(
    x: float, y: float, width: float, height: float
) -> Tuple[float, float, float, float]:
    """Convert top-left origin coordinates to bottom-left (OpenGL convention)
    
    Args:
        x, y: Top-left corner position (normalized coords -1 to 1)
        width, height: Rectangle dimensions (normalized coords)
    
    Returns:
        (x, y, width, height) with y adjusted to bottom-left
    """
    # In top-left system, y increases downward
    # In bottom-left system, y increases upward
    # So bottom-left y = top-left y - height
    return (x, y - height, width, height)


def normalized_to_pixel_size(
    norm_width: float, norm_height: float, 
    screen_width: int, screen_height: int
) -> Tuple[float, float]:
    """Convert normalized dimensions to pixel dimensions
    
    Args:
        norm_width, norm_height: Dimensions in normalized coords (-1 to 1 range = 2.0 units)
        screen_width, screen_height: Screen dimensions in pixels
    
    Returns:
        (width_pixels, height_pixels)
    """
    # Normalized coords span -1 to 1 (2.0 units total)
    w_pixels = (norm_width / 2.0) * screen_width
    h_pixels = (norm_height / 2.0) * screen_height
    return (w_pixels, h_pixels)


# ============================================================================
# Rectangle Data Preparation
# ============================================================================

def prepare_rectangle_instance_data(
    rect: Dict[str, Any], 
    screen_width: int, 
    screen_height: int
) -> Dict[str, Any]:
    """Prepare GPU instance data for a single rectangle
    
    Args:
        rect: Dictionary with 'x', 'y', 'width', 'height', 'color', 'brightness'
        screen_width, screen_height: Screen dimensions in pixels
    
    Returns:
        Dictionary with 'color', 'rect', 'size_pixels' ready for GPU
    """
    # Apply brightness to color
    brightness = rect.get('brightness', 1.0)
    color = apply_brightness_to_color(rect['color'], brightness)
    
    # Convert coordinates
    rect_coords = normalize_coords_topleft_to_bottomleft(
        rect['x'], rect['y'], rect['width'], rect['height']
    )
    
    # Calculate pixel size for anti-aliasing
    size_pixels = normalized_to_pixel_size(
        rect['width'], rect['height'], 
        screen_width, screen_height
    )
    
    return {
        'color': color,
        'rect': rect_coords,
        'size_pixels': size_pixels
    }


def batch_rectangle_data(
    rectangles: List[Dict[str, Any]], 
    screen_width: int, 
    screen_height: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Batch multiple rectangles into numpy arrays for GPU upload
    
    Args:
        rectangles: List of rectangle specifications
        screen_width, screen_height: Screen dimensions in pixels
    
    Returns:
        (colors, rects, sizes) - numpy arrays ready for GPU buffers
        - colors: (N, 3) float32 array
        - rects: (N, 4) float32 array 
        - sizes: (N, 2) float32 array
    """
    prepared = [
        prepare_rectangle_instance_data(rect, screen_width, screen_height)
        for rect in rectangles
    ]
    
    colors = np.array([p['color'] for p in prepared], dtype='f4')
    rects = np.array([p['rect'] for p in prepared], dtype='f4')
    sizes = np.array([p['size_pixels'] for p in prepared], dtype='f4')
    
    return colors, rects, sizes


# ============================================================================
# Note Position and Animation Calculations
# ============================================================================

def calculate_note_y_position(
    time_until_hit: float, 
    strike_line_y: float, 
    fall_speed: float
) -> float:
    """Calculate Y position of falling note based on timing
    
    Args:
        time_until_hit: Seconds until note reaches strike line (negative = after hit)
        strike_line_y: Y coordinate of strike line (normalized coords)
        fall_speed: Speed of note fall in units per second
    
    Returns:
        Y position in normalized coordinates
    """
    # Distance = speed * time
    # Negative time means note has passed strike line (continues falling)
    distance_from_strike = -time_until_hit * fall_speed
    return strike_line_y + distance_from_strike


def calculate_note_alpha_fade(
    note_y: float,
    strike_line_y: float,
    screen_bottom: float
) -> float:
    """Calculate note alpha based on position after strike line
    
    Args:
        note_y: Current Y position of note
        strike_line_y: Y position of strike line
        screen_bottom: Y position of screen bottom
    
    Returns:
        Alpha value 0.2 to 1.0
    """
    # Before strike line: always full opacity
    if note_y <= strike_line_y:
        return 1.0
    
    # After strike line: fade from 1.0 to 0.2
    distance_after_strike = note_y - strike_line_y
    max_distance = screen_bottom - strike_line_y
    fade_progress = min(distance_after_strike / max_distance, 1.0)
    
    # Fade from 1.0 to 0.2 (never fully transparent)
    return 1.0 - (0.8 * fade_progress)


def is_note_visible(note_y: float, screen_top: float = -1.0, screen_bottom: float = 1.0) -> bool:
    """Check if note is within visible screen bounds
    
    Args:
        note_y: Y position of note
        screen_top: Top of screen in normalized coords
        screen_bottom: Bottom of screen in normalized coords
    
    Returns:
        True if note is visible
    """
    return screen_top <= note_y <= screen_bottom


# ============================================================================
# Drum Lane Calculations
# ============================================================================

def get_lane_x_position(lane: str, all_lanes: List[str]) -> float:
    """Calculate X position for a drum lane
    
    Args:
        lane: Lane name (e.g., 'hihat', 'snare', 'kick', 'tom')
        all_lanes: List of all lane names in order
    
    Returns:
        X position in normalized coordinates
    """
    num_lanes = len(all_lanes)
    lane_index = all_lanes.index(lane)
    
    # Distribute lanes evenly across screen width
    # Range: -0.8 to 0.8 (leave margins on edges)
    total_width = 1.6
    lane_spacing = total_width / num_lanes
    start_x = -0.8 + (lane_spacing / 2)
    
    return start_x + (lane_index * lane_spacing)


def get_note_width_for_type(note_type: str) -> float:
    """Get appropriate width for note type
    
    Args:
        note_type: Type of drum note
    
    Returns:
        Width in normalized coordinates
    """
    # Kick notes are wider
    if note_type == 'kick':
        return 0.25
    
    # All other notes standard width
    return 0.15


def get_note_height() -> float:
    """Get standard note height
    
    Returns:
        Height in normalized coordinates
    """
    return 0.06
