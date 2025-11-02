"""
MIDI Rendering Core - Pure Functions

Pure functions for MIDI note rendering calculations. These functions have NO side effects
and depend only on their input parameters. They can be used by any renderer (PIL, OpenCV,
ModernGL, etc.) by passing in the appropriate rendering configuration.

Functional Core Design:
- All functions are pure (deterministic, no I/O, no mutation)
- Take explicit parameters instead of reading from objects/globals
- Return new values instead of modifying state
- Can be tested in isolation without mocking

Used by: render_midi_to_video.py (PIL/OpenCV), moderngl_renderer (future)
"""

import math
from typing import Tuple, Set, Dict, List, Any
from midi_types import DrumNote


# ============================================================================
# Color & Brightness Calculations (Already Extracted)
# ============================================================================

def calculate_note_alpha(time_until_hit: float, y_pos: float, strike_line_y: float, height: float) -> float:
    """Pure function to calculate note transparency based on timing and position.
    
    Args:
        time_until_hit: Seconds until note reaches strike line (negative = after hit)
        y_pos: Current y position of note (pixels)
        strike_line_y: Y position of strike line (pixels)
        height: Total screen height (pixels)
    
    Returns:
        Alpha multiplier from 0.0 to 1.0
    """
    # Before strike line: always fully opaque
    if time_until_hit >= 0:
        return 1.0
    
    # After strike line: fade from 100% to 20% as note travels to bottom
    distance_after_strike = y_pos - strike_line_y
    max_distance = height - strike_line_y
    fade_progress = min(distance_after_strike / max_distance, 1.0)
    return 1.0 - (0.8 * fade_progress)  # 1.0 → 0.2


def calculate_brightness(velocity: int) -> float:
    """Pure function: Convert MIDI velocity to brightness factor
    
    Args:
        velocity: MIDI velocity (0-127)
    
    Returns:
        Brightness factor from 0.0 to 1.0
    """
    return velocity / 127.0


def apply_brightness_to_color(color: Tuple[int, int, int], brightness: float) -> Tuple[int, int, int]:
    """Pure function: Apply brightness factor to RGB color
    
    Args:
        color: RGB color tuple (0-255 per channel)
        brightness: Brightness factor (0.0 to 1.0)
    
    Returns:
        Adjusted RGB color tuple
    """
    return tuple(int(c * brightness) for c in color)


def get_brighter_outline_color(base_color: Tuple[int, int, int], alpha: int) -> Tuple[int, int, int, int]:
    """Pure function: Calculate brighter outline color from base color
    
    Args:
        base_color: RGB color tuple
        alpha: Alpha value (0-255)
    
    Returns:
        RGBA color tuple with brightened RGB values
    """
    # Brighten each channel by adding 80% of remaining headroom to 255
    bright_color = tuple(min(255, int(c + (255 - c) * 0.8)) for c in base_color)
    return (*bright_color, alpha)


# ============================================================================
# Strike Animation Calculations
# ============================================================================

def calculate_kick_strike_pulse(time_until_hit: float, strike_window: float = 0.08) -> float:
    """Calculate pulse animation factor for kick drum strike effect
    
    Pure function that creates a smooth pulse animation when a kick drum
    note is at the strike line. Uses quarter-sine wave for smooth in/out.
    
    Args:
        time_until_hit: Time in seconds until note hits strike line (negative = after)
        strike_window: Time window in seconds for strike effect (default 80ms)
    
    Returns:
        Pulse factor from 0.0 (no effect) to 1.0 (peak pulse)
        Returns 0.0 if note is outside strike window
    """
    if abs(time_until_hit) >= strike_window:
        return 0.0
    
    # Calculate progress through strike window (0.0 to 1.0)
    pulse_progress = 1.0 - abs(time_until_hit) / strike_window
    
    # Quarter-sine pulse: smooth acceleration and deceleration
    return abs(math.sin(pulse_progress * math.pi * 0.5))


def calculate_strike_color_mix(base_color: Tuple[int, int, int], 
                                pulse: float, 
                                white_mix_factor: float = 0.5) -> Tuple[int, int, int]:
    """Calculate brightened/whitened color for strike animation
    
    Pure function that mixes base color toward white based on pulse intensity.
    Creates the "flash" effect when notes are struck.
    
    Args:
        base_color: Base RGB color tuple (0-255 per channel)
        pulse: Pulse intensity from 0.0 (no effect) to 1.0 (full effect)
        white_mix_factor: Maximum amount of white to mix (0.0 to 1.0, default 0.5 = 50%)
    
    Returns:
        RGB color tuple with white mixed in based on pulse
    """
    white_mix = pulse * white_mix_factor
    return tuple(int(c + (255 - c) * white_mix) for c in base_color)


