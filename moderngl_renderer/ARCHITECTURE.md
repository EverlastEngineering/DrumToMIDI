# ModernGL Renderer Architecture

## Design Pattern: Functional Core, Imperative Shell

The ModernGL renderer strictly separates pure logic (functional core) from side effects (imperative shell).

## Module Organization

### Functional Core (Pure Functions)
**No side effects, no I/O, no GPU operations - only calculations.**

- **`core.py`** - Coordinate transformations, data preparation
  - Coordinate system conversions
  - Rectangle batching for GPU upload
  - Lane position calculations
  
- **`animation.py`** - Time-based animation logic
  - Frame timing calculations
  - Note visibility windows
  - Velocity to color/brightness mapping
  
- **`midi_animation.py`** - MIDI to animation conversion
  - Convert DrumNote → MidiAnimationNote
  - Y position interpolation over time
  - Lane layout and spacing
  
- **`midi_video_core.py`** - Video rendering calculations
  - Strike effect calculations (scale, flash, brightness)
  - Note fade after strike line
  - MIDI note to rectangle conversion
  - UI element creation (strike line, lane markers)

### Imperative Shell (Side Effects)
**GPU operations, I/O, resource management.**

- **`shell.py`** - GPU rendering operations
  - ModernGL context management
  - Shader compilation and execution
  - Multi-pass rendering pipeline (scene → blur → composite)
  - Framebuffer operations
  - File I/O
  - **Tested with:** Level 1 & 2 integration tests (test_shell.py)
  
- **`midi_video_moderngl.py`** - High-level video rendering
  - MIDI file loading
  - FFmpeg process management
  - Frame-by-frame rendering loop
  - Progress reporting
  - **Tested with:** Level 1 & 2 integration tests (test_midi_video_moderngl.py)

## Data Flow

```
MIDI File
  ↓
parse_midi_file() [midi_shell.py]
  ↓
List[DrumNote]
  ↓
convert_drum_notes_to_animation() [midi_animation.py - PURE]
  ↓
List[MidiAnimationNote]
  ↓
For each frame:
  calculate_note_y_at_time() [midi_animation.py - PURE]
  midi_note_to_rectangle() [midi_video_core.py - PURE]
  ↓
  List[Rectangle Dict]
  ↓
  render_rectangles() [shell.py - GPU SIDE EFFECTS]
  read_framebuffer() [shell.py - GPU SIDE EFFECTS]
  ↓
  Video Frame (numpy array)
  ↓
FFmpeg encode [midi_video_moderngl.py - I/O]
  ↓
Output Video File
```

## Shader Pipeline (shell.py)

### Multi-Pass Rendering
1. **Scene Pass** - Render all rectangles with:
   - Rounded corners (fragment shader distance field)
   - Directional outlines (based on light position)
   - Animated sparkles (procedural, time-based)
   - Gradient and specular highlights
   
2. **Horizontal Blur Pass** - Separable Gaussian blur
   
3. **Vertical Blur Pass** - Complete the blur (creates glow)
   
4. **Composite Pass** - Blend glow with original scene

### Shader Features
- **Instanced rendering** - One draw call per layer
- **Rounded corners** - Distance field anti-aliasing
- **Glow effect** - Two-pass Gaussian blur + additive blend
- **Sparkles** - Procedural animation below strike line
- **Directional lighting** - Outlines brighten toward strike line

## Testing Strategy

### Functional Core (100% Unit Test Coverage)
All pure functions are fully unit tested:
- Deterministic outputs for given inputs
- No mocking required
- Fast execution (<0.1s)

### Imperative Shell (Integration Tests)
GPU operations tested through observable behavior:

**Level 1: Smoke Tests**
- Context creation/cleanup works
- Rendering produces valid output
- No crashes on edge cases

**Level 2: Property Tests**
- Color correctness (red objects → red pixels)
- Glow increases brightness
- Resolution independence
- Frame independence

**Level 3: Regression Tests**
- Pixel-perfect baseline comparisons
- Run manually before releases
- Marked `@pytest.mark.slow` and `@pytest.mark.regression`

**Shaders are not directly tested** - they are implementation details tested through observable outputs.

See [TESTING.md](./TESTING.md) for details.

## Coordinate Systems

### Normalized Coordinates (-1 to 1)
Used throughout functional core and GPU shaders.

- X: -1.0 (left edge) to +1.0 (right edge)
- Y: -1.0 (bottom) to +1.0 (top) - **OpenGL convention**

### Top-Left vs Bottom-Left
- **Functional core**: Uses top-left origin for intuitive note falling
- **GPU (OpenGL)**: Uses bottom-left origin
- **Conversion**: Done in `core.py` before GPU upload

```python
# Top-left (intuitive for falling notes)
y_top = 1.0   # Top of screen
y_bottom = -1.0  # Bottom of screen

# Bottom-left (OpenGL)
y_opengl = y_top - height  # Converted in core.py
```

## Adding New Features

### New Visual Effect (e.g., particle system)
1. **Functional core**: Write pure functions for calculations
   - Particle position/velocity updates
   - Lifetime calculations
   - Color interpolation
   
2. **Write tests**: Unit tests for pure functions

3. **Imperative shell**: Add shader and rendering code
   - Create particle vertex/fragment shaders
   - Add render pass in `shell.py`
   
4. **Integration tests**: Add Level 2 property tests
   - Verify particles appear in expected regions
   - Verify particle count is correct
   - Verify colors match specification

### New Note Effect (e.g., trail)
1. **Functional core** (`midi_video_core.py`): Add calculation functions
2. **Tests**: Unit test the calculations
3. **Shell integration** (`midi_video_moderngl.py`): Call new functions
4. **Verify**: Run existing tests (should still pass)

## Performance Characteristics

- **Rendering**: ~100-120 FPS @ 1080p (1.7-2x real-time)
- **Functional core**: Negligible overhead (<1ms per frame)
- **Bottleneck**: GPU operations (blur passes, shader execution)
- **Memory**: ~50MB GPU memory for 1080p framebuffers

## Dependencies

- **ModernGL**: OpenGL context and shader management
- **NumPy**: Array operations and data marshaling
- **FFmpeg**: Video encoding (external process)
- **Pillow**: Image I/O (save individual frames)

## File Naming Conventions

- `*_core.py` - Functional core (pure functions)
- `*_shell.py` - Imperative shell (side effects)
- `test_*.py` - Test files (match module names)
- `demo_*.py` - Demo/example scripts
