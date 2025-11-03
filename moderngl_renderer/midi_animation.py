"""
MIDI Animation Bridge - Functional Core

Converts MIDI DrumNote data into animation-compatible format.
Pure functions only - no side effects, no GPU operations.

This bridges between MIDI parsing (midi_shell.py) and GPU rendering (animation.py).
"""

from typing import List, Dict, Tuple, Any
from dataclasses import dataclass


# ============================================================================
# Data Structures
# ============================================================================

@dataclass(frozen=True)
class MidiAnimationNote:
    """Animation-compatible note format
    
    Uses normalized OpenGL coordinates (-1 to +1 range).
    No pixel-space calculations - everything in normalized coords.
    
    Attributes:
        x: Horizontal position (-1.0 = left edge, +1.0 = right edge)
        y_start: Starting Y position (+1.0 = top of screen)
        width: Note width in normalized coords
        height: Note height in normalized coords
        color: RGB color tuple (0.0-1.0 per channel)
        start_time: When note should appear (seconds)
        hit_time: When note should hit strike line (seconds)
        is_kick: True if this is a kick drum (full-width bar)
        velocity: MIDI velocity (0-127) for brightness
        name: Drum name for debugging
    """
    x: float
    y_start: float
    width: float
    height: float
    color: Tuple[float, float, float]
    start_time: float
    hit_time: float
    is_kick: bool
    velocity: int
    name: str = ""


# ============================================================================
# Coordinate Conversion
# ============================================================================

def calculate_lane_x_position(lane_index: int, num_lanes: int) -> float:
    """Calculate normalized X position for a lane
    
    Distributes lanes evenly across screen width in normalized coords.
    
    Args:
        lane_index: Lane number (0 to num_lanes-1)
        num_lanes: Total number of lanes
    
    Returns:
        X position in normalized coords (-1.0 to +1.0)
        
    Example:
        With 4 lanes, positions are: -0.75, -0.25, +0.25, +0.75
        (evenly spaced across the screen)
    """
    if num_lanes == 0:
        return 0.0
    
    # Calculate spacing between lanes
    lane_width = 2.0 / num_lanes  # 2.0 = range from -1 to +1
    
    # Position lane centers
    # Lane 0 should be at left, lane N-1 at right
    x = -1.0 + (lane_index + 0.5) * lane_width
    
    return x


def calculate_note_width(num_lanes: int, lane_spacing_factor: float = 0.9) -> float:
    """Calculate note width in normalized coords
    
    Args:
        num_lanes: Total number of lanes
        lane_spacing_factor: How much of lane width to use (0.0-1.0)
            0.9 = 90% of lane (small gaps between notes)
            1.0 = 100% of lane (no gaps)
    
    Returns:
        Note width in normalized coords
    """
    if num_lanes == 0:
        return 0.2
    
    lane_width = 2.0 / num_lanes
    return lane_width * lane_spacing_factor


def calculate_note_height(fall_duration: float, pixels_per_second: float, 
                         screen_height: int) -> float:
    """Calculate note height in normalized coords
    
    Args:
        fall_duration: Time for note to fall from top to strike line (seconds)
        pixels_per_second: Fall speed in pixels per second
        screen_height: Screen height in pixels
    
    Returns:
        Note height in normalized coords (corresponds to ~150ms of fall time)
    """
    # Note should represent about 150ms of fall time
    note_duration = 0.15  # seconds
    note_height_pixels = pixels_per_second * note_duration
    
    # Convert to normalized coords
    # Screen height = 2.0 in normalized coords (-1 to +1)
    note_height_norm = (note_height_pixels / screen_height) * 2.0
    
    return note_height_norm


# ============================================================================
# DrumNote to Animation Note Conversion
# ============================================================================

def convert_drum_note_to_animation(
    drum_note: Any,  # DrumNote from midi_types
    lane_x: float,
    note_width: float,
    note_height: float,
    fall_duration: float,
    strike_line_y: float = -0.6
) -> MidiAnimationNote:
    """Convert a DrumNote to animation-compatible format
    
    Args:
        drum_note: DrumNote from MIDI parsing
        lane_x: X position for this lane (normalized)
        note_width: Width of notes (normalized)
        note_height: Height of notes (normalized)
        fall_duration: Time to fall from top to strike line (seconds)
        strike_line_y: Strike line position (normalized, default -0.6 = 85% down)
    
    Returns:
        MidiAnimationNote ready for rendering
    """
    # Check if this is a kick drum (lane -1 = special rendering)
    is_kick = drum_note.lane == -1
    
    # For kick drums, use full width
    if is_kick:
        x = 0.0  # Centered
        width = 2.0  # Full screen width (-1 to +1)
        height = note_height * 0.5  # Kick drums are shorter
    else:
        x = lane_x
        width = note_width
        height = note_height
    
    # Convert color from 0-255 to 0.0-1.0
    color = tuple(c / 255.0 for c in drum_note.color)
    
    # Calculate when note should start appearing
    # Note needs to start ABOVE screen so it falls into view
    start_time = drum_note.time - fall_duration
    
    # Calculate starting Y position - ALL notes start from same position
    # This ensures all notes fall at same speed regardless of height
    # Use the standard note_height for positioning (not the modified kick height)
    # Screen top is at y=1.0 in normalized coords
    # For bottom edge to be at screen top (y=1.0): center = 1.0 + note_height/2
    y_start = 1.0 + (note_height / 2.0) + 0.01
    
    return MidiAnimationNote(
        x=x,
        y_start=y_start,
        width=width,
        height=height,
        color=color,
        start_time=start_time,
        hit_time=drum_note.time,
        is_kick=is_kick,
        velocity=drum_note.velocity,
        name=drum_note.name
    )


