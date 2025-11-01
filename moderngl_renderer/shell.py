"""
ModernGL Renderer - Imperative Shell

Handles all GPU operations and side effects.
Uses pure functions from moderngl_core for calculations.

Follows functional core, imperative shell pattern:
- moderngl_core.py: Pure transformations (testable, predictable)
- This module: GPU operations (side effects, resources, I/O)
"""

import moderngl
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Optional
from pathlib import Path

from .core import batch_rectangle_data


# ============================================================================
# Shader Source Code
# ============================================================================

VERTEX_SHADER = """
#version 330

in vec2 in_position;      // Vertex position (0-1 quad)
in vec3 in_color;         // Per-instance color
in vec4 in_rect;          // Per-instance: x, y, width, height (normalized coords)
in vec2 in_size_pixels;   // Per-instance: width, height in pixels

out vec3 v_color;
out vec2 v_texcoord;
out vec2 v_size;

void main() {
    // Transform unit quad (0-1) to rectangle position and size
    vec2 pos = in_rect.xy + in_position * in_rect.zw;
    gl_Position = vec4(pos, 0.0, 1.0);
    
    v_color = in_color;
    v_texcoord = in_position;  // 0-1 coordinates for fragment shader
    v_size = in_size_pixels;
}
"""

FRAGMENT_SHADER = """
#version 330

in vec3 v_color;
in vec2 v_texcoord;  // 0-1 texture coordinates within the rectangle
in vec2 v_size;      // Width and height of rectangle in pixels

out vec4 f_color;

uniform float u_corner_radius;  // Corner radius in pixels

void main() {
    // Calculate distance from edges
    vec2 pixel_pos = v_texcoord * v_size;
    vec2 half_size = v_size * 0.5;
    
    // Distance from center to this pixel
    vec2 dist_from_center = abs(pixel_pos - half_size);
    
    // Corner boundaries (where rounding starts)
    vec2 corner_start = half_size - vec2(u_corner_radius);
    
    // If we're in the corner region, calculate distance from corner circle
    float alpha = 1.0;
    if (dist_from_center.x > corner_start.x && dist_from_center.y > corner_start.y) {
        // Distance from corner circle center
        vec2 corner_dist = dist_from_center - corner_start;
        float dist = length(corner_dist);
        
        // Smooth anti-aliased edge (1 pixel transition)
        alpha = 1.0 - smoothstep(u_corner_radius - 1.0, u_corner_radius, dist);
    }
    
    f_color = vec4(v_color, alpha);
}
"""


# ============================================================================
# GPU Context and Resource Management
# ============================================================================

class ModernGLContext:
    """Manages ModernGL context and resources (imperative shell)"""
    
    def __init__(self, width: int, height: int, corner_radius: float = 12.0):
        """Initialize GPU context and resources
        
        Side effects:
        - Creates OpenGL context
        - Allocates GPU memory for framebuffer
        - Compiles shaders
        
        Args:
            width: Frame width in pixels
            height: Frame height in pixels
            corner_radius: Rounded corner radius in pixels
        """
        self.width = width
        self.height = height
        self.corner_radius = corner_radius
        
        # Create standalone OpenGL context (no window required)
        self.ctx = moderngl.create_standalone_context()
        
        # Enable blending for transparency
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Create offscreen framebuffer
        self.fbo = self.ctx.simple_framebuffer((width, height))
        self.fbo.use()
        
        # Compile shader program
        self.prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER
        )
        
        # Set corner radius uniform
        self.prog['u_corner_radius'].value = corner_radius
        
        # Create unit quad vertices (will be instanced for each rectangle)
        quad_vertices = np.array([
            [0, 0],  # Bottom-left
            [1, 0],  # Bottom-right
            [0, 1],  # Top-left
            [1, 1],  # Top-right
        ], dtype='f4')
        
        self.quad_vbo = self.ctx.buffer(quad_vertices.tobytes())
    
    def cleanup(self):
        """Release GPU resources
        
        Side effects:
        - Frees GPU memory
        - Destroys OpenGL context
        """
        self.quad_vbo.release()
        self.fbo.release()
        self.ctx.release()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.cleanup()


# ============================================================================
# GPU Rendering Operations
# ============================================================================

