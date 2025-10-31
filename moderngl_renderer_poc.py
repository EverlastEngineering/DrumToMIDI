#!/usr/bin/env python3
"""
ModernGL Renderer - Proof of Concept

GPU-accelerated video rendering using OpenGL.
This is a minimal POC to validate the approach.

Phase 1 Goals:
1. Initialize ModernGL context (headless)
2. Create offscreen framebuffer
3. Render a simple colored rectangle
4. Export frame to image file
"""

import moderngl
import numpy as np
from PIL import Image
import sys


# Vertex shader with instanced rendering support
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

# Fragment shader with rounded corners and anti-aliasing
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


class ModernGLRenderer:
    """GPU-accelerated renderer using ModernGL"""
    
    def __init__(self, width: int = 1920, height: int = 1080, corner_radius: float = 8.0):
        """Initialize ModernGL context and framebuffer
        
        Args:
            width: Frame width in pixels
            height: Frame height in pixels
            corner_radius: Rounded corner radius in pixels
        """
        self.width = width
        self.height = height
        self.corner_radius = corner_radius
        
        # Create standalone OpenGL context (no window required)
        print(f"Initializing ModernGL context ({width}x{height})...")
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
        
        print("✓ ModernGL context initialized successfully")
    
    def render_rectangles(self, rectangles: list) -> None:
        """Render multiple rounded rectangles efficiently using instancing
        
        Args:
            rectangles: List of dicts with keys: 'x', 'y', 'width', 'height', 'color', 'brightness'
                       x, y: Top-left corner in normalized coords (-1 to 1)
                       width, height: Size in normalized coords
                       color: RGB tuple (0.0 to 1.0 per channel)
                       brightness: Multiplier for color (0.0 to 1.0)
        """
        if not rectangles:
            return
        
        num_rects = len(rectangles)
        
        # Build instance data arrays
        colors = []
        rects = []
        sizes = []
        
        for rect in rectangles:
            # Apply brightness to color
            brightness = rect.get('brightness', 1.0)
            color = tuple(c * brightness for c in rect['color'])
            colors.append(color)
            
            # Rectangle position and size (normalized coords)
            x, y = rect['x'], rect['y']
            w, h = rect['width'], rect['height']
            rects.append([x, y - h, w, h])  # Convert top-left to bottom-left
            
            # Size in pixels (for shader anti-aliasing)
            w_pixels = w * self.width / 2.0
            h_pixels = h * self.height / 2.0
            sizes.append([w_pixels, h_pixels])
        
        # Create instance buffers
        color_data = np.array(colors, dtype='f4')
        rect_data = np.array(rects, dtype='f4')
        size_data = np.array(sizes, dtype='f4')
        
        color_vbo = self.ctx.buffer(color_data.tobytes())
        rect_vbo = self.ctx.buffer(rect_data.tobytes())
        size_vbo = self.ctx.buffer(size_data.tobytes())
        
        # Create VAO with instanced attributes
        vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.quad_vbo, '2f', 'in_position'),           # Per-vertex
                (color_vbo, '3f/i', 'in_color'),                 # Per-instance
                (rect_vbo, '4f/i', 'in_rect'),                   # Per-instance
                (size_vbo, '2f/i', 'in_size_pixels'),            # Per-instance
            ]
        )
        
        # Clear background to black
        self.ctx.clear(0.0, 0.0, 0.0)
        
        # Draw all rectangles in one call (instanced rendering)
        vao.render(moderngl.TRIANGLE_STRIP, instances=num_rects)
        
        # Cleanup
        vao.release()
        color_vbo.release()
        rect_vbo.release()
        size_vbo.release()
    
    def get_frame(self) -> np.ndarray:
        """Read current framebuffer as numpy array
        
        Returns:
            RGB numpy array (height, width, 3)
        """
        # Read framebuffer pixels (returns bytes)
        raw = self.fbo.read(components=3)
        
        # Convert to numpy array
        img = np.frombuffer(raw, dtype='u1').reshape((self.height, self.width, 3))
        
        # Flip vertically (OpenGL origin is bottom-left, images are top-left)
        img = np.flip(img, axis=0).copy()
        
        return img
    
    def save_frame(self, filename: str) -> None:
        """Save current frame to image file
        
        Args:
            filename: Output filename (PNG/JPEG)
        """
        frame = self.get_frame()
        img = Image.fromarray(frame, 'RGB')
        img.save(filename)
        print(f"✓ Saved frame to {filename}")
    
    def cleanup(self):
        """Release resources"""
        self.fbo.release()
        self.ctx.release()


