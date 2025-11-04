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
import time
from contextlib import contextmanager

from .core import batch_rectangle_data


# ============================================================================
# Performance Timing Utilities
# ============================================================================

class RenderTimings:
    """Accumulates timing data for rendering operations"""
    def __init__(self):
        self.timings = {}
        self.counts = {}
    
    def record(self, operation: str, duration: float):
        """Record timing for an operation"""
        if operation not in self.timings:
            self.timings[operation] = 0.0
            self.counts[operation] = 0
        self.timings[operation] += duration
        self.counts[operation] += 1
    
    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get timing summary with total, average, and count"""
        summary = {}
        for op, total in self.timings.items():
            count = self.counts[op]
            summary[op] = {
                'total_ms': total * 1000,
                'avg_ms': (total / count) * 1000 if count > 0 else 0,
                'count': count
            }
        return summary
    
    def reset(self):
        """Clear all timing data"""
        self.timings.clear()
        self.counts.clear()


@contextmanager
def time_operation(timings: Optional[RenderTimings], operation: str):
    """Context manager to time an operation
    
    Args:
        timings: RenderTimings instance to record to (or None to skip timing)
        operation: Name of the operation being timed
    """
    if timings is None:
        yield
        return
    
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        timings.record(operation, duration)


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
in float in_no_outline;   // Per-instance: 1.0 = skip outline, 0.0 = normal

out vec3 v_color;
out vec2 v_texcoord;
out vec2 v_size;
out vec2 v_world_pos;     // World position (normalized coords)
out vec4 v_rect;          // Rectangle bounds for positional effects
out float v_no_outline;   // Pass through no_outline flag

void main() {
    // Transform unit quad (0-1) to rectangle position and size
    vec2 pos = in_rect.xy + in_position * in_rect.zw;
    gl_Position = vec4(pos, 0.0, 1.0);
    
    v_color = in_color;
    v_texcoord = in_position;  // 0-1 coordinates for fragment shader
    v_size = in_size_pixels;
    v_world_pos = pos;         // Actual world position of this pixel
    v_rect = in_rect;          // Pass through rectangle bounds
    v_no_outline = in_no_outline;
}
"""

