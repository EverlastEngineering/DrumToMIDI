"""
MIDI Bridge - Imperative Shell

Handles GPU rendering of MIDI notes using ModernGL.
Uses pure functions from midi_bridge_core for all data transformations.

This module coordinates between MIDI data and GPU operations:
- Input: List[DrumNote] from MIDI parser
- Transform: Pure functions from midi_bridge_core
- Output: GPU rendering via shell.render_rectangles()
"""

from typing import List

from midi_types import DrumNote
from .midi_bridge_core import (
    RenderConfig,
    build_frame_from_drum_notes
)
from .shell import ModernGLContext, render_rectangles


def render_midi_frame(
    ctx: ModernGLContext,
    notes: List[DrumNote],
    current_time: float,
    config: RenderConfig,
    clear_color: tuple = (0.0, 0.0, 0.0)
) -> None:
    """Render a single frame of MIDI notes to GPU
    
    Imperative shell that:
    1. Uses pure functions to transform DrumNotes → rectangle specs
    2. Executes GPU rendering via ModernGL
    
    Side effects:
    - Renders to GPU framebuffer
    - Updates GPU textures
    - Executes shader programs
    
    Args:
        ctx: ModernGL rendering context
        notes: All DrumNotes in sequence
        current_time: Current playback time in seconds
        config: Rendering configuration
        clear_color: Background color RGB (0.0 to 1.0)
    """
    # Pure: Transform MIDI data to GPU format
    frame_data = build_frame_from_drum_notes(notes, current_time, config)
    
    # Impure: Execute GPU rendering
    rectangles = frame_data['rectangles']
    render_rectangles(ctx, rectangles, clear_color)
    
    # TODO: Add circle rendering when shell.py supports it
    # circles = frame_data['circles']
    # render_circles(ctx, circles)


def render_midi_to_frames(
    notes: List[DrumNote],
    width: int = 1920,
    height: int = 1080,
    fps: int = 60,
    duration: float = None,
    corner_radius: float = 12.0,
    blur_radius: float = 5.0,
    glow_strength: float = 0.5,
    fall_speed_multiplier: float = 1.0,
    clear_color: tuple = (0.0, 0.0, 0.0)
):
    """Generator that yields rendered frames for MIDI sequence
    
    Creates GPU context, renders each frame, yields as numpy array.
    This is the main entry point for video generation.
    
    Side effects:
    - Creates/destroys GPU context
    - Allocates/deallocates GPU memory
    - Performs GPU rendering for each frame
    
    Args:
        notes: All DrumNotes in sequence
        width: Frame width in pixels
        height: Frame height in pixels
        fps: Frames per second
        duration: Total duration in seconds (auto-calculated if None)
        corner_radius: Rounded corner radius in pixels
        blur_radius: Gaussian blur radius for glow
        glow_strength: Glow intensity (0.0 to 1.0)
        fall_speed_multiplier: Speed multiplier for note falling
        clear_color: Background color RGB (0.0 to 1.0)
    
    Yields:
        numpy.ndarray: Each frame as RGB image (height, width, 3)
    """
    # Calculate duration if not provided
    if duration is None:
        if not notes:
            return
        max_time = max(note.time for note in notes)
        # Add passthrough time for last note to fall off screen
        duration = max_time + 2.0  # 2 seconds buffer
    
    # Create rendering context
    config = RenderConfig(
        width=width,
        height=height,
        fps=fps,
        fall_speed_multiplier=fall_speed_multiplier
    )
    
    ctx = ModernGLContext(
        width=width,
        height=height,
        corner_radius=corner_radius,
        blur_radius=blur_radius,
        glow_strength=glow_strength
    )
    
    try:
        # Generate frames
        total_frames = int(duration * fps)
        for frame_idx in range(total_frames):
            current_time = frame_idx / fps
            
            # Render frame
            render_midi_frame(ctx, notes, current_time, config, clear_color)
            
            # Read framebuffer to numpy array
            # Note: shell.read_framebuffer() returns RGB data
            from .shell import read_framebuffer
            frame = read_framebuffer(ctx)
            
            yield frame
    
    finally:
        # Cleanup: Release GPU resources
        ctx.cleanup()
