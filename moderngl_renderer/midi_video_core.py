"""
MIDI Video Rendering Core - Functional Core

Pure functions for MIDI video rendering calculations.
No side effects, no GPU operations - only transformations.

Used by midi_video_moderngl.py (imperative shell) for video rendering.
"""

from typing import Dict, Any, List, Tuple


# ============================================================================
# Strike Effect Calculations
# ============================================================================

def calculate_strike_effect(
    y_center: float,
    strike_line_y: float = -0.6,
    strike_window: float = 0.04
) -> Tuple[float, float, float]:
    """Calculate strike effect parameters for a note
    
    Pure function that calculates visual effects when notes are near strike line.
    
    Args:
        y_center: Note center Y position in normalized coords
        strike_line_y: Strike line Y position in normalized coords
        strike_window: Size of strike window in normalized coords
    
    Returns:
        Tuple of (scale_factor, flash_alpha, brightness_boost)
        - scale_factor: Height multiplier (1.0 = normal, >1.0 = enlarged)
        - flash_alpha: White flash intensity (0.0-1.0)
        - brightness_boost: Brightness addition (0.0-1.0)
    
    Examples:
        >>> calculate_strike_effect(0.0, -0.6, 0.04)  # Far from strike line
        (1.0, 0.0, 0.0)
        
        >>> calculate_strike_effect(-0.6, -0.6, 0.04)  # At strike line
        (1.3, ..., 0.7)  # Max scale, flash, and brightness
    """
    # Distance from strike line (negative = below, positive = above)
    distance = y_center - strike_line_y
    
    # Check if within strike window
    if abs(distance) > strike_window:
        return 1.0, 0.0, 0.0
    
    # Calculate position within strike window (0.0 at edges, 1.0 at center)
    progress = 1.0 - abs(distance) / strike_window
    
    # Scale pulse: 1.0 → 1.3 → 1.0 (stronger height increase)
    scale_factor = 1.0 + 0.7 * progress * progress
    
    # Flash: peaks at strike line, fades at edges (more intense)
    flash_alpha = 2.5 * progress * progress * progress
    
    # Brightness boost for enhanced glow (stronger)
    brightness_boost = 0.7 * progress
    
    return scale_factor, flash_alpha, brightness_boost


def calculate_note_fade(
    y_center: float,
    strike_line_y: float,
    fade_distance: float = 0.3
) -> float:
    """Calculate fade factor for notes that have passed strike line
    
    Pure function that calculates opacity fade for notes below strike line.
    
    Args:
        y_center: Note center Y position in normalized coords
        strike_line_y: Strike line Y position in normalized coords
        fade_distance: Distance over which to fade (normalized coords)
    
    Returns:
        Fade factor (0.0-1.0), where 1.0 = full opacity, 0.0 = fully faded
    
    Examples:
        >>> calculate_note_fade(-0.5, -0.6, 0.3)  # Above strike line
        1.0
        
        >>> calculate_note_fade(-0.6, -0.6, 0.3)  # At strike line
        1.0
        
        >>> calculate_note_fade(-0.9, -0.6, 0.3)  # Just past fade distance
        0.0
    """
    # Notes above or at strike line: no fade
    if y_center >= strike_line_y:
        return 1.0
    
    # Notes below strike line: fade from 1.0 to 0.0
    distance_past_strike = strike_line_y - y_center
    fade_progress = min(distance_past_strike / fade_distance, 1.0)
    
    return 1.0 - fade_progress


# ============================================================================
# Note Rectangle Conversion
# ============================================================================

def midi_note_to_rectangle(
    x: float,
    y_center: float,
    width: float,
    height: float,
    color: Tuple[float, float, float],
    velocity: int,
    is_kick: bool,
    strike_line_y: float = -0.6,
    strike_window: float = 0.04,
    fade_distance: float = 0.3
) -> Dict[str, Any]:
    """Convert MIDI note data to rectangle specification for rendering
    
    Pure function that transforms note parameters into GPU-ready rectangle format.
    Applies strike effects, velocity-based brightness, and fade effects.
    
    Args:
        x: Note center X position in normalized coords
        y_center: Note center Y position in normalized coords
        width: Note width in normalized coords
        height: Note height in normalized coords
        color: RGB color tuple (0.0-1.0 per channel)
        velocity: MIDI velocity (0-127)
        is_kick: True if this is a kick drum note
        strike_line_y: Strike line Y position
        strike_window: Strike effect window size
        fade_distance: Fade distance after strike line
    
    Returns:
        Rectangle dict with keys: x, y, width, height, color, no_outline
        where (x, y) is the TOP-LEFT corner in OpenGL coords
    
    Note:
        Coordinate system: Higher Y = top of screen (OpenGL convention)
        The 'y' in return value is the TOP-LEFT corner
    """
    # Calculate strike effect
    scale_factor, flash_alpha, brightness_boost = calculate_strike_effect(
        y_center, strike_line_y, strike_window
    )
    
    # Base brightness from velocity (0-127 → 0.3-1.0)
    base_brightness = 0.3 + (velocity / 127.0) * 0.7
    
    # Apply fade effect
    fade_factor = calculate_note_fade(y_center, strike_line_y, fade_distance)
    brightness = base_brightness * fade_factor
    
    # Apply strike brightness boost
    brightness = min(1.0, brightness + brightness_boost)
    
    # Apply brightness to color
    base_color = tuple(c * brightness for c in color)
    
    # Apply flash effect (mix towards white)
    if flash_alpha > 0:
        final_color = tuple(
            c * (1.0 - flash_alpha) + flash_alpha
            for c in base_color
        )
    else:
        final_color = base_color
    
    # Apply scale factor to height only (not width)
    scaled_width = width
    scaled_height = height * scale_factor
    
    # Calculate top-left corner from center position (accounting for scale)
    # In OpenGL: higher Y = top, so top = center + height/2
    y_top = y_center + scaled_height / 2.0
    x_left = x - scaled_width / 2.0
    
    return {
        'x': x_left,
        'y': y_top,
        'width': scaled_width,
        'height': scaled_height,
        'color': final_color,
        'no_outline': is_kick  # Skip outline for kick drum
    }


