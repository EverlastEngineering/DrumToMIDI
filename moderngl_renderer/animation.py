"""
Animation Core - Functional Core

Pure functions for time-based animation calculations.
No side effects, no GPU operations - only animation math.

Used by animation_shell.py to generate frame sequences.
"""

from typing import List, Dict, Tuple, Any
from .core import (
    get_lane_x_position,
    get_note_width_for_type,
    get_note_height,
    calculate_note_y_position,
    calculate_note_alpha_fade,
    is_note_visible,
    create_strike_line,
    create_lane_markers,
    create_background_lanes
)


# ============================================================================
# Time Calculations
# ============================================================================

def frame_time_from_number(frame_number: int, fps: float) -> float:
    """Calculate time in seconds for a given frame number
    
    Args:
        frame_number: Frame index (0-based)
        fps: Frames per second
    
    Returns:
        Time in seconds
    """
    return frame_number / fps


def total_frames_from_duration(duration_seconds: float, fps: float) -> int:
    """Calculate total number of frames for duration
    
    Args:
        duration_seconds: Duration in seconds
        fps: Frames per second
    
    Returns:
        Total frame count
    """
    return int(duration_seconds * fps)


# ============================================================================
# Note Visibility Window
# ============================================================================

def calculate_visibility_window(
    strike_line_y: float,
    screen_top: float,
    screen_bottom: float,
    fall_speed: float
) -> Tuple[float, float]:
    """Calculate time window for visible notes
    
    Args:
        strike_line_y: Y position of strike line
        screen_top: Y position of screen top
        screen_bottom: Y position of screen bottom
        fall_speed: Note fall speed (units per second)
    
    Returns:
        (lookahead_time, lookbehind_time) in seconds
    """
    # Distance from top to strike line (top has higher Y, strike line lower)
    distance_above = screen_top - strike_line_y
    lookahead_time = distance_above / fall_speed
    
    # Distance from strike line to bottom (strike line higher Y, bottom lower)
    distance_below = strike_line_y - screen_bottom
    lookbehind_time = distance_below / fall_speed
    
    return (lookahead_time, lookbehind_time)


def is_note_in_window(
    note_time: float,
    current_time: float,
    lookahead_time: float,
    lookbehind_time: float
) -> bool:
    """Check if note is within visibility window
    
    Args:
        note_time: When note hits strike line
        current_time: Current playback time
        lookahead_time: How far ahead to show notes
        lookbehind_time: How far behind to show notes
    
    Returns:
        True if note should be visible
    """
    time_until_hit = note_time - current_time
    return -lookbehind_time <= time_until_hit <= lookahead_time


# ============================================================================
# Velocity and Color Mapping
# ============================================================================

def velocity_to_brightness(velocity: int) -> float:
    """Convert MIDI velocity to brightness value
    
    Args:
        velocity: MIDI velocity (0-127)
    
    Returns:
        Brightness (0.0 to 1.0), never fully transparent
    """
    # Map to 0.3 - 1.0 range (never fully transparent)
    min_brightness = 0.3
    max_brightness = 1.0
    normalized = velocity / 127.0
    return min_brightness + (normalized * (max_brightness - min_brightness))


def lane_to_color(lane: str) -> Tuple[float, float, float]:
    """Map lane name to RGB color
    
    Args:
        lane: Lane identifier
    
    Returns:
        RGB tuple (0.0 to 1.0)
    """
    color_map = {
        'hihat': (0.0, 1.0, 1.0),    # Cyan
        'snare': (1.0, 0.0, 0.0),    # Red
        'kick': (1.0, 0.5, 0.0),     # Orange
        'tom': (0.0, 1.0, 0.0),      # Green
    }
    return color_map.get(lane, (1.0, 1.0, 1.0))  # Default white


# ============================================================================
# Note to Rectangle Conversion
# ============================================================================