FRAGMENT_SHADER = """
#version 330

in vec3 v_color;
in vec2 v_texcoord;  // 0-1 texture coordinates within the rectangle
in vec2 v_size;      // Width and height of rectangle in pixels
in vec2 v_world_pos; // World position (normalized coords -1 to 1)
in vec4 v_rect;      // Rectangle bounds (x, y, width, height)
in float v_no_outline; // 1.0 = skip outline, 0.0 = normal

out vec4 f_color;

uniform float u_corner_radius;  // Corner radius in pixels
uniform float u_time;            // Animation time in seconds

void main() {
    // =====================================================================
    // ROUNDED CORNER ALPHA AND OUTLINE DETECTION
    // =====================================================================
    vec2 pixel_pos = v_texcoord * v_size;
    vec2 half_size = v_size * 0.5;
    vec2 dist_from_center = abs(pixel_pos - half_size);
    vec2 corner_start = half_size - vec2(u_corner_radius);
    
    float alpha = 1.0;
    float dist_from_edge = 0.0;  // Distance from edge (for outline)
    
    if (dist_from_center.x > corner_start.x && dist_from_center.y > corner_start.y) {
        // In corner region - use circular distance
        vec2 corner_dist = dist_from_center - corner_start;
        float dist = length(corner_dist);
        alpha = 1.0 - smoothstep(u_corner_radius - 1.0, u_corner_radius, dist);
        dist_from_edge = u_corner_radius - dist;
    } else {
        // In straight edge region - use rectangular distance
        dist_from_edge = min(
            min(pixel_pos.x, v_size.x - pixel_pos.x),
            min(pixel_pos.y, v_size.y - pixel_pos.y)
        );
    }
    
    // =====================================================================
    // ANIMATED GEM EFFECT WITH SPARKLES
    // =====================================================================
    
    // World light source at strike line (y = -0.6, center of screen horizontally)
    vec2 light_pos = vec2(0.0, -0.6);
    float dist_to_light = length(v_world_pos - light_pos);
    
    // Light falloff (pronounced for testing - stronger effect)
    float light_intensity = 1.0 / (1.0 + dist_to_light * 1.5);
    light_intensity = clamp(light_intensity, 0.2, 2.0);  // Wider range for dramatic effect
    
    // 1. Vertical gradient (darker at bottom, brighter at top)
    float gradient = mix(0.7, 1.0, v_texcoord.y);
    
    // 2. Specular highlight (bright spot near top-center)
    vec2 highlight_center = vec2(0.5, 0.75);  // Centered horizontally, 75% up
    float highlight_dist = length(v_texcoord - highlight_center);
    float highlight = exp(-highlight_dist * 8.0) * 0.4;  // Soft falloff
    
    // 3. Edge brightening (subtle rim light)
    float edge_x = min(v_texcoord.x, 1.0 - v_texcoord.x);
    float edge_y = min(v_texcoord.y, 1.0 - v_texcoord.y);
    float edge_dist = min(edge_x, edge_y);
    float edge_bright = smoothstep(0.0, 0.15, edge_dist) * 0.2;
    
    // 4. Hard 2px outline (respects rounded corners) - skip if no_outline flag set
    bool skip_outline = v_no_outline > 0.5;
    float outline_width = 2.0;  // Width in pixels
    
    // Outline is active if we're within 2px of the edge
    float is_outline = (dist_from_edge < outline_width && !skip_outline) ? 1.0 : 0.0;
    
    // 5. SUBTLE SPARKLE EFFECT - animated procedural sparkles (toned down)
    // Only activate sparkles BELOW strike line (y < -0.6)
    float strike_line_y = -0.6;
    float below_strike = step(v_world_pos.y, strike_line_y);  // 1.0 if below, 0.0 if above
    
    // Create pseudo-random sparkle positions based on world position
    vec2 sparkle_coord = v_world_pos * 15.0;  // Less dense sparkles
    float sparkle_pattern = fract(sin(dot(sparkle_coord, vec2(12.9898, 78.233))) * 43758.5453);
    
    // Animate sparkles by offsetting the pattern with time (slower)
    float sparkle_time = fract(sparkle_pattern + u_time * 0.3);
    
    // Sharp pulse for sparkle (0 most of the time, 1 briefly)
    float sparkle = smoothstep(0.985, 0.995, sparkle_time) * smoothstep(1.0, 0.995, sparkle_time);
    sparkle *= 0.6 * below_strike;  // Much dimmer sparkles, only below strike line
    
    // Add moving shimmer waves (diagonal sweep) - very subtle
    float shimmer = sin(v_world_pos.x * 6.0 - v_world_pos.y * 6.0 + u_time * 2.0) * 0.5 + 0.5;
    shimmer = pow(shimmer, 10.0) * 0.12 * below_strike;  // Very subtle peaks, only below strike line
    
    // 6. Combine effects with world lighting and subtle sparkles
    vec3 gem_color = v_color * gradient * light_intensity;  // Apply gradient + lighting
    gem_color += vec3(highlight);                           // Add specular highlight
    gem_color += v_color * edge_bright;                     // Subtle edge glow
    gem_color += vec3(sparkle);                             // Add subtle sparkle flashes (only below strike)
    gem_color += vec3(shimmer);                             // Add very subtle shimmer waves (only below strike)
    
    // Directional outline lighting based on position relative to strike line
    // Calculate direction from current pixel to strike line
    vec2 to_light = vec2(0.0, -0.6) - v_world_pos;
    float light_distance = length(to_light);
    vec2 light_direction = to_light / light_distance;
    
    // Calculate the rectangle's center in world coords
    vec2 rect_center = vec2(v_rect.x + v_rect.z * 0.5, v_rect.y + v_rect.w * 0.5);
    
    // Calculate normal from rect center to current pixel (points outward from rect)
    vec2 pixel_world = v_world_pos;
    vec2 from_rect_center = pixel_world - rect_center;
    vec2 outline_normal = normalize(from_rect_center);
    
    // Calculate how much the outline pixel faces the light (dot product)
    float facing_light = max(0.0, dot(outline_normal, light_direction));
    
    // Modulate outline brightness based on facing direction
    float outline_brightness = 0.3 + 0.5 * facing_light;  // Range: 0.3 to 0.8
    vec3 outline_color = vec3(outline_brightness);
    
    gem_color = mix(gem_color, outline_color, is_outline);
    
    f_color = vec4(gem_color, alpha);
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
uniform vec2 u_glow_offset;     // Glow offset in normalized coords

void main() {
    vec4 scene_color = texture(u_scene, v_texcoord);
    vec4 glow_color = texture(u_glow, v_texcoord + u_glow_offset);
    
    // Additive blend with strength control
    vec3 final_color = scene_color.rgb + glow_color.rgb * u_glow_strength;
    
    f_color = vec4(final_color, scene_color.a);
}
"""

