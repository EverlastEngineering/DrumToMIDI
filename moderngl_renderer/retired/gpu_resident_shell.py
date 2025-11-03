"""
GPU-Resident MIDI Renderer - Imperative Shell

Manages GPU-resident rendering with persistent buffers.
All note geometry uploaded once, animation via time uniform updates.
"""

import moderngl
import numpy as np
import time
from typing import List, Generator
from midi_types import DrumNote

from .gpu_resident_core import (
    precompute_all_note_instances,
    calculate_render_params
)
from .gpu_resident_shaders import (
    TIME_ANIMATED_VERTEX_SHADER,
    TIME_ANIMATED_FRAGMENT_SHADER
)


class GPUResidentContext:
    """ModernGL context with GPU-resident note buffers
    
    Architecture:
    1. Initialization: Upload all notes to GPU buffer once
    2. Per-frame: Update only time uniform (4 bytes)
    3. GPU: Vertex shader animates positions, culls invisible notes
    4. GPU: Fragment shader renders with rounded corners
    5. Read framebuffer to numpy array
    
    Benefits:
    - Zero per-frame geometry uploads
    - GPU-parallel visibility culling
    - GPU-parallel position animation
    - Minimal CPU involvement per frame
    """
    
    def __init__(
        self,
        notes: List[DrumNote],
        width: int = 1920,
        height: int = 1080,
        fps: int = 60,
        fall_speed_multiplier: float = 1.0,
        corner_radius: float = 12.0
    ):
        """Initialize GPU context and upload all notes to persistent buffer
        
        Side effects:
        - Creates OpenGL context
        - Allocates GPU memory for note buffer (persistent)
        - Compiles shader program
        - Uploads all note geometry to GPU
        
        Args:
            notes: All DrumNotes in sequence (uploaded once)
            width: Frame width in pixels
            height: Frame height in pixels
            fps: Frames per second
            fall_speed_multiplier: Note fall speed multiplier
            corner_radius: Rounded corner radius in pixels
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.corner_radius = corner_radius
        
        # Calculate rendering parameters
        self.params = calculate_render_params(width, height, fall_speed_multiplier)
        
        # Create OpenGL context
        self.ctx = moderngl.create_standalone_context()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Create framebuffer for rendering
        self.fbo = self.ctx.simple_framebuffer((width, height))
        self.fbo.use()
        
        # Compile shader program
        self.program = self.ctx.program(
            vertex_shader=TIME_ANIMATED_VERTEX_SHADER,
            fragment_shader=TIME_ANIMATED_FRAGMENT_SHADER
        )
        
        # Set static uniforms (never change)
        self.program['u_corner_radius'].value = corner_radius
        self.program['u_screen_size'].value = (width, height)
        self.program['u_strike_line_y_norm'].value = self.params['strike_line_y_norm']
        self.program['u_pixels_per_second'].value = self.params['pixels_per_second']
        self.program['u_lookahead_time'].value = self.params['lookahead_time']
        self.program['u_passthrough_time'].value = self.params['passthrough_time']
        
        # Pre-compute all note instances
        instance_data, self.num_instances = precompute_all_note_instances(
            notes=notes,
            width=width,
            height=height,
            pixels_per_second=self.params['pixels_per_second'],
            strike_line_y=self.params['strike_line_y']
        )
        
        # Upload to GPU - THIS HAPPENS ONCE!
        self._upload_persistent_buffer(instance_data)
        
        print(f"GPU-Resident: Uploaded {self.num_instances} notes to GPU buffer (one-time)")
    
    def _upload_persistent_buffer(self, instance_data: np.ndarray):
        """Upload note instance data to persistent GPU buffer
        
        Side effect: Allocates GPU memory and uploads data.
        This is called ONCE at initialization.
        
        Args:
            instance_data: numpy structured array of note instances
        """
        # Create unit quad vertices (reused for all instances)
        quad_vertices = np.array([
            [0.0, 0.0],  # Bottom-left
            [1.0, 0.0],  # Bottom-right
            [0.0, 1.0],  # Top-left
            [1.0, 1.0],  # Top-right
        ], dtype='f4')
        
        # Create vertex buffer for quad
        self.vbo_quad = self.ctx.buffer(quad_vertices.tobytes())
        
        # Create buffer for instance data (persistent)
        if self.num_instances > 0:
            self.vbo_instances = self.ctx.buffer(instance_data.tobytes())
        else:
            # Empty buffer for edge case
            self.vbo_instances = self.ctx.buffer(reserve=1024)
        
        # Create VAO (vertex array object) that describes buffer layout
        self.vao = self.ctx.vertex_array(
            self.program,
            [
                # Quad vertices (per-vertex)
                (self.vbo_quad, '2f', 'in_position'),
                
                # Instance attributes (per-instance, uploaded once)
                (self.vbo_instances, '4f 3f 2f 2f/i', 
                 'in_base_rect', 'in_color', 'in_timing', 'in_size_pixels'),
            ]
        )
    
    def render_frame(self, current_time: float):
        """Render frame at given time
        
        Only updates time uniform - all geometry already on GPU.
        
        Side effects:
        - Updates GPU uniform (4 bytes)
        - Executes GPU rendering
        
        Args:
            current_time: Current playback time in seconds
        """
        # Clear framebuffer
        self.fbo.clear(0.0, 0.0, 0.0, 1.0)
        
        # Update time uniform (THIS IS ALL THAT CHANGES PER FRAME!)
        self.program['u_current_time'].value = current_time
        
        # Render all instances (GPU culls invisible ones in vertex shader)
        if self.num_instances > 0:
            self.vao.render(moderngl.TRIANGLE_STRIP, instances=self.num_instances)
    
    def read_framebuffer(self) -> np.ndarray:
        """Read framebuffer to numpy array
        
        Side effect: GPU→CPU transfer (unavoidable for FFmpeg).
        
        Returns:
            numpy array (height, width, 3) of RGB data
        """
                # Read RGB data from framebuffer
        data = self.fbo.read(components=3)
        
        # Convert to numpy array and reshape
        image = np.frombuffer(data, dtype=np.uint8)
        image = image.reshape((self.height, self.width, 3))
        
        # Flip vertically (OpenGL origin is bottom-left)
        image = np.flipud(image).copy()  # .copy() ensures contiguous memory
        
        return image
    
    def cleanup(self):
        """Release GPU resources
        
        Side effect: Frees GPU memory.
        """
        if hasattr(self, 'vao'):
            self.vao.release()
        if hasattr(self, 'vbo_quad'):
            self.vbo_quad.release()
        if hasattr(self, 'vbo_instances'):
            self.vbo_instances.release()
        if hasattr(self, 'fbo'):
            self.fbo.release()
        if hasattr(self, 'ctx'):
            self.ctx.release()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False


def render_midi_to_frames_gpu_resident(
    notes: List[DrumNote],
    duration: float,
    width: int = 1920,
    height: int = 1080,
    fps: int = 60,
    fall_speed_multiplier: float = 1.0,
    corner_radius: float = 12.0
) -> Generator[np.ndarray, None, None]:
    """Generate frames using GPU-resident rendering
    
    This is the GPU-optimized replacement for render_midi_to_frames().
    
    Key differences:
    - Uploads all notes to GPU ONCE at start
    - Per-frame only updates time uniform (4 bytes)
    - GPU handles animation and visibility culling
    
    Side effects:
    - Creates/destroys GPU context
    - Allocates/deallocates GPU memory
    - Performs GPU rendering for each frame
    
    Args:
        notes: All DrumNotes in sequence
        duration: Total duration in seconds
        width: Frame width in pixels
        height: Frame height in pixels
        fps: Frames per second
        fall_speed_multiplier: Note fall speed multiplier
        corner_radius: Rounded corner radius in pixels
        
    Yields:
        numpy.ndarray: Each frame as RGB image (height, width, 3)
    """
    # Create GPU context and upload notes ONCE
    init_start = time.perf_counter()
    with GPUResidentContext(
        notes=notes,
        width=width,
        height=height,
        fps=fps,
        fall_speed_multiplier=fall_speed_multiplier,
        corner_radius=corner_radius
    ) as ctx:
        init_time = time.perf_counter() - init_start
        print(f"DEBUG: GPU initialization took {init_time:.3f}s")
        
        # Generate frames
        total_frames = int(duration * fps)
        
        # Profile first 100 frames
        render_times = []
        readback_times = []
        
        for frame_idx in range(total_frames):
            current_time = frame_idx / fps
            
            # Render frame (only updates time uniform)
            t0 = time.perf_counter()
            ctx.render_frame(current_time)
            t1 = time.perf_counter()
            
            # Read framebuffer
            frame = ctx.read_framebuffer()
            t2 = time.perf_counter()
            
            if frame_idx < 100:
                render_times.append(t1 - t0)
                readback_times.append(t2 - t1)
            
            if frame_idx == 99:
                avg_render = sum(render_times) / len(render_times) * 1000
                avg_readback = sum(readback_times) / len(readback_times) * 1000
                print(f"DEBUG: Avg render time: {avg_render:.3f}ms, Avg readback: {avg_readback:.3f}ms")
            
            yield frame
