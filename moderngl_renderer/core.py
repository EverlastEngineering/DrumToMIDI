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
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Batch multiple rectangles into numpy arrays for GPU upload
    
    Args:
        rectangles: List of rectangle specifications
        screen_width, screen_height: Screen dimensions in pixels
    
    Returns:
        (colors, rects, sizes, flags) - numpy arrays ready for GPU buffers
        - colors: (N, 3) float32 array
        - rects: (N, 4) float32 array 
        - sizes: (N, 2) float32 array
        - flags: (N,) float32 array (1.0 = no_outline, 0.0 = normal)
    """
    prepared = [
        prepare_rectangle_instance_data(rect, screen_width, screen_height)
        for rect in rectangles
    ]
    
    colors = np.array([p['color'] for p in prepared], dtype='f4')
    rects = np.array([p['rect'] for p in prepared], dtype='f4')
    sizes = np.array([p['size_pixels'] for p in prepared], dtype='f4')
    flags = np.array([1.0 if rect.get('no_outline', False) else 0.0 for rect in rectangles], dtype='f4')
    
    return colors, rects, sizes, flags


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
    # Positive time_until_hit means note is in future (ABOVE strike line in screen space)
    # Negative time_until_hit means note is in past (BELOW strike line, already hit)
    # In OpenGL: higher Y = top of screen, lower Y = bottom
    distance_from_strike = time_until_hit * fall_speed
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
    # In OpenGL coords: higher Y = top, lower Y = bottom
    # Notes above strike line (note_y > strike_line_y): full opacity
    if note_y >= strike_line_y:
        return 1.0
    
    # Notes below strike line (already hit): fade from 1.0 to 0.2
    distance_after_strike = strike_line_y - note_y
    max_distance = strike_line_y - screen_bottom
    fade_progress = min(distance_after_strike / max_distance, 1.0)
    
    # Fade from 1.0 to 0.2 (never fully transparent)
    return 1.0 - (0.8 * fade_progress)


def is_note_visible(note_y: float, note_height: float = 0.06, screen_top: float = 1.0, screen_bottom: float = -1.0) -> bool:
    """Check if note is within visible screen bounds
    
    Args:
        note_y: Y position of note (top-left corner)
        note_height: Height of note
        screen_top: Top of screen in normalized coords (higher Y)
        screen_bottom: Bottom of screen in normalized coords (lower Y)
    
    Returns:
        True if note is visible (any part on screen)
    """
    note_bottom = note_y - note_height
    # Note visible if bottom edge is below screen top AND top edge is above screen bottom
    return note_bottom <= screen_top and note_y >= screen_bottom


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


# ============================================================================
# Strike Line and Lane Markers
# ============================================================================

def create_strike_line(
    y_position: float, 
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    thickness: float = 0.01
) -> Dict[str, Any]:
    """Create strike line rectangle specification
    
    Args:
        y_position: Y coordinate of strike line (normalized coords)
        color: RGB color tuple
        thickness: Line thickness (normalized coords)
    
    Returns:
        Rectangle specification dict
    """
    return {
        'x': -1.0,  # Left edge of screen
        'y': y_position,
        'width': 2.0,  # Full screen width
        'height': thickness,
        'color': color,
        'brightness': 1.0
    }


def create_lane_markers(
    lanes: List[str],
    color: Tuple[float, float, float] = (0.3, 0.3, 0.3),
    thickness: float = 0.005
) -> List[Dict[str, Any]]:
    """Create lane divider markers
    
    Args:
        lanes: List of lane names
        color: RGB color for dividers
        thickness: Divider thickness (normalized coords)
    
    Returns:
        List of rectangle specifications for dividers
    """
    if len(lanes) <= 1:
        return []
    
    markers = []
    
    # Create dividers between lanes
    for i in range(len(lanes) - 1):
        # Get X positions of adjacent lanes
        x1 = get_lane_x_position(lanes[i], lanes)
        x2 = get_lane_x_position(lanes[i + 1], lanes)
        
        # Place divider between them
        divider_x = (x1 + x2) / 2.0 - (thickness / 2.0)
        
        markers.append({
            'x': divider_x,
            'y': 1.0,  # Top of screen
            'width': thickness,
            'height': 2.0,  # Full screen height
            'color': color,
            'brightness': 1.0
        })
    
    return markers


def create_background_lanes(
    lanes: List[str],
    colors: Dict[str, Tuple[float, float, float]],
    brightness: float = 0.3
) -> List[Dict[str, Any]]:
    """Create background rectangles for each lane
    
    Args:
        lanes: List of lane names
        colors: Dictionary mapping lane name to RGB color
        brightness: Brightness multiplier for backgrounds
    
    Returns:
        List of rectangle specifications for lane backgrounds
    """
    backgrounds = []
    
    # Calculate lane width
    num_lanes = len(lanes)
    total_width = 1.6  # Same as in get_lane_x_position
    lane_width = total_width / num_lanes
    
    for lane in lanes:
        lane_center_x = get_lane_x_position(lane, lanes)
        lane_left_x = lane_center_x - (lane_width / 2.0)
        
        backgrounds.append({
            'x': lane_left_x,
            'y': 1.0,  # Top of screen
            'width': lane_width,
            'height': 2.0,  # Full screen height
            'color': colors.get(lane, (0.1, 0.1, 0.1)),
            'brightness': brightness
        })
    
    return backgrounds


# ============================================================================
# Ending Image Fade Logic
# ============================================================================

def calculate_ending_image_alpha(
    current_time: float,
    duration: float,
    fade_duration: float = 4.0,
    hold_duration: float = 1.0
) -> float:
    """Calculate alpha value for ending image fade-in effect
    
    Pure function that determines transparency of ending image based on time.
    Fades in over the last N seconds of video, then holds at full opacity.
    
    Args:
        current_time: Current playback time in seconds
        duration: Total video duration in seconds
        fade_duration: Duration of fade-in effect in seconds (default: 4.0)
        hold_duration: Duration to hold at full opacity in seconds (default: 1.0)
    
    Returns:
        Alpha value between 0.0 (transparent) and 1.0 (opaque)
        
    Examples:
        >>> calculate_ending_image_alpha(5.0, 10.0, 4.0, 1.0)  # Before fade starts
        0.0
        >>> calculate_ending_image_alpha(7.0, 10.0, 4.0, 1.0)  # Halfway through fade
        0.5
        >>> calculate_ending_image_alpha(9.0, 10.0, 4.0, 1.0)  # Fade complete
        1.0
        >>> calculate_ending_image_alpha(10.0, 10.0, 4.0, 1.0)  # Holding at full
        1.0
    """
    # Fade starts at duration - fade_duration - hold_duration
    # So it finishes fading at duration - hold_duration, then holds
    fade_start_time = duration - fade_duration - hold_duration
    fade_end_time = duration - hold_duration
    
    if current_time < fade_start_time:
        return 0.0  # Not visible yet
    
    if current_time >= fade_end_time:
        return 1.0  # Holding at full opacity
    
    # Calculate progress through fade (0.0 to 1.0)
    fade_progress = (current_time - fade_start_time) / fade_duration
    
    # Clamp to [0.0, 1.0]
    return min(max(fade_progress, 0.0), 1.0)


def ease_out_cubic(t: float) -> float:
    """Ease-out cubic easing function
    
    Starts fast, decelerates smoothly to stop.
    
    Args:
        t: Progress value between 0.0 and 1.0
    
    Returns:
        Eased value between 0.0 and 1.0
        
    Examples:
        >>> ease_out_cubic(0.0)
        0.0
        >>> ease_out_cubic(0.5)
        0.875
        >>> ease_out_cubic(1.0)
        1.0
    """
    return 1.0 - pow(1.0 - t, 3.0)


def calculate_ending_image_y_position(
    current_time: float,
    duration: float,
    fade_duration: float = 4.0,
    hold_duration: float = 1.0,
    image_height_normalized: float = 0.5
) -> float:
    """Calculate Y position for ending image with eased scroll animation
    
    Image starts above the screen and eases down to center, synchronized with fade-in.
    Uses ease-out cubic for smooth deceleration.
    
    Args:
        current_time: Current playback time in seconds
        duration: Total video duration in seconds
        fade_duration: Duration of fade-in effect in seconds
        hold_duration: Duration to hold at center in seconds
        image_height_normalized: Height of image in normalized coords (0.0 to 2.0)
    
    Returns:
        Y offset in normalized coordinates (-1.0 to 1.0, where 0.0 is center)
        Positive values move image down, negative values move up
        
    Examples:
        >>> calculate_ending_image_y_position(3.0, 10.0, 4.0, 1.0, 0.5)  # Before animation
        1.25
        >>> calculate_ending_image_y_position(7.0, 10.0, 4.0, 1.0, 0.5)  # Middle of scroll
        0.15625
        >>> calculate_ending_image_y_position(9.0, 10.0, 4.0, 1.0, 0.5)  # At center
        0.0
    """
    fade_start_time = duration - fade_duration - hold_duration
    fade_end_time = duration - hold_duration
    
    # Start position: above screen (positive Y in OpenGL, accounting for image height)
    start_y = 1.0 + (image_height_normalized / 2.0)
    # End position: centered
    end_y = 0.0
    
    if current_time < fade_start_time:
        return start_y  # Above screen, not visible yet
    
    if current_time >= fade_end_time:
        return end_y  # At center, holding position
    
    # Calculate progress through animation (0.0 to 1.0)
    progress = (current_time - fade_start_time) / fade_duration
    
    # Apply ease-out cubic for smooth deceleration
    eased_progress = ease_out_cubic(progress)
    
    # Interpolate from start to end position
    return start_y + (end_y - start_y) * eased_progress


def calculate_image_dimensions_with_aspect_ratio(
    image_width: int,
    image_height: int,
    canvas_width: int,
    canvas_height: int,
    margin_percent: float = 0.30
) -> Tuple[int, int, int, int]:
    """Calculate dimensions to fit image within canvas with fixed aspect ratio and margins
    
    Pure function that calculates the target dimensions and position for an image
    to fit within a canvas while maintaining aspect ratio and applying margins.
    
    Args:
        image_width: Original image width in pixels
        image_height: Original image height in pixels
        canvas_width: Target canvas width in pixels
        canvas_height: Target canvas height in pixels
        margin_percent: Margin as percentage of canvas (0.30 = 30% margins on each side)
    
    Returns:
        Tuple of (new_width, new_height, x_offset, y_offset) in pixels
        - new_width, new_height: Scaled dimensions maintaining aspect ratio
        - x_offset, y_offset: Position to center the image (top-left corner)
    
    Examples:
        >>> # 1000x500 image in 1920x1080 canvas with 30% margin
        >>> calculate_image_dimensions_with_aspect_ratio(1000, 500, 1920, 1080, 0.30)
        (1344, 672, 288, 204)
    """
    # Calculate available space after margins
    margin_factor = 1.0 - (2.0 * margin_percent)
    available_width = canvas_width * margin_factor
    available_height = canvas_height * margin_factor
    
    # Calculate aspect ratios
    image_aspect = image_width / image_height
    available_aspect = available_width / available_height
    
    # Determine scaling based on which dimension is the limiting factor
    if image_aspect > available_aspect:
        # Image is wider - width is limiting factor
        new_width = int(available_width)
        new_height = int(available_width / image_aspect)
    else:
        # Image is taller - height is limiting factor
        new_height = int(available_height)
        new_width = int(available_height * image_aspect)
    
    # Calculate offsets to center the image
    x_offset = (canvas_width - new_width) // 2
    y_offset = (canvas_height - new_height) // 2
    
    return (new_width, new_height, x_offset, y_offset)