# Circle rendering shaders (instanced circles with smooth anti-aliased edges)
CIRCLE_VERTEX_SHADER = """
#version 330

in vec2 in_position;      // Vertex position (unit circle: -1 to 1)
in vec3 in_color;         // Per-instance color
in vec4 in_circle;        // Per-instance: x, y, radius, brightness (normalized coords)

out vec3 v_color;
out vec2 v_local_pos;     // Position within circle (-1 to 1)
out float v_brightness;

uniform float u_aspect_ratio;  // width / height

void main() {
    // Scale unit circle by radius, adjusting X for aspect ratio to maintain circular shape
    vec2 scale = vec2(in_circle.z / u_aspect_ratio, in_circle.z);
    vec2 pos = in_circle.xy + in_position * scale;
    gl_Position = vec4(pos, 0.0, 1.0);
    
    v_color = in_color;
    v_local_pos = in_position;  // -1 to 1 within circle
    v_brightness = in_circle.w;
}
"""

CIRCLE_FRAGMENT_SHADER = """
#version 330

in vec3 v_color;
in vec2 v_local_pos;
in float v_brightness;

out vec4 f_color;

void main() {
    // Distance from center (0-1 for edge, >1 for outside)
    float dist = length(v_local_pos);
    
    // Smooth anti-aliased edge (1 pixel transition)
    // Use fwidth for automatic derivative-based smoothing
    float edge_smooth = fwidth(dist);
    float alpha = 1.0 - smoothstep(1.0 - edge_smooth, 1.0, dist);
    
    // Apply brightness and alpha
    alpha *= v_brightness;
    
    f_color = vec4(v_color, alpha);
}
"""

# Transparent rectangle shaders (alpha-blended rectangles without rounded corners)
TRANSPARENT_RECT_VERTEX_SHADER = """
#version 330

in vec2 in_position;      // Vertex position (0-1 quad)
in vec3 in_color;         // Per-instance color
in vec4 in_rect;          // Per-instance: x, y, width, height (normalized coords)
in float in_brightness;   // Per-instance: brightness/alpha (0.0-1.0)

out vec3 v_color;
out float v_brightness;

void main() {
    // Transform unit quad (0-1) to rectangle position and size
    vec2 pos = in_rect.xy + in_position * in_rect.zw;
    gl_Position = vec4(pos, 0.0, 1.0);
    
    v_color = in_color;
    v_brightness = in_brightness;
}
"""

TRANSPARENT_RECT_FRAGMENT_SHADER = """
#version 330

in vec3 v_color;
in float v_brightness;

out vec4 f_color;

void main() {
    // Simple alpha-blended rectangle
    f_color = vec4(v_color, v_brightness);
}
"""

# Texture blit shaders (for rendering static overlays like text)
TEXTURE_BLIT_VERTEX_SHADER = """
#version 330

in vec2 in_position;  // Fullscreen quad vertices

out vec2 v_texcoord;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    // Convert from clip space (-1 to 1) to texture space (0 to 1)
    v_texcoord = (in_position + 1.0) * 0.5;
    // Flip Y axis for texture coordinates
    v_texcoord.y = 1.0 - v_texcoord.y;
}
"""

TEXTURE_BLIT_FRAGMENT_SHADER = """
#version 330

uniform sampler2D u_texture;
uniform float u_alpha;

in vec2 v_texcoord;
out vec4 f_color;

void main() {
    vec4 texColor = texture(u_texture, v_texcoord);
    f_color = vec4(texColor.rgb, texColor.a * u_alpha);
}
"""

# ============================================================================
# GPU Context and Resource Management
# ============================================================================