# ============================================================================
# UI Element Creation
# ============================================================================

def create_strike_line_rectangle(
    strike_line_y: float = -0.6,
    thickness: float = 0.01
) -> Dict[str, Any]:
    """Create strike line rectangle specification
    
    Pure function that generates rectangle data for the strike line.
    
    Args:
        strike_line_y: Y position in normalized coords
        thickness: Line thickness in normalized coords
    
    Returns:
        Rectangle dict for strike line (white, full-width, no outline)
    
    Examples:
        >>> create_strike_line_rectangle(-0.6, 0.01)
        {'x': -1.0, 'y': -0.605, 'width': 2.0, 'height': 0.01, ...}
    """
    return {
        'x': -1.0,
        'y': strike_line_y - thickness / 2.0,
        'width': 2.0,
        'height': thickness,
        'color': (1.0, 1.0, 1.0),  # White
        'no_outline': True  # Skip outline for UI elements
    }


def create_lane_markers(num_lanes: int = 3) -> List[Dict[str, Any]]:
    """Create vertical lane marker rectangles
    
    Pure function that generates rectangle specifications for lane dividers.
    
    Args:
        num_lanes: Number of lanes (determines marker spacing)
    
    Returns:
        List of rectangle dicts for lane markers (dark gray, no outline)
    
    Examples:
        >>> markers = create_lane_markers(3)
        >>> len(markers)
        4  # 3 lanes = 4 markers (edges + dividers)
        
        >>> markers[0]['x']  # Left edge
        -1.005
        
        >>> markers[1]['x']  # First divider
        -0.338333...
    """
    markers = []
    lane_width = 2.0 / num_lanes
    
    for i in range(num_lanes + 1):
        x = -1.0 + i * lane_width
        markers.append({
            'x': x - 0.005,
            'y': 1.0,  # Top of screen
            'width': 0.01,
            'height': 2.0,
            'color': (0.3, 0.3, 0.3),  # Dark gray
            'no_outline': True  # Skip outline for UI elements
        })
    
    return markers


def create_hit_indicator_circles(
    anim_notes: List[Any],
    current_time: float,
    strike_line_y: float = -0.6,
    hit_window: float = 0.24,
    max_circle_size: float = 0.15
) -> List[Dict[str, Any]]:
    """Create expanding circle indicators for notes hitting the strike line
    
    Pure function that generates circle specifications for visual hit feedback.
    Creates circular "burst" effects that expand and fade when notes hit.
    
    Args:
        anim_notes: All animation notes with hit_time, x, color attributes
        current_time: Current playback time in seconds
        strike_line_y: Y position of strike line (normalized coords)
        hit_window: Time window to show circles after hit (seconds)
        max_circle_size: Maximum circle radius (normalized coords)
    
    Returns:
        List of circle dicts for render_circles() with keys:
        x, y, radius, color, brightness
    
    Examples:
        >>> # Note hits at t=1.0, check at t=1.04 (halfway through window)
        >>> circles = create_hit_indicator_circles(notes, 1.04)
        >>> len(circles)  # Should have circles for recent hits
        1
        >>> circles[0]['brightness']  # Should be fading
        0.36  # (1 - 0.5)^2 * 0.8 ≈ 0.2
    """
    circles = []
    
    for note in anim_notes:
        # Skip kick drum (no circle indicator for kick)
        if note.is_kick:
            continue
        
        # Calculate time since hit
        time_since_hit = current_time - note.hit_time
        
        # Only show circles during hit window
        if 0 <= time_since_hit <= hit_window:
            # Progress: 0.0 at hit, 1.0 at end of window
            progress = time_since_hit / hit_window
            
            # Circle expands quickly then slows down (ease-out quadratic)
            radius = max_circle_size * (1.0 - (1.0 - progress) ** 2)
            
            # Brightness fades out (quadratic for faster fade)
            brightness = (1.0 - progress) ** 2
            
            # Skip if too dim to see
            if brightness < 0.05:
                continue
            
            # Position at strike line, centered on note X position
            circles.append({
                'x': note.x,
                'y': strike_line_y,
                'radius': radius,
                'color': note.color,
                'brightness': brightness * 0.8  # Slightly transparent
            })
    
    return circles
