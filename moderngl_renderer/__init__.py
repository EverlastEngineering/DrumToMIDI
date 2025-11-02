"""
ModernGL Renderer Package

GPU-accelerated video rendering using functional core, imperative shell pattern.

Modules:
- core: Pure functional transformations (100% test coverage)
- animation: Time-based animation logic (98% test coverage)
- shell: GPU operations and I/O (imperative side effects)
"""

from .core import (
    # Color and brightness
    apply_brightness_to_color,
    
    # Coordinate transformations
    normalize_coords_topleft_to_bottomleft,
    normalized_to_pixel_size,
    
    # Rectangle data preparation
    prepare_rectangle_instance_data,
    batch_rectangle_data,
    
    # Note positioning
    calculate_note_y_position,
    calculate_note_alpha_fade,
    is_note_visible,
    
    # Lane calculations
    get_lane_x_position,
    get_note_width_for_type,
    get_note_height,
    
    # Scene elements
    create_strike_line,
    create_lane_markers,
    create_background_lanes,
)

from .animation import (
    # Time calculations
    frame_time_from_number,
    total_frames_from_duration,
    
    # Visibility window
    calculate_visibility_window,
    is_note_in_window,
    
    # Velocity and color mapping
    velocity_to_brightness,
    lane_to_color,
    
    # Note conversion
    note_to_rectangle,
    
    # Frame generation
    generate_frame_notes,
    build_frame_scene,
)

from .shell import (
    ModernGLContext,
    render_rectangles,
    read_framebuffer,
    save_frame,
    render_frame_to_file,
    render_frames_to_array,
)

__all__ = [
    # Core
    'apply_brightness_to_color',
    'normalize_coords_topleft_to_bottomleft',
    'normalized_to_pixel_size',
    'prepare_rectangle_instance_data',
    'batch_rectangle_data',
    'calculate_note_y_position',
    'calculate_note_alpha_fade',
    'is_note_visible',
    'get_lane_x_position',
    'get_note_width_for_type',
    'get_note_height',
    'create_strike_line',
    'create_lane_markers',
    'create_background_lanes',
    
    # Animation
    'frame_time_from_number',
    'total_frames_from_duration',
    'calculate_visibility_window',
    'is_note_in_window',
    'velocity_to_brightness',
    'lane_to_color',
    'note_to_rectangle',
    'generate_frame_notes',
    'build_frame_scene',
    
    # Shell
    'ModernGLContext',
    'render_rectangles',
    'read_framebuffer',
    'save_frame',
    'render_frame_to_file',
    'render_frames_to_array',
]