def convert_drum_notes_to_animation(
    drum_notes: List[Any],  # List[DrumNote]
    screen_width: int = 1920,
    screen_height: int = 1080,
    pixels_per_second: float = 600.0,
    strike_line_percent: float = 0.85
) -> List[MidiAnimationNote]:
    """Convert list of DrumNotes to animation format
    
    Args:
        drum_notes: List of DrumNote objects from MIDI parsing
        screen_width: Screen width in pixels (for calculations)
        screen_height: Screen height in pixels (for calculations)
        pixels_per_second: Note fall speed in pixels per second
        strike_line_percent: Strike line position as % down from top (0.85 = 85% down)
    
    Returns:
        List of MidiAnimationNote objects ready for rendering
    """
    if not drum_notes:
        return []
    
    # Find number of lanes (excluding kick drum lane -1)
    regular_lanes = set(n.lane for n in drum_notes if n.lane >= 0)
    num_lanes = len(regular_lanes)
    
    if num_lanes == 0:
        # Only kick drums, use default
        num_lanes = 1
    
    # Calculate strike line position in normalized coords
    # strike_line_percent = 0.85 means 85% down from top
    # In normalized coords: +1.0 = top, -1.0 = bottom
    strike_line_y = 1.0 - (strike_line_percent * 2.0)  # 0.85 -> -0.7
    
    # Calculate fall duration (time to go from top to strike line)
    distance_pixels = screen_height * strike_line_percent
    fall_duration = distance_pixels / pixels_per_second
    
    # Calculate note dimensions
    note_width = calculate_note_width(num_lanes)
    note_height = calculate_note_height(fall_duration, pixels_per_second, screen_height)
    
    # Build lane position map
    lane_positions = {}
    sorted_lanes = sorted(regular_lanes)
    for i, lane in enumerate(sorted_lanes):
        lane_positions[lane] = calculate_lane_x_position(i, num_lanes)
    
    # Convert each drum note
    animation_notes = []
    for drum_note in drum_notes:
        # Get lane X position (kick drums will override this)
        lane_x = lane_positions.get(drum_note.lane, 0.0)
        
        anim_note = convert_drum_note_to_animation(
            drum_note=drum_note,
            lane_x=lane_x,
            note_width=note_width,
            note_height=note_height,
            fall_duration=fall_duration,
            strike_line_y=strike_line_y
        )
        animation_notes.append(anim_note)
    
    return animation_notes


# ============================================================================
# Visibility and Timing
# ============================================================================

def get_visible_notes_at_time(
    animation_notes: List[MidiAnimationNote],
    current_time: float,
    strike_line_y: float = -0.6,
    screen_bottom: float = -1.0
) -> List[MidiAnimationNote]:
    """Get notes visible at a specific time
    
    Args:
        animation_notes: All notes
        current_time: Current playback time (seconds)
        strike_line_y: Strike line Y position
        screen_bottom: Bottom of screen Y position
    
    Returns:
        List of notes that should be visible (on screen)
    """
    visible = []
    for note in animation_notes:
        # Calculate current Y position
        y = calculate_note_y_at_time(note, current_time, strike_line_y)
        
        # Note is visible if any part overlaps with screen
        # In OpenGL coords: screen_top = 1.0, screen_bottom = -1.0
        # Note spans from (y - height/2) to (y + height/2)
        # Visible if: bottom_edge < screen_top AND top_edge > screen_bottom
        top_edge = y + note.height / 2.0
        bottom_edge = y - note.height / 2.0
        
        # Show note if it overlaps with screen bounds
        if bottom_edge < 1.0 and top_edge > screen_bottom:
            visible.append(note)
    
    return visible


def calculate_note_y_at_time(
    note: MidiAnimationNote,
    current_time: float,
    strike_line_y: float = -0.6
) -> float:
    """Calculate note's Y position at a specific time
    
    Args:
        note: Animation note
        current_time: Current playback time (seconds)
        strike_line_y: Strike line position in normalized coords
    
    Returns:
        Y position in normalized coords (+1.0 = top, -1.0 = bottom)
    """
    if current_time <= note.start_time:
        # Not started yet, position above screen
        return note.y_start
    
    # Calculate how far through the animation we are
    time_elapsed = current_time - note.start_time
    time_total = note.hit_time - note.start_time
    
    if time_total == 0:
        return strike_line_y
    
    # Calculate fall speed (units per second)
    distance = note.y_start - strike_line_y  # e.g., 1.05 - (-0.6) = 1.65
    fall_speed = distance / time_total
    
    # Note continues falling at constant speed after hit time
    y = note.y_start - (fall_speed * time_elapsed)
    
    return y