def calculate_strike_glow_size(base_size: int, pulse: float, size_multiplier: float = 8.0) -> int:
    """Calculate size increase for strike glow effect
    
    Pure function that scales up an element's size during strike animation.
    
    Args:
        base_size: Base size in pixels
        pulse: Pulse intensity from 0.0 to 1.0
        size_multiplier: Maximum size increase at full pulse (default 8 pixels)
    
    Returns:
        Size increase in pixels (0 at pulse=0, size_multiplier at pulse=1)
    """
    return int(size_multiplier * pulse)


def calculate_strike_alpha_boost(base_alpha: int, pulse: float, 
                                  min_factor: float = 0.8, max_factor: float = 1.0) -> int:
    """Calculate alpha transparency boost during strike animation
    
    Pure function that makes elements more opaque during strike pulse.
    
    Args:
        base_alpha: Base alpha value (0-255)
        pulse: Pulse intensity from 0.0 to 1.0
        min_factor: Minimum alpha multiplier at pulse=0 (default 0.8 = 80%)
        max_factor: Maximum alpha multiplier at pulse=1 (default 1.0 = 100%)
    
    Returns:
        Boosted alpha value (0-255)
    """
    boost = min_factor + (max_factor - min_factor) * pulse
    return int(base_alpha * boost)


def calculate_strike_outline_width(base_width: int, pulse: float, width_increase: int = 2) -> int:
    """Calculate outline width increase during strike animation
    
    Pure function that thickens outlines during strike pulse for emphasis.
    
    Args:
        base_width: Base outline width in pixels
        pulse: Pulse intensity from 0.0 to 1.0
        width_increase: Maximum width increase at full pulse (default 2 pixels)
    
    Returns:
        Total outline width in pixels
    """
    return base_width + int(width_increase * pulse)


# ============================================================================
# Position & Timing Calculations
# ============================================================================

def calculate_note_y_position(
    note_time: float,
    current_time: float,
    strike_line_y: int,
    pixels_per_second: float
) -> float:
    """Calculate Y position of a falling note
    
    Pure function that calculates where a note should be drawn based on time.
    Returns float for sub-pixel precision; caller should round as needed.
    
    Args:
        note_time: Time in seconds when note should hit strike line
        current_time: Current playback time in seconds
        strike_line_y: Y coordinate of strike line (pixels)
        pixels_per_second: Fall speed in pixels per second
    
    Returns:
        Y position in pixels (float for precision)
    """
    time_until_hit = note_time - current_time
    return strike_line_y - (time_until_hit * pixels_per_second)


def calculate_highlight_zone(
    strike_line_y: int,
    note_height: int,
    zone_multiplier: float = 1.5
) -> Tuple[int, int]:
    """Calculate the vertical zone where highlight effects should be shown
    
    Args:
        strike_line_y: Y coordinate of strike line (pixels)
        note_height: Height of note rectangles (pixels)
        zone_multiplier: Multiplier for zone height (default 1.5x note height)
    
    Returns:
        Tuple of (zone_start_y, zone_end_y) in pixels
    """
    highlight_zone_height = int(note_height * zone_multiplier)
    zone_start = strike_line_y - highlight_zone_height // 2
    zone_end = strike_line_y + highlight_zone_height // 2
    return (zone_start, zone_end)


def is_note_in_highlight_zone(
    note: DrumNote,
    current_time: float,
    strike_line_y: int,
    note_height: int,
    pixels_per_second: float,
    zone_multiplier: float = 1.5
) -> bool:
    """Check if note is in highlight zone (pure function)
    
    Args:
        note: DrumNote to check
        current_time: Current playback time
        strike_line_y: Y coordinate of strike line
        note_height: Height of note rectangles
        pixels_per_second: Fall speed
        zone_multiplier: Multiplier for zone height
    
    Returns:
        True if note center is within highlight zone
    """
    # Calculate note position
    y_pos = calculate_note_y_position(note.time, current_time, strike_line_y, pixels_per_second)
    y_pos_int = int(round(y_pos))
    
    # Calculate note center
    note_top = y_pos_int - note_height
    note_bottom = y_pos_int
    note_center_y = (note_top + note_bottom) // 2
    
    # Check against zone
    zone_start, zone_end = calculate_highlight_zone(strike_line_y, note_height, zone_multiplier)
    return zone_start <= note_center_y <= zone_end