def render_rectangles(
    ctx: ModernGLContext,
    rectangles: List[Dict[str, Any]],
    clear_color: tuple = (0.0, 0.0, 0.0)
) -> None:
    """Render rectangles to GPU framebuffer
    
    Side effects:
    - Clears framebuffer
    - Uploads data to GPU
    - Executes draw calls
    - Allocates/deallocates GPU buffers
    
    Args:
        ctx: ModernGL context
        rectangles: List of rectangle specifications
        clear_color: Background color RGB (0.0 to 1.0)
    """
    if not rectangles:
        ctx.ctx.clear(*clear_color)
        return
    
    # Use functional core to prepare data (pure function)
    colors, rects, sizes = batch_rectangle_data(
        rectangles, 
        ctx.width, 
        ctx.height
    )
    
    # GPU operations (side effects)
    color_vbo = ctx.ctx.buffer(colors.tobytes())
    rect_vbo = ctx.ctx.buffer(rects.tobytes())
    size_vbo = ctx.ctx.buffer(sizes.tobytes())
    
    # Create VAO with instanced attributes
    vao = ctx.ctx.vertex_array(
        ctx.prog,
        [
            (ctx.quad_vbo, '2f', 'in_position'),      # Per-vertex
            (color_vbo, '3f/i', 'in_color'),          # Per-instance
            (rect_vbo, '4f/i', 'in_rect'),            # Per-instance
            (size_vbo, '2f/i', 'in_size_pixels'),     # Per-instance
        ]
    )
    
    # Clear and render
    ctx.ctx.clear(*clear_color)
    vao.render(moderngl.TRIANGLE_STRIP, instances=len(rectangles))
    
    # Cleanup GPU resources
    vao.release()
    color_vbo.release()
    rect_vbo.release()
    size_vbo.release()


def read_framebuffer(ctx: ModernGLContext) -> np.ndarray:
    """Read current framebuffer contents
    
    Side effects:
    - Reads from GPU memory
    - Allocates CPU memory for result
    
    Args:
        ctx: ModernGL context
    
    Returns:
        RGB numpy array (height, width, 3)
    """
    # Read framebuffer pixels
    raw = ctx.fbo.read(components=3)
    
    # Convert to numpy array
    img = np.frombuffer(raw, dtype='u1').reshape((ctx.height, ctx.width, 3))
    
    # Flip vertically (OpenGL origin is bottom-left, images are top-left)
    img = np.flip(img, axis=0).copy()
    
    return img


def save_frame(ctx: ModernGLContext, filepath: str) -> None:
    """Save current framebuffer to image file
    
    Side effects:
    - Reads from GPU
    - Writes to filesystem
    
    Args:
        ctx: ModernGL context
        filepath: Output file path
    """
    frame = read_framebuffer(ctx)
    img = Image.fromarray(frame, 'RGB')
    img.save(filepath)


# ============================================================================
# High-Level Rendering Functions
# ============================================================================

def render_frame_to_file(
    rectangles: List[Dict[str, Any]],
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    corner_radius: float = 12.0
) -> None:
    """High-level function: Render rectangles and save to file
    
    Side effects:
    - Creates GPU context
    - Renders to GPU
    - Writes to filesystem
    - Cleans up GPU resources
    
    Args:
        rectangles: List of rectangle specifications
        output_path: Where to save the image
        width, height: Frame dimensions
        corner_radius: Corner radius in pixels
    """
    with ModernGLContext(width, height, corner_radius) as ctx:
        render_rectangles(ctx, rectangles)
        save_frame(ctx, output_path)


def render_frames_to_array(
    frames: List[List[Dict[str, Any]]],
    width: int = 1920,
    height: int = 1080,
    corner_radius: float = 12.0
) -> List[np.ndarray]:
    """High-level function: Render multiple frames efficiently
    
    Reuses GPU context across frames for performance.
    
    Side effects:
    - Creates GPU context once
    - Renders multiple frames to GPU
    - Reads from GPU memory
    - Cleans up GPU resources
    
    Args:
        frames: List of frame specs, each frame is a list of rectangles
        width, height: Frame dimensions
        corner_radius: Corner radius in pixels
    
    Returns:
        List of numpy arrays, one per frame
    """
    results = []
    
    with ModernGLContext(width, height, corner_radius) as ctx:
        for rectangles in frames:
            render_rectangles(ctx, rectangles)
            frame_data = read_framebuffer(ctx)
            results.append(frame_data)
    
    return results