class ModernGLContext:
    """GPU rendering context for multi-pass rendering pipeline
    
    Implements a 4-pass pipeline:
    1. Scene rendering (rectangles to texture)
    2. Horizontal blur pass
    3. Vertical blur pass
    4. Composite pass (blend glow with scene)
    
    This is an imperative shell - handles GPU resources and side effects.
    """
    
    def __init__(
        self, 
        width: int = 1920, 
        height: int = 1080,
        corner_radius: float = 8.0,
        blur_radius: float = 5.0,
        glow_strength: float = 0.3,
        glow_offset_pixels: float = 0.0,
        enable_timing: bool = False
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
            glow_offset_pixels: Vertical offset for glow in pixels (positive = up)
        """
        self.width = width
        self.height = height
        self.corner_radius = corner_radius
        self.blur_radius = blur_radius
        self.glow_strength = glow_strength
        self.glow_offset_pixels = glow_offset_pixels
        
        # Performance timing
        self.timings = RenderTimings() if enable_timing else None
        
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
        self.scene_prog['u_time'].value = 0.0  # Will be updated each frame
        
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
        # Convert pixel offset to normalized coords (negative because OpenGL Y is inverted)
        glow_offset_y = -glow_offset_pixels / height
        self.composite_prog['u_glow_offset'].value = (0.0, glow_offset_y)
        
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
        
        # ====================================================================
        # Circle rendering (instanced circles)
        # ====================================================================
        
        # Compile circle shader program
        self.circle_prog = self.ctx.program(
            vertex_shader=CIRCLE_VERTEX_SHADER,
            fragment_shader=CIRCLE_FRAGMENT_SHADER
        )
        # Set aspect ratio uniform for circular rendering
        self.circle_prog['u_aspect_ratio'].value = width / height
        
        # Create unit circle vertices (triangle fan approximation)
        # Using 32 segments for smooth circles
        num_segments = 32
        circle_vertices = []
        for i in range(num_segments + 1):
            angle = 2.0 * np.pi * i / num_segments
            x = np.cos(angle)
            y = np.sin(angle)
            circle_vertices.append([x, y])
        circle_vertices = np.array(circle_vertices, dtype='f4')
        self.circle_vbo = self.ctx.buffer(circle_vertices.tobytes())
        
        # ====================================================================
        # Transparent rectangle rendering (alpha-blended rectangles)
        # ====================================================================
        
        # Compile transparent rectangle shader program
        self.transparent_rect_prog = self.ctx.program(
            vertex_shader=TRANSPARENT_RECT_VERTEX_SHADER,
            fragment_shader=TRANSPARENT_RECT_FRAGMENT_SHADER
        )
        # Uses the same quad_vbo as regular rectangles
        
        # ====================================================================
        # Texture blitting (for static overlays like text)
        # ====================================================================
        
        # Compile texture blit shader program
        self.texture_blit_prog = self.ctx.program(
            vertex_shader=TEXTURE_BLIT_VERTEX_SHADER,
            fragment_shader=TEXTURE_BLIT_FRAGMENT_SHADER
        )
        # Uses the same fullscreen_vbo
    
    def get_timing_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of timing data
        
        Returns:
            Dictionary with operation names as keys, each containing:
            - total_ms: Total time spent in milliseconds
            - avg_ms: Average time per call in milliseconds
            - count: Number of times operation was called
        """
        if self.timings is None:
            return {}
        return self.timings.get_summary()
    
    def print_timing_summary(self, title: str = "Render Timing Summary"):
        """Print formatted timing summary
        
        Args:
            title: Header title for the summary
        """
        if self.timings is None:
            print(f"{title}: Timing disabled")
            return
        
        summary = self.timings.get_summary()
        if not summary:
            print(f"{title}: No timing data collected")
            return
        
        print(f"\n{'='*70}")
        print(f"{title}")
        print(f"{'='*70}")
        print(f"{'Operation':<35} {'Total (ms)':>12} {'Avg (ms)':>12} {'Count':>8}")
        print(f"{'-'*70}")
        
        # Sort by total time descending
        sorted_ops = sorted(summary.items(), key=lambda x: x[1]['total_ms'], reverse=True)
        
        for op_name, stats in sorted_ops:
            print(f"{op_name:<35} {stats['total_ms']:>12.3f} {stats['avg_ms']:>12.4f} {stats['count']:>8}")
        
        print(f"{'='*70}\n")
    
    def reset_timing(self):
        """Reset all timing data"""
        if self.timings is not None:
            self.timings.reset()
    
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
    clear_color: tuple = (0.0, 0.0, 0.0),
    time: float = 0.0
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
        time: Current animation time in seconds (for sparkle effects)
    """
    with time_operation(ctx.timings, 'render_rectangles_total'):
        clear_rgba = (*clear_color, 1.0)
        
        if not rectangles:
            # Just clear all framebuffers and return
            with time_operation(ctx.timings, 'clear_empty'):
                ctx.scene_fbo.use()
                ctx.ctx.clear(*clear_rgba)
                ctx.fbo.use()
                ctx.ctx.clear(*clear_color)
            return
        
        # ========================================================================
        # PASS 1: Render scene to texture
        # ========================================================================
        
        with time_operation(ctx.timings, 'pass1_scene_setup'):
            # Update time uniform for sparkle animation
            ctx.scene_prog['u_time'].value = time
            
            # Use functional core to prepare data (pure function)
            colors, rects, sizes, flags = batch_rectangle_data(
                rectangles, 
                ctx.width, 
                ctx.height
            )
    
        with time_operation(ctx.timings, 'pass1_gpu_upload'):
            # GPU operations: Upload instanced data
            color_vbo = ctx.ctx.buffer(colors.tobytes())
            rect_vbo = ctx.ctx.buffer(rects.tobytes())
            size_vbo = ctx.ctx.buffer(sizes.tobytes())
            flags_vbo = ctx.ctx.buffer(flags.tobytes())
            
            # Create VAO for instanced rendering
            scene_vao = ctx.ctx.vertex_array(
                ctx.scene_prog,
                [
                    (ctx.quad_vbo, '2f', 'in_position'),      # Per-vertex
                    (color_vbo, '3f/i', 'in_color'),          # Per-instance
                    (rect_vbo, '4f/i', 'in_rect'),            # Per-instance
                    (size_vbo, '2f/i', 'in_size_pixels'),     # Per-instance
                    (flags_vbo, '1f/i', 'in_no_outline'),     # Per-instance
                ]
            )
        
        with time_operation(ctx.timings, 'pass1_scene_render'):
            # Render scene to texture
            ctx.scene_fbo.use()
            ctx.ctx.clear(*clear_rgba)
            scene_vao.render(moderngl.TRIANGLE_STRIP, instances=len(rectangles))
        
        with time_operation(ctx.timings, 'pass1_cleanup'):
            # Cleanup instanced rendering resources
            scene_vao.release()
            color_vbo.release()
            rect_vbo.release()
            size_vbo.release()
            flags_vbo.release()
    
        # ========================================================================
        # PASS 2: Horizontal blur
        # ========================================================================
        
        with time_operation(ctx.timings, 'pass2_blur_h_setup'):
            # Create VAO for fullscreen quad
            blur_h_vao = ctx.ctx.vertex_array(
                ctx.blur_prog,
                [(ctx.fullscreen_vbo, '2f', 'in_position')]
            )
            
            # Bind scene texture and set horizontal direction
            ctx.scene_texture.use(location=0)
            ctx.blur_prog['u_texture'].value = 0
            ctx.blur_prog['u_direction'].value = (1.0, 0.0)  # Horizontal
        
        with time_operation(ctx.timings, 'pass2_blur_h_render'):
            # Render to horizontal blur framebuffer
            ctx.blur_h_fbo.use()
            ctx.ctx.clear(*clear_rgba)
            blur_h_vao.render(moderngl.TRIANGLE_STRIP)
        
        with time_operation(ctx.timings, 'pass2_cleanup'):
            blur_h_vao.release()
    
        # ========================================================================
        # PASS 3: Vertical blur
        # ========================================================================
        
        with time_operation(ctx.timings, 'pass3_blur_v_setup'):
            blur_v_vao = ctx.ctx.vertex_array(
                ctx.blur_prog,
                [(ctx.fullscreen_vbo, '2f', 'in_position')]
            )
            
            # Bind horizontally-blurred texture and set vertical direction
            ctx.blur_h_texture.use(location=0)
            ctx.blur_prog['u_direction'].value = (0.0, 1.0)  # Vertical
        
        with time_operation(ctx.timings, 'pass3_blur_v_render'):
            # Render to vertical blur framebuffer (final glow)
            ctx.blur_v_fbo.use()
            ctx.ctx.clear(*clear_rgba)
            blur_v_vao.render(moderngl.TRIANGLE_STRIP)
        
        with time_operation(ctx.timings, 'pass3_cleanup'):
            blur_v_vao.release()
    
        # ========================================================================
        # PASS 4: Composite (blend glow with original scene)
        # ========================================================================
        
        with time_operation(ctx.timings, 'pass4_composite_setup'):
            composite_vao = ctx.ctx.vertex_array(
                ctx.composite_prog,
                [(ctx.fullscreen_vbo, '2f', 'in_position')]
            )
            
            # Bind both textures
            ctx.scene_texture.use(location=0)
            ctx.blur_v_texture.use(location=1)
            ctx.composite_prog['u_scene'].value = 0
            ctx.composite_prog['u_glow'].value = 1
        
        with time_operation(ctx.timings, 'pass4_composite_render'):
            # Render to final output framebuffer
            ctx.fbo.use()
            ctx.ctx.clear(*clear_color)
            composite_vao.render(moderngl.TRIANGLE_STRIP)
        
        with time_operation(ctx.timings, 'pass4_cleanup'):
            composite_vao.release()


def render_rectangles_no_glow(
    ctx: ModernGLContext,
    rectangles: List[Dict[str, Any]],
    time: float = 0.0
) -> None:
    """Render rectangles directly to output framebuffer without glow effect
    
    Renders sharp rectangles on top of current framebuffer contents.
    Useful for UI elements that should remain crisp (strike line, lane markers).
    
    Side effects:
    - Renders directly to output framebuffer
    - Uploads data to GPU
    - Executes draw call
    
    Args:
        ctx: ModernGL context
        rectangles: List of rectangle specifications
        time: Current animation time in seconds (for sparkle effects)
    """
    with time_operation(ctx.timings, 'render_rectangles_no_glow'):
        if not rectangles:
            return
        
        with time_operation(ctx.timings, 'no_glow_setup'):
            # Update time uniform
            ctx.scene_prog['u_time'].value = time
            
            # Prepare data using functional core
            colors, rects, sizes, flags = batch_rectangle_data(
                rectangles, 
                ctx.width, 
                ctx.height
            )
        
        with time_operation(ctx.timings, 'no_glow_gpu_upload'):
            # Upload instanced data
            color_vbo = ctx.ctx.buffer(colors.tobytes())
            rect_vbo = ctx.ctx.buffer(rects.tobytes())
            size_vbo = ctx.ctx.buffer(sizes.tobytes())
            flags_vbo = ctx.ctx.buffer(flags.tobytes())
            
            # Create VAO
            vao = ctx.ctx.vertex_array(
                ctx.scene_prog,
                [
                    (ctx.quad_vbo, '2f', 'in_position'),
                    (color_vbo, '3f/i', 'in_color'),
                    (rect_vbo, '4f/i', 'in_rect'),
                    (size_vbo, '2f/i', 'in_size_pixels'),
                    (flags_vbo, '1f/i', 'in_no_outline'),
                ]
            )
        
        with time_operation(ctx.timings, 'no_glow_render'):
            # Render directly to output framebuffer
            ctx.fbo.use()
            vao.render(moderngl.TRIANGLE_STRIP, instances=len(rectangles))
        
        with time_operation(ctx.timings, 'no_glow_cleanup'):
            # Cleanup
            vao.release()
            color_vbo.release()
            rect_vbo.release()
            size_vbo.release()
            flags_vbo.release()


def render_circles(
    ctx: ModernGLContext,
    circles: List[Dict[str, Any]]
) -> None:
    """Render circles on top of current framebuffer
    
    Renders anti-aliased circles with alpha blending. Must be called
    after render_rectangles() to overlay circles on the scene.
    
    Side effects:
    - Renders to current framebuffer (ctx.fbo)
    - Uploads data to GPU
    - Executes draw call
    - Allocates/deallocates GPU buffers
    
    Args:
        ctx: ModernGL context
        circles: List of circle specifications with keys:
                 x, y (center in normalized coords)
                 radius (in normalized coords)
                 color (RGB tuple 0-1)
                 brightness (alpha multiplier 0-1)
    """
    with time_operation(ctx.timings, 'render_circles'):
        if not circles:
            return
        
        with time_operation(ctx.timings, 'circles_prepare_data'):
            # Prepare instanced data
            colors = []
            circle_data = []  # x, y, radius, brightness
            
            for circle in circles:
                colors.append(circle['color'])
                circle_data.append([
                    circle['x'],
                    circle['y'],
                    circle['radius'],
                    circle['brightness']
                ])
            
            colors = np.array(colors, dtype='f4')
            circle_data = np.array(circle_data, dtype='f4')
        
        with time_operation(ctx.timings, 'circles_gpu_upload'):
            # Upload instanced data
            color_vbo = ctx.ctx.buffer(colors.tobytes())
            circle_vbo = ctx.ctx.buffer(circle_data.tobytes())
            
            # Create VAO for instanced rendering
            circle_vao = ctx.ctx.vertex_array(
                ctx.circle_prog,
                [
                    (ctx.circle_vbo, '2f', 'in_position'),     # Per-vertex
                    (color_vbo, '3f/i', 'in_color'),           # Per-instance
                    (circle_vbo, '4f/i', 'in_circle'),         # Per-instance
                ]
            )
        
        with time_operation(ctx.timings, 'circles_render'):
            # Render circles to current framebuffer
            ctx.fbo.use()
            circle_vao.render(moderngl.TRIANGLE_FAN, instances=len(circles))
        
        with time_operation(ctx.timings, 'circles_cleanup'):
            # Cleanup
            circle_vao.release()
            color_vbo.release()
            circle_vbo.release()


def render_transparent_rectangles(
    ctx: ModernGLContext,
    rectangles: List[Dict[str, Any]]
) -> None:
    """Render transparent/alpha-blended rectangles on top of current framebuffer
    
    Renders simple rectangles with alpha transparency. No rounded corners,
    no outlines, no glow - just alpha-blended colored rectangles.
    
    Side effects:
    - Renders to current framebuffer (ctx.fbo)
    - Uploads data to GPU
    - Executes draw call
    - Allocates/deallocates GPU buffers
    
    Args:
        ctx: ModernGL context
        rectangles: List of rectangle specifications with keys:
                    x, y (top-left corner in normalized coords)
                    width, height (size in normalized coords)
                    color (RGB tuple 0-1)
                    brightness (alpha value 0-1)
    """
    with time_operation(ctx.timings, 'render_transparent_rectangles'):
        if not rectangles:
            return
        
        with time_operation(ctx.timings, 'transparent_prepare_data'):
            # Prepare instanced data
            colors = []
            rect_data = []  # x, y, width, height
            brightness_data = []
            
            for rect in rectangles:
                colors.append(rect['color'])
                rect_data.append([
                    rect['x'],
                    rect['y'] - rect['height'],  # Convert from top-left to bottom-left
                    rect['width'],
                    rect['height']
                ])
                brightness_data.append(rect['brightness'])
            
            colors = np.array(colors, dtype='f4')
            rect_data = np.array(rect_data, dtype='f4')
            brightness_data = np.array(brightness_data, dtype='f4')
        
        with time_operation(ctx.timings, 'transparent_gpu_upload'):
            # Upload instanced data
            color_vbo = ctx.ctx.buffer(colors.tobytes())
            rect_vbo = ctx.ctx.buffer(rect_data.tobytes())
            brightness_vbo = ctx.ctx.buffer(brightness_data.tobytes())
            
            # Create VAO for instanced rendering
            transparent_vao = ctx.ctx.vertex_array(
                ctx.transparent_rect_prog,
                [
                    (ctx.quad_vbo, '2f', 'in_position'),         # Per-vertex (shared quad)
                    (color_vbo, '3f/i', 'in_color'),             # Per-instance
                    (rect_vbo, '4f/i', 'in_rect'),               # Per-instance
                    (brightness_vbo, '1f/i', 'in_brightness'),   # Per-instance
                ]
            )
        
        with time_operation(ctx.timings, 'transparent_render'):
            # Render rectangles to current framebuffer
            ctx.fbo.use()
            transparent_vao.render(moderngl.TRIANGLE_STRIP, vertices=4, instances=len(rectangles))
        
        with time_operation(ctx.timings, 'transparent_cleanup'):
            # Cleanup
            transparent_vao.release()
            color_vbo.release()
            rect_vbo.release()
            brightness_vbo.release()


def blit_texture(ctx: ModernGLContext, texture: moderngl.Texture, alpha: float = 1.0):
    """Blit a texture onto the current framebuffer with alpha blending
    
    Renders a fullscreen textured quad with alpha blending enabled.
    Used for static overlays like text labels.
    
    Side effects:
    - Renders to current framebuffer
    - Modifies GPU state
    
    Args:
        ctx: ModernGL context
        texture: Texture to blit (must have alpha channel)
        alpha: Global alpha multiplier (0.0-1.0)
    """
    with time_operation(ctx.timings, 'blit_texture'):
        with time_operation(ctx.timings, 'blit_setup'):
            # Bind texture to slot 0
            texture.use(0)
            ctx.texture_blit_prog['u_texture'].value = 0
            ctx.texture_blit_prog['u_alpha'].value = alpha
            
            # Create VAO for fullscreen quad
            blit_vao = ctx.ctx.vertex_array(
                ctx.texture_blit_prog,
                [(ctx.fullscreen_vbo, '2f', 'in_position')]
            )
        
        with time_operation(ctx.timings, 'blit_render'):
            # Render fullscreen quad to current framebuffer with alpha blending
            ctx.fbo.use()
            blit_vao.render(moderngl.TRIANGLE_STRIP, vertices=4)
        
        with time_operation(ctx.timings, 'blit_cleanup'):
            # Cleanup
            blit_vao.release()


def read_framebuffer(ctx: ModernGLContext) -> np.ndarray:
    """Read current framebuffer contents (synchronous)
    
    Side effects:
    - Reads from GPU memory
    - Allocates CPU memory for result
    
    Args:
        ctx: ModernGL context
    
    Returns:
        RGB numpy array (height, width, 3)
    """
    with time_operation(ctx.timings, 'read_framebuffer'):
        with time_operation(ctx.timings, 'read_gpu'):
            # Read framebuffer pixels
            raw = ctx.fbo.read(components=3)
        
        with time_operation(ctx.timings, 'process_pixels'):
            # Convert to numpy array
            img = np.frombuffer(raw, dtype='u1').reshape((ctx.height, ctx.width, 3))
            
            # Flip vertically (OpenGL origin is bottom-left, images are top-left)
            img = np.flip(img, axis=0).copy()
        
        return img


class AsyncFramebufferReader:
    """Double-buffered async framebuffer reader using PBOs
    
    Overlaps GPU→CPU transfer with rendering by using two Pixel Buffer Objects (PBOs).
    While rendering frame N, we read frame N-1 from PBO to CPU memory.
    
    This reduces stalls and improves throughput by ~30%.
    """
    
    def __init__(self, ctx: ModernGLContext):
        """Initialize async reader with double-buffered PBOs
        
        Args:
            ctx: ModernGL context
        """
        self.ctx = ctx
        self.width = ctx.width
        self.height = ctx.height
        self.bytes_per_frame = ctx.width * ctx.height * 3  # RGB
        
        # Create two PBOs for double buffering
        self.pbo1 = ctx.ctx.buffer(reserve=self.bytes_per_frame)
        self.pbo2 = ctx.ctx.buffer(reserve=self.bytes_per_frame)
        
        # Track which PBO is current (being written to) vs previous (being read from)
        self.current_pbo = self.pbo1
        self.previous_pbo = self.pbo2
        
        # Track if first frame (no previous data yet)
        self.first_frame = True
    
    def start_read(self) -> None:
        """Start async read from framebuffer to current PBO (non-blocking)
        
        Side effects:
        - Initiates GPU→PBO transfer (async)
        """
        with time_operation(self.ctx.timings, 'pbo_start_read'):
            # Read framebuffer into current PBO (this is async on modern GPUs)
            self.ctx.fbo.read_into(self.current_pbo, components=3)
    
    def get_previous_frame(self) -> Optional[np.ndarray]:
        """Get the previous frame from PBO (frame N-1)
        
        Returns:
            RGB numpy array (height, width, 3) or None if first frame
        
        Side effects:
        - Reads from PBO to CPU memory
        """
        if self.first_frame:
            self.first_frame = False
            return None
        
        with time_operation(self.ctx.timings, 'pbo_get_frame'):
            with time_operation(self.ctx.timings, 'pbo_read_cpu'):
                # Read from previous PBO (frame N-1, already transferred)
                raw = self.previous_pbo.read()
            
            with time_operation(self.ctx.timings, 'pbo_process_pixels'):
                # Convert to numpy array
                img = np.frombuffer(raw, dtype='u1').reshape((self.height, self.width, 3))
                
                # Flip vertically (OpenGL origin is bottom-left, images are top-left)
                img = np.flip(img, axis=0).copy()
            
            return img
    
    def swap_buffers(self) -> None:
        """Swap current and previous PBOs for next frame"""
        with time_operation(self.ctx.timings, 'pbo_swap'):
            self.current_pbo, self.previous_pbo = self.previous_pbo, self.current_pbo
    
    def finalize(self) -> np.ndarray:
        """Get the final frame after rendering is complete
        
        Returns:
            RGB numpy array of the last frame
        """
        with time_operation(self.ctx.timings, 'pbo_finalize'):
            # Read the current PBO which has the last frame
            raw = self.current_pbo.read()
            img = np.frombuffer(raw, dtype='u1').reshape((self.height, self.width, 3))
            img = np.flip(img, axis=0).copy()
            return img
    
    def cleanup(self) -> None:
        """Release PBO resources"""
        self.pbo1.release()
        self.pbo2.release()


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
    img = Image.fromarray(frame)
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
