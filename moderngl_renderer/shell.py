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

# Scene rendering shader (instanced rectangles with rounded corners)
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

# Full-screen quad vertex shader for post-processing passes
FULLSCREEN_VERTEX_SHADER = """
#version 330

in vec2 in_position;
out vec2 v_texcoord;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_texcoord = in_position * 0.5 + 0.5;  // Convert from [-1,1] to [0,1]
}
"""

# Gaussian blur fragment shader (separable, single direction)
BLUR_FRAGMENT_SHADER = """
#version 330

in vec2 v_texcoord;
out vec4 f_color;

uniform sampler2D u_texture;
uniform vec2 u_direction;  // (1,0) for horizontal, (0,1) for vertical
uniform float u_blur_radius;  // Blur radius in pixels

void main() {
    vec2 tex_size = textureSize(u_texture, 0);
    vec2 pixel_size = 1.0 / tex_size;
    
    // Gaussian kernel weights for radius 5 (11-tap filter)
    // Weights sum to 1.0
    float weights[11] = float[](
        0.0093, 0.0280, 0.0656, 0.1210, 0.1747,
        0.1974,
        0.1747, 0.1210, 0.0656, 0.0280, 0.0093
    );
    
    vec4 color = vec4(0.0);
    float total_weight = 0.0;
    
    // Sample along blur direction
    for (int i = -5; i <= 5; i++) {
        float weight = weights[i + 5];
        vec2 offset = u_direction * pixel_size * float(i) * u_blur_radius;
        color += texture(u_texture, v_texcoord + offset) * weight;
        total_weight += weight;
    }
    
    f_color = color / total_weight;
}
"""

# Composite shader (blend glow with original scene)
COMPOSITE_FRAGMENT_SHADER = """
#version 330

in vec2 v_texcoord;
out vec4 f_color;

uniform sampler2D u_scene;     // Original scene
uniform sampler2D u_glow;      // Blurred glow
uniform float u_glow_strength;  // Glow intensity multiplier

void main() {
    vec4 scene_color = texture(u_scene, v_texcoord);
    vec4 glow_color = texture(u_glow, v_texcoord);
    
    // Additive blend with strength control
    vec3 final_color = scene_color.rgb + glow_color.rgb * u_glow_strength;
    
    f_color = vec4(final_color, scene_color.a);
}
"""


# ============================================================================
# GPU Context and Resource Management
# ============================================================================