def main():
    """Phase 2 test: Render multiple rounded rectangles with different colors and brightness"""
    print("\n" + "="*60)
    print("ModernGL Renderer - Phase 2: Rounded Rectangles & Batching")
    print("="*60 + "\n")
    
    try:
        # Initialize renderer with rounded corners
        renderer = ModernGLRenderer(width=1920, height=1080, corner_radius=12.0)
        
        # Simulate falling drum notes with different colors and velocities
        print("\nRendering multiple notes with rounded corners...")
        
        # Define note colors (matching drum visualization)
        HIHAT_COLOR = (0.0, 1.0, 1.0)    # Cyan
        SNARE_COLOR = (1.0, 0.0, 0.0)    # Red
        KICK_COLOR = (1.0, 0.5, 0.0)     # Orange
        TOM_COLOR = (0.0, 1.0, 0.0)      # Green
        
        notes = [
            # Hihat notes (top lane)
            {'x': -0.8, 'y': 0.8, 'width': 0.15, 'height': 0.06, 
             'color': HIHAT_COLOR, 'brightness': 1.0},
            {'x': -0.5, 'y': 0.6, 'width': 0.15, 'height': 0.06, 
             'color': HIHAT_COLOR, 'brightness': 0.7},
            {'x': -0.2, 'y': 0.4, 'width': 0.15, 'height': 0.06, 
             'color': HIHAT_COLOR, 'brightness': 0.5},
            
            # Snare notes (second lane)
            {'x': -0.45, 'y': 0.7, 'width': 0.15, 'height': 0.06, 
             'color': SNARE_COLOR, 'brightness': 1.0},
            {'x': -0.15, 'y': 0.3, 'width': 0.15, 'height': 0.06, 
             'color': SNARE_COLOR, 'brightness': 0.8},
            
            # Kick notes (third lane - wider)
            {'x': -0.1, 'y': 0.5, 'width': 0.25, 'height': 0.08, 
             'color': KICK_COLOR, 'brightness': 1.0},
            {'x': 0.2, 'y': 0.2, 'width': 0.25, 'height': 0.08, 
             'color': KICK_COLOR, 'brightness': 0.6},
            
            # Tom notes (fourth lane)
            {'x': 0.5, 'y': 0.7, 'width': 0.15, 'height': 0.06, 
             'color': TOM_COLOR, 'brightness': 1.0},
            {'x': 0.5, 'y': 0.4, 'width': 0.15, 'height': 0.06, 
             'color': TOM_COLOR, 'brightness': 0.9},
            {'x': 0.5, 'y': -0.2, 'width': 0.15, 'height': 0.06, 
             'color': TOM_COLOR, 'brightness': 0.4},
        ]
        
        # Render all notes in single batched call
        renderer.render_rectangles(notes)
        
        # Save result
        output_file = "moderngl_phase2_output.png"
        renderer.save_frame(output_file)
        
        print("\n" + "="*60)
        print("SUCCESS! Phase 2 validated:")
        print("  ✓ Rounded corners with anti-aliasing")
        print("  ✓ Instanced rendering (10 notes in 1 draw call)")
        print("  ✓ Per-note colors and brightness")
        print("  ✓ Alpha blending enabled")
        print("  ✓ Efficient GPU batching")
        print(f"\nRendered {len(notes)} notes")
        print(f"Check output: {output_file}")
        print("="*60 + "\n")
        
        # Cleanup
        renderer.cleanup()
        
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
