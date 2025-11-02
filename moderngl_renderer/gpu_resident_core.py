"""
GPU-Resident MIDI Renderer - Functional Core

Pure functions for pre-computing all note geometry for GPU-resident rendering.
All notes converted to GPU format once at initialization, then uploaded to persistent buffer.
"""

import numpy as np
from typing import List, Tuple
from midi_types import DrumNote


def precompute_all_note_instances(
    notes: List[DrumNote],
    width: int,
    height: int,
    pixels_per_second: float,
    strike_line_y: int
) -> Tuple[np.ndarray, int]:
    """Pre-compute all note instance data for GPU upload
    
    Converts all MIDI notes to GPU-friendly format once.
    This data is uploaded to GPU buffer and reused for entire video.
    
    Pure function - no side effects.
    
    Args:
        notes: All DrumNotes in the MIDI sequence
        width: Screen width in pixels
        height: Screen height in pixels
        pixels_per_second: Note fall speed
        strike_line_y: Y position of strike line in pixels
        
    Returns:
        Tuple of (instance_data_array, num_instances)
        - instance_data_array: numpy structured array ready for GPU upload
        - num_instances: number of note instances
    
    Instance data structure (per note):
        - base_rect: vec4 (x, y_at_strike, width, height) in normalized coords
        - color: vec3 (r, g, b) normalized 0-1
        - timing: vec2 (start_time, duration) in seconds
        - size_pixels: vec2 (width, height) in pixels
    """
    if not notes:
        # Return empty array with correct dtype
        dtype = _get_instance_dtype()
        return np.array([], dtype=dtype), 0
    
    # Calculate lane layout
    regular_lanes = set(n.lane for n in notes if n.lane >= 0)
    num_lanes = len(regular_lanes) if regular_lanes else 1
    note_width_pixels = width / num_lanes if num_lanes > 0 else width
    note_height_pixels = 60  # Fixed height in pixels
    
    # Normalize to OpenGL coords (-1 to 1)
    def pixel_to_norm_x(x_pixels):
        return (x_pixels / width) * 2.0 - 1.0
    
    def pixel_to_norm_y(y_pixels):
        return (y_pixels / height) * 2.0 - 1.0
    
    def pixels_to_norm_width(w_pixels):
        return (w_pixels / width) * 2.0
    
    def pixels_to_norm_height(h_pixels):
        return (h_pixels / height) * 2.0
    
    # Pre-allocate array
    num_instances = len(notes)
    dtype = _get_instance_dtype()
    instances = np.zeros(num_instances, dtype=dtype)
    
    strike_y_norm = pixel_to_norm_y(strike_line_y)
    
    for i, note in enumerate(notes):
        # Calculate horizontal position
        if note.lane == -1:
            # Kick drum - full width
            x_norm = -1.0
            width_norm = 2.0
            width_pixels = width
        else:
            # Regular note - positioned in lane
            x_pixels = note.lane * note_width_pixels
            x_norm = pixel_to_norm_x(x_pixels)
            width_norm = pixels_to_norm_width(note_width_pixels)
            width_pixels = note_width_pixels
        
        # Height
        if note.lane == -1:
            # Kick drum - thinner bar
            height_pixels = 30
        else:
            height_pixels = note_height_pixels
        
        height_norm = pixels_to_norm_height(height_pixels)
        
        # Normalize color (0-255 -> 0-1)
        color_norm = (
            note.color[0] / 255.0,
            note.color[1] / 255.0,
            note.color[2] / 255.0
        )
        
        # Fill instance data
        instances[i]['base_rect'] = (x_norm, strike_y_norm, width_norm, height_norm)
        instances[i]['color'] = color_norm
        instances[i]['timing'] = (note.time, 0.0)  # duration unused for now
        instances[i]['size_pixels'] = (width_pixels, height_pixels)
    
    return instances, num_instances


def _get_instance_dtype():
    """Get numpy dtype for instance data structure
    
    Must match shader layout:
    - base_rect: vec4
    - color: vec3
    - timing: vec2
    - size_pixels: vec2
    """
    return np.dtype([
        ('base_rect', np.float32, 4),      # x, y_at_strike, width, height
        ('color', np.float32, 3),          # r, g, b
        ('timing', np.float32, 2),         # start_time, duration
        ('size_pixels', np.float32, 2),    # width, height in pixels
    ])


def calculate_render_params(
    width: int,
    height: int,
    fall_speed_multiplier: float = 1.0
) -> dict:
    """Calculate rendering parameters
    
    Pure function - returns configuration dict.
    
    Args:
        width: Screen width in pixels
        height: Screen height in pixels
        fall_speed_multiplier: Speed multiplier for falling notes
        
    Returns:
        Dictionary with rendering parameters:
        - pixels_per_second: Fall speed
        - strike_line_y: Strike line position in pixels
        - strike_line_y_norm: Strike line in normalized coords
        - lookahead_time: How far ahead to show notes (seconds)
        - passthrough_time: How long after strike to show (seconds)
    """
    pixels_per_second = height * 0.4 * fall_speed_multiplier
    strike_line_y = int(height * 0.85)
    strike_line_y_norm = (strike_line_y / height) * 2.0 - 1.0
    
    # Time calculations (from midi_render_core)
    lookahead_time = strike_line_y / pixels_per_second
    passthrough_time = (height - strike_line_y + 60) / pixels_per_second  # 60 = note height
    
    return {
        'pixels_per_second': pixels_per_second,
        'strike_line_y': strike_line_y,
        'strike_line_y_norm': strike_line_y_norm,
        'lookahead_time': lookahead_time,
        'passthrough_time': passthrough_time,
    }


def precompute_static_elements(
    width: int,
    height: int,
    num_lanes: int,
    strike_line_y: int
) -> Tuple[np.ndarray, int]:
    """Pre-compute static UI elements (strike line, lane markers, background)
    
    These elements don't animate, rendered from separate static buffer.
    
    Args:
        width: Screen width in pixels
        height: Screen height in pixels
        num_lanes: Number of note lanes
        strike_line_y: Strike line Y position in pixels
        
    Returns:
        Tuple of (static_elements_array, num_elements)
    """
    # For now, return empty - will implement in Phase B
    dtype = _get_instance_dtype()
    return np.array([], dtype=dtype), 0
