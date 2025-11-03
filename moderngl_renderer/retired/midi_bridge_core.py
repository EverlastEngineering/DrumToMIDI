"""
MIDI to ModernGL Bridge

Converts MIDI data structures (DrumNote) to ModernGL rectangle format.
Uses extracted pure functions from midi_render_core for all calculations.

This module bridges the gap between MIDI parsing and GPU rendering:
- Input: List[DrumNote] from midi_parser
- Output: ModernGL rectangle specifications
- Calculations: Pure functions from midi_render_core
"""

from typing import List, Dict, Tuple, Any
from midi_types import DrumNote, STANDARD_GM_DRUM_MAP
from midi_render_core import (
    calculate_note_y_position,
    calculate_note_alpha,
    calculate_brightness,
    is_note_in_highlight_zone,
    calculate_strike_progress,
    calculate_kick_strike_pulse,
    calculate_strike_color_mix,
    calculate_lookahead_time,
    calculate_passthrough_time,
    filter_and_remap_lanes
)


# ============================================================================
# Configuration
# ============================================================================

class RenderConfig:
    """ModernGL renderer configuration
    
    All coordinates in OpenGL normalized space:
    - X: -1.0 (left) to 1.0 (right)
    - Y: -1.0 (bottom) to 1.0 (top)
    """
    
    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: int = 60,
        fall_speed_multiplier: float = 1.0
    ):
        self.width = width
        self.height = height
        self.fps = fps
        
        # Screen bounds (OpenGL normalized coords)
        self.screen_top = 1.0
        self.screen_bottom = -1.0
        self.screen_left = -1.0
        self.screen_right = 1.0
        
        # Strike line position (85% down from top)
        # In OpenGL: higher Y = top, so 85% down = lower Y value
        screen_height_norm = self.screen_top - self.screen_bottom  # 2.0
        strike_offset = screen_height_norm * 0.85
        self.strike_line_y = self.screen_top - strike_offset  # 1.0 - 1.7 = -0.7
        
        # Note dimensions (normalized coords)
        self.note_height = 0.06
        self.kick_bar_height = 0.03
        
        # Fall speed (normalized units per second)
        # Notes should take ~2.5 seconds to fall from top to strike line
        # Distance: 1.0 - (-0.7) = 1.7 units
        base_speed = 1.7 / 2.5  # 0.68 units/second
        self.fall_speed = base_speed * fall_speed_multiplier
        
        # Timing windows (calculated once)
        # Convert from pixel-based calculations to normalized coords
        # For compatibility, we'll use pixel equivalents then convert
        pixel_strike_y = int(height * 0.85)
        pixels_per_second = height * 0.4 * fall_speed_multiplier
        
        self.lookahead_time = calculate_lookahead_time(pixel_strike_y, pixels_per_second)
        self.passthrough_time = calculate_passthrough_time(
            height, pixel_strike_y, 60, pixels_per_second
        )


# ============================================================================
# Coordinate Conversion
# ============================================================================