class ModernGLContext:
    """Manages ModernGL context and resources for multi-pass rendering"""
    
    def __init__(
        self, 
        width: int, 
        height: int, 
        corner_radius: float = 12.0,
        blur_radius: float = 5.0,
        glow_strength: float = 0.5
    ):
        """Initialize GPU context and resources for multi-pass rendering
        
        Multi-pass pipeline:
        1. Render scene to texture (scene_fbo)
        2. Horizontal blur pass (blur_h_fbo)
        3. Vertical blur pass (blur_v_fbo)
        4. Composite glow + scene to output (fbo)
        
        Side effects:
        - Creates OpenGL context
        - Allocates GPU memory for 4 framebuffers + textures
        - Compiles 4 shader programs
        
        Args:
            width: Frame width in pixels
            height: Frame height in pixels
            corner_radius: Rounded corner radius in pixels
            blur_radius: Gaussian blur radius (higher = more blur)
            glow_strength: Glow intensity (0.0 = none, 1.0 = full)
        """
        self.width = width
        self.height = height
        self.corner_radius = corner_radius
        self.blur_radius = blur_radius
        self.glow_strength = glow_strength
        
        # Create standalone OpenGL context (no window required)
        self.ctx = moderngl.create_standalone_context()
        
        # Enable blending for transparency
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # ====================================================================
        # Pass 1: Scene rendering (instanced rectangles)
        # ====================================================================
        
        # Scene texture (RGBA for alpha blending)
        self.scene_texture = self.ctx.texture((width, height), 4)
        self.scene_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        
        self.scene_fbo = self.ctx.framebuffer(color_attachments=[self.scene_texture])
        
        # Compile scene shader program
        self.scene_prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER
        )
        self.scene_prog['u_corner_radius'].value = corner_radius
        
        # Create unit quad vertices for instanced rendering
        quad_vertices = np.array([
            [0, 0],  # Bottom-left
            [1, 0],  # Bottom-right
            [0, 1],  # Top-left
            [1, 1],  # Top-right
        ], dtype='f4')
        self.quad_vbo = self.ctx.buffer(quad_vertices.tobytes())
        
        # ====================================================================
        # Passes 2-3: Blur passes (horizontal and vertical)
        # ====================================================================
        
        # Horizontal blur texture
        self.blur_h_texture = self.ctx.texture((width, height), 4)
        self.blur_h_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.blur_h_fbo = self.ctx.framebuffer(color_attachments=[self.blur_h_texture])
        
        # Vertical blur texture (final blurred result)
        self.blur_v_texture = self.ctx.texture((width, height), 4)
        self.blur_v_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.blur_v_fbo = self.ctx.framebuffer(color_attachments=[self.blur_v_texture])
        
        # Compile blur shader program
        self.blur_prog = self.ctx.program(
            vertex_shader=FULLSCREEN_VERTEX_SHADER,
            fragment_shader=BLUR_FRAGMENT_SHADER
        )
        self.blur_prog['u_blur_radius'].value = blur_radius
        
        # ====================================================================
        # Pass 4: Composite pass (blend glow with scene)
        # ====================================================================
        
        # Final output framebuffer
        self.fbo = self.ctx.simple_framebuffer((width, height))
        
        # Compile composite shader program
        self.composite_prog = self.ctx.program(
            vertex_shader=FULLSCREEN_VERTEX_SHADER,
            fragment_shader=COMPOSITE_FRAGMENT_SHADER
        )
        self.composite_prog['u_glow_strength'].value = glow_strength
        
        # ====================================================================
        # Fullscreen quad for post-processing passes
        # ====================================================================
        
        fullscreen_quad = np.array([
            [-1, -1],  # Bottom-left
            [ 1, -1],  # Bottom-right
            [-1,  1],  # Top-left
            [ 1,  1],  # Top-right
        ], dtype='f4')
        self.fullscreen_vbo = self.ctx.buffer(fullscreen_quad.tobytes())
    
    def cleanup(self):
        """Release GPU resources
        
        Side effects:
        - Frees GPU memory for all framebuffers and textures
        - Destroys OpenGL context
        """
        # Release buffers
        self.quad_vbo.release()
        self.fullscreen_vbo.release()
        
        # Release framebuffers
        self.scene_fbo.release()
        self.blur_h_fbo.release()
        self.blur_v_fbo.release()
        self.fbo.release()
        
        # Release textures
        self.scene_texture.release()
        self.blur_h_texture.release()
        self.blur_v_texture.release()
        
        # Release context
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
    """Render rectangles using multi-pass pipeline with glow
    
    Multi-pass pipeline:
    1. Render scene to texture (scene_fbo)
    2. Apply horizontal blur to scene (blur_h_fbo)
    3. Apply vertical blur (blur_v_fbo) - this is the glow
    4. Composite glow + original scene to final output (fbo)
    
    Side effects:
    - Renders to 4 different framebuffers
    - Uploads data to GPU
    - Executes 4 separate draw calls
    - Allocates/deallocates GPU buffers
    
    Args:
        ctx: ModernGL context
        rectangles: List of rectangle specifications
        clear_color: Background color RGB (0.0 to 1.0)
    """
    clear_rgba = (*clear_color, 1.0)
    
    if not rectangles:
        # Just clear all framebuffers and return
        ctx.scene_fbo.use()
        ctx.ctx.clear(*clear_rgba)
        ctx.fbo.use()
        ctx.ctx.clear(*clear_color)
        return
    
    # ========================================================================
    # PASS 1: Render scene to texture
    # ========================================================================
    
    # Use functional core to prepare data (pure function)
    colors, rects, sizes = batch_rectangle_data(
        rectangles, 
        ctx.width, 
        ctx.height
    )
    
    # GPU operations: Upload instanced data
    color_vbo = ctx.ctx.buffer(colors.tobytes())
    rect_vbo = ctx.ctx.buffer(rects.tobytes())
    size_vbo = ctx.ctx.buffer(sizes.tobytes())
    
    # Create VAO for instanced rendering
    scene_vao = ctx.ctx.vertex_array(
        ctx.scene_prog,
        [
            (ctx.quad_vbo, '2f', 'in_position'),      # Per-vertex
            (color_vbo, '3f/i', 'in_color'),          # Per-instance
            (rect_vbo, '4f/i', 'in_rect'),            # Per-instance
            (size_vbo, '2f/i', 'in_size_pixels'),     # Per-instance
        ]
    )
    
    # Render scene to texture
    ctx.scene_fbo.use()
    ctx.ctx.clear(*clear_rgba)
    scene_vao.render(moderngl.TRIANGLE_STRIP, instances=len(rectangles))
    
    # Cleanup instanced rendering resources
    scene_vao.release()
    color_vbo.release()
    rect_vbo.release()
    size_vbo.release()
    
    # ========================================================================
    # PASS 2: Horizontal blur
    # ========================================================================
    
    # Create VAO for fullscreen quad
    blur_h_vao = ctx.ctx.vertex_array(
        ctx.blur_prog,
        [(ctx.fullscreen_vbo, '2f', 'in_position')]
    )
    
    # Bind scene texture and set horizontal direction
    ctx.scene_texture.use(location=0)
    ctx.blur_prog['u_texture'].value = 0
    ctx.blur_prog['u_direction'].value = (1.0, 0.0)  # Horizontal
    
    # Render to horizontal blur framebuffer
    ctx.blur_h_fbo.use()
    ctx.ctx.clear(*clear_rgba)
    blur_h_vao.render(moderngl.TRIANGLE_STRIP)
    
    blur_h_vao.release()
    
    # ========================================================================
    # PASS 3: Vertical blur
    # ========================================================================
    
    blur_v_vao = ctx.ctx.vertex_array(
        ctx.blur_prog,
        [(ctx.fullscreen_vbo, '2f', 'in_position')]
    )
    
    # Bind horizontally-blurred texture and set vertical direction
    ctx.blur_h_texture.use(location=0)
    ctx.blur_prog['u_direction'].value = (0.0, 1.0)  # Vertical
    
    # Render to vertical blur framebuffer (final glow)
    ctx.blur_v_fbo.use()
    ctx.ctx.clear(*clear_rgba)
    blur_v_vao.render(moderngl.TRIANGLE_STRIP)
    
    blur_v_vao.release()
    
    # ========================================================================
    # PASS 4: Composite (blend glow with original scene)
    # ========================================================================
    
    composite_vao = ctx.ctx.vertex_array(
        ctx.composite_prog,
        [(ctx.fullscreen_vbo, '2f', 'in_position')]
    )
    
    # Bind both textures
    ctx.scene_texture.use(location=0)
    ctx.blur_v_texture.use(location=1)
    ctx.composite_prog['u_scene'].value = 0
    ctx.composite_prog['u_glow'].value = 1
    
    # Render to final output framebuffer
    ctx.fbo.use()
    ctx.ctx.clear(*clear_color)
    composite_vao.render(moderngl.TRIANGLE_STRIP)
    
    composite_vao.release()


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
    corner_radius: float = 12.0,
    blur_radius: float = 5.0,
    glow_strength: float = 0.5
) -> None:
    """High-level function: Render rectangles with glow and save to file
    
    Uses multi-pass rendering pipeline for quality glow effect.
    
    Side effects:
    - Creates GPU context
    - Renders to GPU (4 passes)
    - Writes to filesystem
    - Cleans up GPU resources
    
    Args:
        rectangles: List of rectangle specifications
        output_path: Where to save the image
        width, height: Frame dimensions
        corner_radius: Corner radius in pixels
        blur_radius: Gaussian blur radius for glow
        glow_strength: Glow intensity (0.0-1.0)
    """
    with ModernGLContext(
        width, height, corner_radius, 
        blur_radius, glow_strength
    ) as ctx:
        render_rectangles(ctx, rectangles)
        save_frame(ctx, output_path)


def render_frames_to_array(
    frames: List[List[Dict[str, Any]]],
    width: int = 1920,
    height: int = 1080,
    corner_radius: float = 12.0,
    blur_radius: float = 5.0,
    glow_strength: float = 0.5
) -> List[np.ndarray]:
    """High-level function: Render multiple frames efficiently with glow
    
    Reuses GPU context across frames for performance.
    Uses multi-pass rendering pipeline (4 passes per frame).
    
    Side effects:
    - Creates GPU context once
    - Renders multiple frames to GPU (4 passes each)
    - Reads from GPU memory
    - Cleans up GPU resources
    
    Args:
        frames: List of frame specs, each frame is a list of rectangles
        width, height: Frame dimensions
        corner_radius: Corner radius in pixels
        blur_radius: Gaussian blur radius for glow
        glow_strength: Glow intensity (0.0-1.0)
    
    Returns:
        List of numpy arrays, one per frame
    """
    results = []
    
    with ModernGLContext(
        width, height, corner_radius,
        blur_radius, glow_strength
    ) as ctx:
        for rectangles in frames:
            render_rectangles(ctx, rectangles)
            frame_data = read_framebuffer(ctx)
            results.append(frame_data)
    
    return results
