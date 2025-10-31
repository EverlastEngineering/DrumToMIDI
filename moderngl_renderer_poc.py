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


# Simple vertex shader - transforms vertices to screen space
VERTEX_SHADER = """
#version 330

in vec2 in_position;
in vec3 in_color;

out vec3 v_color;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_color = in_color;
}
"""

# Simple fragment shader - outputs solid color
FRAGMENT_SHADER = """
#version 330

in vec3 v_color;
out vec4 f_color;

void main() {
    f_color = vec4(v_color, 1.0);
}
"""


class ModernGLRenderer:
    """GPU-accelerated renderer using ModernGL"""
    
    def __init__(self, width: int = 1920, height: int = 1080):
        """Initialize ModernGL context and framebuffer
        
        Args:
            width: Frame width in pixels
            height: Frame height in pixels
        """
        self.width = width
        self.height = height
        
        # Create standalone OpenGL context (no window required)
        print(f"Initializing ModernGL context ({width}x{height})...")
        self.ctx = moderngl.create_standalone_context()
        
        # Create offscreen framebuffer
        self.fbo = self.ctx.simple_framebuffer((width, height))
        self.fbo.use()
        
        # Compile shader program
        self.prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER
        )
        
        print("✓ ModernGL context initialized successfully")
    
    def render_rectangle(self, x: float, y: float, width: float, height: float, 
                        color: tuple = (1.0, 0.0, 0.0)) -> None:
        """Render a colored rectangle at specified position
        
        Args:
            x, y: Top-left corner in normalized coords (-1 to 1)
            width, height: Size in normalized coords
            color: RGB color (0.0 to 1.0 per channel)
        """
        # Define rectangle vertices (2 triangles)
        # OpenGL coordinates: (-1, -1) bottom-left, (1, 1) top-right
        vertices = np.array([
            # Triangle 1
            [x, y, *color],                      # Top-left
            [x + width, y, *color],              # Top-right
            [x, y - height, *color],             # Bottom-left
            
            # Triangle 2
            [x + width, y, *color],              # Top-right
            [x + width, y - height, *color],     # Bottom-right
            [x, y - height, *color],             # Bottom-left
        ], dtype='f4')
        
        # Create vertex buffer
        vbo = self.ctx.buffer(vertices.tobytes())
        
        # Create vertex array object
        vao = self.ctx.simple_vertex_array(
            self.prog,
            vbo,
            'in_position', 'in_color'
        )
        
        # Clear background to black
        self.ctx.clear(0.0, 0.0, 0.0)
        
        # Draw the rectangle
        vao.render(moderngl.TRIANGLES)
        
        # Cleanup
        vao.release()
        vbo.release()
    
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
    """POC test: Render a simple colored rectangle"""
    print("\n" + "="*60)
    print("ModernGL Renderer - Proof of Concept")
    print("="*60 + "\n")
    
    try:
        # Initialize renderer
        renderer = ModernGLRenderer(width=1920, height=1080)
        
        # Render a bright cyan rectangle (simulating a drum note)
        # Position: center of screen, size: 200x100 pixels
        # Convert pixel coords to normalized (-1 to 1)
        rect_x = -0.1  # Slightly left of center
        rect_y = 0.05  # Slightly above center
        rect_w = 0.2   # Width in normalized coords
        rect_h = 0.1   # Height in normalized coords
        
        print("\nRendering colored rectangle...")
        renderer.render_rectangle(
            rect_x, rect_y, rect_w, rect_h,
            color=(0.0, 1.0, 1.0)  # Cyan (like a hihat note)
        )
        
        # Save result
        output_file = "moderngl_poc_output.png"
        renderer.save_frame(output_file)
        
        print("\n" + "="*60)
        print("SUCCESS! ModernGL POC validated:")
        print("  ✓ OpenGL context created (headless)")
        print("  ✓ Offscreen framebuffer working")
        print("  ✓ Shaders compiled and executed")
        print("  ✓ Geometry rendered on GPU")
        print("  ✓ Frame exported to image file")
        print(f"\nCheck output: {output_file}")
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