def rgb_255_to_normalized(color: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Convert RGB from 0-255 range to 0.0-1.0 range for OpenGL
    
    Args:
        color: RGB tuple (0-255 per channel)
    
    Returns:
        RGB tuple (0.0-1.0 per channel)
    """
    return (color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)


def pixel_to_normalized_y(pixel_y: float, height: int, screen_top: float = 1.0, screen_bottom: float = -1.0) -> float:
    """Convert pixel Y coordinate to normalized OpenGL coordinate
    
    Args:
        pixel_y: Y coordinate in pixels (0 = top, height = bottom)
        height: Screen height in pixels
        screen_top: Top of screen in normalized coords (default 1.0)
        screen_bottom: Bottom of screen in normalized coords (default -1.0)
    
    Returns:
        Y coordinate in normalized space
    """
    # Convert pixel space (0 at top) to normalized space (1.0 at top)
    normalized_progress = pixel_y / height  # 0.0 to 1.0
    screen_height_norm = screen_top - screen_bottom
    return screen_top - (normalized_progress * screen_height_norm)


# ============================================================================
# Lane Layout
# ============================================================================

def calculate_lane_layout(num_lanes: int, screen_left: float = -1.0, screen_right: float = 1.0) -> Dict[int, float]:
    """Calculate X positions for drum lanes
    
    Args:
        num_lanes: Number of lanes to layout
        screen_left: Left edge in normalized coords
        screen_right: Right edge in normalized coords
    
    Returns:
        Dictionary mapping lane index → center X position
    """
    if num_lanes == 0:
        return {}
    
    # Leave margins on edges
    margin = 0.2
    usable_left = screen_left + margin
    usable_right = screen_right - margin
    usable_width = usable_right - usable_left
    
    lane_width = usable_width / num_lanes
    
    layout = {}
    for i in range(num_lanes):
        # Center of lane
        lane_center = usable_left + (i + 0.5) * lane_width
        layout[i] = lane_center
    
    return layout


def calculate_note_width(num_lanes: int, screen_width: float = 2.0) -> float:
    """Calculate note width based on number of lanes
    
    Args:
        num_lanes: Number of lanes
        screen_width: Total screen width in normalized coords (default 2.0)
    
    Returns:
        Note width in normalized coords
    """
    if num_lanes == 0:
        return 0.1
    
    # Use 80% of lane width (leave gap between lanes)
    usable_width = screen_width * 0.8
    lane_width = usable_width / num_lanes
    return lane_width * 0.8


# ============================================================================
# DrumNote to Rectangle Conversion
# ============================================================================

def drum_note_to_rectangle(
    note: DrumNote,
    current_time: float,
    lane_layout: Dict[int, float],
    note_width: float,
    config: RenderConfig
) -> Dict[str, Any]:
    """Convert DrumNote to ModernGL rectangle specification
    
    Uses extracted pure functions from midi_render_core for all calculations.
    
    Args:
        note: DrumNote with timing, lane, color, velocity
        current_time: Current playback time in seconds
        lane_layout: Dictionary mapping lane index → X position
        note_width: Width of regular notes
        config: Renderer configuration
    
    Returns:
        Rectangle specification for ModernGL renderer
    """
    # Calculate Y position using pixel-based function, then convert
    # We use pixel space for compatibility with existing tested functions
    pixel_strike_y = int(config.height * 0.85)
    pixels_per_second = config.height * 0.4 * config.fall_speed
    
    pixel_y = calculate_note_y_position(
        note.time, current_time, pixel_strike_y, pixels_per_second
    )
    
    # Convert to normalized coords
    y_pos = pixel_to_normalized_y(pixel_y, config.height, config.screen_top, config.screen_bottom)
    
    # Kick drum (lane -1) is full-width bar
    if note.lane == -1:
        return {
            'x': config.screen_left,
            'y': y_pos,
            'width': config.screen_right - config.screen_left,  # Full width
            'height': config.kick_bar_height,
            'color': rgb_255_to_normalized(note.color),
            'brightness': calculate_brightness(note.velocity),
            'note_type': 'kick'
        }
    
    # Regular lane note
    # Calculate alpha using existing function (pixel-based)
    time_until_hit = note.time - current_time
    alpha_factor = calculate_note_alpha(
        time_until_hit, pixel_y, pixel_strike_y, config.height
    )
    
    # Get lane position
    x_center = lane_layout.get(note.lane, 0.0)
    
    # Calculate brightness from velocity
    brightness = calculate_brightness(note.velocity) * alpha_factor
    
    return {
        'x': x_center - note_width / 2,  # Center on lane
        'y': y_pos,
        'width': note_width,
        'height': config.note_height,
        'color': rgb_255_to_normalized(note.color),
        'brightness': brightness,
        'note_type': 'regular'
    }


def generate_highlight_circles(
    notes: List[DrumNote],
    current_time: float,
    lane_layout: Dict[int, float],
    config: RenderConfig
) -> List[Dict[str, Any]]:
    """Generate highlight circle specifications for notes at strike line
    
    Args:
        notes: All notes in sequence
        current_time: Current playback time
        lane_layout: Dictionary mapping lane index → X position
        config: Renderer configuration
    
    Returns:
        List of circle specifications for ModernGL circle renderer
    """
    circles = []
    
    # Use pixel-based calculations for compatibility
    pixel_strike_y = int(config.height * 0.85)
    pixels_per_second = config.height * 0.4 * config.fall_speed
    
    for note in notes:
        # Skip kick drums (they have their own strike effect)
        if note.lane == -1:
            continue
        
        # Check if note is in highlight zone
        if not is_note_in_highlight_zone(
            note, current_time, pixel_strike_y, 60, pixels_per_second, zone_multiplier=1.5
        ):
            continue
        
        # Calculate strike animation progress
        progress = calculate_strike_progress(
            note, current_time, pixel_strike_y, 60, pixels_per_second, zone_multiplier=1.5
        )
        
        # Calculate pulse using sine wave
        import math
        pulse = abs(math.sin(progress * math.pi))
        
        # Calculate size and color using extracted functions
        base_size = 0.05  # Normalized coords
        size_increase = 0.02 * pulse
        circle_size = base_size + size_increase
        
        # Color mixing
        brightness = calculate_brightness(note.velocity)
        base_color_255 = tuple(int(c * brightness) for c in note.color)
        highlight_color_255 = calculate_strike_color_mix(base_color_255, pulse, white_mix_factor=0.7)
        highlight_color = rgb_255_to_normalized(highlight_color_255)
        
        # Alpha boost
        base_alpha = 0.7
        alpha = 0.3 + 0.7 * pulse  # Fade in/out with pulse
        
        # Get lane position
        x_center = lane_layout.get(note.lane, 0.0)
        
        circles.append({
            'x': x_center,
            'y': config.strike_line_y,
            'radius': circle_size,
            'color': highlight_color,
            'brightness': alpha
        })
    
    return circles


def build_frame_from_drum_notes(
    notes: List[DrumNote],
    current_time: float,
    config: RenderConfig
) -> Dict[str, List[Dict[str, Any]]]:
    """Build complete frame data from DrumNotes
    
    This is the main entry point for converting MIDI data to ModernGL format.
    
    Args:
        notes: All DrumNotes in sequence
        current_time: Current playback time in seconds
        config: Renderer configuration
    
    Returns:
        Dictionary with 'rectangles' and 'circles' lists ready for GPU rendering
    """
    # Calculate lane layout
    # Get number of unique regular lanes (excluding kick)
    regular_lanes = set(n.lane for n in notes if n.lane >= 0)
    num_lanes = len(regular_lanes) if regular_lanes else 1
    
    lane_layout = calculate_lane_layout(num_lanes, config.screen_left, config.screen_right)
    note_width = calculate_note_width(num_lanes, config.screen_right - config.screen_left)
    
    # Filter visible notes using lookahead/passthrough
    visible_notes = []
    for note in notes:
        time_until_hit = note.time - current_time
        if -config.passthrough_time <= time_until_hit <= config.lookahead_time:
            visible_notes.append(note)
    
    # Convert notes to rectangles
    rectangles = []
    for note in visible_notes:
        rect = drum_note_to_rectangle(note, current_time, lane_layout, note_width, config)
        rectangles.append(rect)
    
    # Generate highlight circles
    circles = generate_highlight_circles(visible_notes, current_time, lane_layout, config)
    
    return {
        'rectangles': rectangles,
        'circles': circles
    }