def note_to_rectangle(
    note: Dict[str, Any],
    current_time: float,
    lanes: List[str],
    strike_line_y: float,
    fall_speed: float,
    screen_bottom: float = -1.0
) -> Dict[str, Any]:
    """Convert note data to rectangle specification
    
    Args:
        note: Dictionary with 'time', 'lane', 'velocity'
        current_time: Current animation time
        lanes: List of all lane names
        strike_line_y: Y position of strike line
        fall_speed: Note fall speed
    
    Returns:
        Rectangle specification dict
    """
    # Calculate time until note hits strike line
    time_until_hit = note['time'] - current_time
    
    # Calculate Y position
    y_pos = calculate_note_y_position(time_until_hit, strike_line_y, fall_speed)
    
    # Get lane position
    lane_x = get_lane_x_position(note['lane'], lanes)
    
    # Get note dimensions
    note_width = get_note_width_for_type(note['lane'])
    note_height = get_note_height()
    
    # Calculate brightness from velocity
    brightness = velocity_to_brightness(note['velocity'])
    
    # Apply fade if past strike line (below it, lower Y value)
    if y_pos < strike_line_y:
        alpha_fade = calculate_note_alpha_fade(y_pos, strike_line_y, screen_bottom)
        brightness *= alpha_fade
    
    # Get color
    color = lane_to_color(note['lane'])
    
    return {
        'x': lane_x - note_width / 2,  # Center on lane
        'y': y_pos,
        'width': note_width,
        'height': note_height,
        'color': color,
        'brightness': brightness
    }


# ============================================================================
# Frame Generation
# ============================================================================

def generate_frame_notes(
    all_notes: List[Dict[str, Any]],
    current_time: float,
    lookahead_time: float,
    lookbehind_time: float
) -> List[Dict[str, Any]]:
    """Filter notes visible at current frame time
    
    Args:
        all_notes: All notes in the sequence
        current_time: Current animation time
        lookahead_time: How far ahead to show notes
        lookbehind_time: How far behind to show notes
    
    Returns:
        List of notes within visibility window
    """
    visible = []
    
    for note in all_notes:
        if is_note_in_window(
            note['time'],
            current_time,
            lookahead_time,
            lookbehind_time
        ):
            visible.append(note)
    
    return visible


def build_frame_scene(
    notes: List[Dict[str, Any]],
    current_time: float,
    lanes: List[str],
    strike_line_y: float,
    fall_speed: float,
    screen_bottom: float = -1.0,
    include_backgrounds: bool = True,
    include_markers: bool = True,
    include_strike_line: bool = True
) -> List[Dict[str, Any]]:
    """Build complete scene for a single frame
    
    Args:
        notes: Notes visible in this frame
        current_time: Current animation time
        lanes: List of all lane names
        strike_line_y: Y position of strike line
        fall_speed: Note fall speed
        screen_bottom: Y position of screen bottom (for fade calculation)
        include_backgrounds: Whether to include lane backgrounds
        include_markers: Whether to include lane markers
        include_strike_line: Whether to include strike line
    
    Returns:
        List of all rectangle specifications for the frame
    """
    elements = []
    
    # Add backgrounds (rendered first, behind everything)
    if include_backgrounds:
        elements.extend(create_background_lanes(
            lanes=lanes,
            colors={
                'hihat': (0.0, 0.1, 0.1),
                'snare': (0.1, 0.0, 0.0),
                'kick': (0.1, 0.05, 0.0),
                'tom': (0.0, 0.1, 0.0)
            },
            brightness=0.3
        ))
    
    # Add lane markers
    if include_markers:
        elements.extend(create_lane_markers(
            lanes=lanes,
            color=(0.3, 0.3, 0.3),
            thickness=0.003
        ))
    
    # Add strike line
    if include_strike_line:
        elements.append(create_strike_line(
            y_position=strike_line_y,
            color=(1.0, 1.0, 1.0),
            thickness=0.008
        ))
    
    # Add notes
    for note in notes:
        rect = note_to_rectangle(
            note=note,
            current_time=current_time,
            lanes=lanes,
            strike_line_y=strike_line_y,
            fall_speed=fall_speed,
            screen_bottom=screen_bottom
        )
        
        # Only add if visible on screen
        if is_note_visible(rect['y'], rect['height'], screen_top=1.0, screen_bottom=screen_bottom):
            elements.append(rect)
    
    return elements