def calculate_strike_progress(
    note: DrumNote,
    current_time: float,
    strike_line_y: int,
    note_height: int,
    pixels_per_second: float,
    zone_multiplier: float = 1.5
) -> float:
    """Calculate animation progress through strike zone (0.0 to 1.0)
    
    Pure function that calculates how far a note has progressed through
    the highlight zone. Returns 0.0 when entering, 0.5 at center, 1.0 when leaving.
    
    Args:
        note: DrumNote to check
        current_time: Current playback time
        strike_line_y: Y coordinate of strike line
        note_height: Height of note rectangles
        pixels_per_second: Fall speed
        zone_multiplier: Multiplier for zone height
    
    Returns:
        Progress value from 0.0 (entering) to 1.0 (leaving)
    """
    # Calculate note position
    y_pos = calculate_note_y_position(note.time, current_time, strike_line_y, pixels_per_second)
    y_pos_int = int(round(y_pos))
    
    # Calculate note center
    note_top = y_pos_int - note_height
    note_bottom = y_pos_int
    note_center_y = (note_top + note_bottom) // 2
    
    # Get zone boundaries
    zone_start, zone_end = calculate_highlight_zone(strike_line_y, note_height, zone_multiplier)
    
    # Calculate progress
    if note_center_y < zone_start:
        return 0.0
    elif note_center_y > zone_end:
        return 1.0
    else:
        return (note_center_y - zone_start) / (zone_end - zone_start)


def calculate_lookahead_time(strike_line_y: int, pixels_per_second: float) -> float:
    """Calculate how far ahead to look for notes to render
    
    Notes should appear at top of screen (y=0) and fall to strike line.
    This calculates the time needed for a note to travel that distance.
    
    Args:
        strike_line_y: Y coordinate where notes are struck
        pixels_per_second: Fall speed
    
    Returns:
        Time in seconds to look ahead
    """
    return strike_line_y / pixels_per_second


def calculate_passthrough_time(
    height: int,
    strike_line_y: int,
    note_height: int,
    pixels_per_second: float
) -> float:
    """Calculate time for note to pass completely off bottom of screen
    
    After hitting the strike line, notes continue to fall and fade out.
    This calculates how long until they're completely off screen.
    
    Args:
        height: Screen height in pixels
        strike_line_y: Y coordinate of strike line
        note_height: Height of note rectangles
        pixels_per_second: Fall speed
    
    Returns:
        Time in seconds after strike line crossing
    """
    distance_to_travel = (height - strike_line_y) + note_height
    return distance_to_travel / pixels_per_second


# ============================================================================
# Lane Management
# ============================================================================

def calculate_used_lanes(notes: List[DrumNote]) -> Set[int]:
    """Extract set of used lane numbers (excluding special lanes like kick)
    
    Args:
        notes: List of DrumNotes
    
    Returns:
        Set of lane numbers that have at least one note (lane >= 0 only)
    """
    return set(note.lane for note in notes if note.lane >= 0)


def create_lane_mapping(used_lanes: Set[int]) -> Dict[int, int]:
    """Create mapping from original lane numbers to consecutive positions
    
    When some lanes are empty, this creates a compact layout by mapping
    the used lanes to consecutive positions (0, 1, 2, ...).
    
    Args:
        used_lanes: Set of lane numbers that have notes
    
    Returns:
        Dictionary mapping original lane -> new consecutive lane
    
    Example:
        used_lanes = {0, 2, 5, 8}
        returns = {0: 0, 2: 1, 5: 2, 8: 3}
    """
    sorted_lanes = sorted(used_lanes)
    return {original: new for new, original in enumerate(sorted_lanes)}


def remap_note_lanes(notes: List[DrumNote], lane_mapping: Dict[int, int]) -> List[DrumNote]:
    """Remap note lanes to consecutive positions
    
    Creates new DrumNote instances with updated lane numbers based on mapping.
    Preserves all other note properties. Skips notes with special lanes (negative).
    
    Args:
        notes: List of DrumNotes with original lane numbers
        lane_mapping: Mapping from original lane -> new lane
    
    Returns:
        New list of DrumNotes with remapped lanes
    """
    remapped = []
    for note in notes:
        if note.lane >= 0 and note.lane in lane_mapping:
            # Remap regular lane (create new instance since DrumNote is frozen)
            remapped.append(DrumNote(
                midi_note=note.midi_note,
                time=note.time,
                velocity=note.velocity,
                lane=lane_mapping[note.lane],
                color=note.color,
                name=note.name
            ))
        else:
            # Keep special lanes (kick drum, etc.) unchanged
            remapped.append(note)
    
    return remapped


def filter_and_remap_lanes(notes: List[DrumNote]) -> Tuple[List[DrumNote], int]:
    """Complete lane filtering and remapping pipeline
    
    Convenience function that detects used lanes, creates mapping, and remaps notes.
    Returns the remapped notes and the count of used lanes.
    
    Args:
        notes: List of DrumNotes with original lane assignments
    
    Returns:
        Tuple of (remapped_notes, num_lanes_used)
    """
    used_lanes = calculate_used_lanes(notes)
    
    if not used_lanes:
        # No regular lanes (only kick drum or empty)
        return notes, 0
    
    lane_mapping = create_lane_mapping(used_lanes)
    remapped_notes = remap_note_lanes(notes, lane_mapping)
    
    return remapped_notes, len(used_lanes)
