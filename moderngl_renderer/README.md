# ModernGL MIDI Renderer

GPU-accelerated MIDI video renderer using ModernGL. Provides significantly faster rendering compared to the legacy PIL/OpenCV renderer.

## Architecture

Follows the **functional core, imperative shell** pattern:

- **Core modules** (`*_core.py`): Pure functions for data transformations
- **Shell modules** (`*_shell.py`): GPU operations and side effects
- **Types**: Defined in `midi_types.py` (shared with project)

### Module Overview

- `core.py`: Rectangle/circle data transformations, coordinate conversion
- `animation.py`: Time-based animation calculations (velocity, fading, etc.)
- `midi_bridge_core.py`: MIDI→GPU data structure conversion
- `midi_bridge_shell.py`: Frame rendering orchestration
- `shell.py`: ModernGL context and GPU rendering primitives
- `ffmpeg_encoder.py`: Video encoding via FFmpeg
- `project_integration.py`: Integration with project manager

## Usage

### Command Line

ModernGL rendering is **enabled by default on macOS**. On other platforms, use the `--use-moderngl` flag:

```bash
# On macOS (default behavior)
python render_midi_to_video.py 1

# On Linux/Windows (enable ModernGL)
python render_midi_to_video.py 1 --use-moderngl

# Force legacy PIL renderer on any platform
python render_midi_to_video.py 1 --no-moderngl

# With custom settings
python render_midi_to_video.py 1 --fps 60 --fall-speed 1.5
```

### Web UI

Add `"use_moderngl": true` to the render-video API request:

```json
{
  "project_number": 1,
  "fps": 60,
  "width": 1920,
  "height": 1080,
  "use_moderngl": true
}
```

### Programmatic

```python
from project_manager import get_project_by_number, USER_FILES_DIR
from moderngl_renderer.project_integration import render_project_video_moderngl

# Get project
project = get_project_by_number(1, USER_FILES_DIR)

# Render with ModernGL
render_project_video_moderngl(
    project=project,
    width=1920,
    height=1080,
    fps=60,
    audio_source='original',
    fall_speed_multiplier=1.0
)
```

## Performance

The ModernGL renderer offers:

- **GPU acceleration**: All rendering on GPU via OpenGL
- **Streaming pipeline**: Memory-efficient frame generation
- **Instanced rendering**: Efficient batch processing

Typical performance: ~100-200 fps on Apple M1 Pro (1920x1080@60fps target).

## Testing

Run the test suite:

```bash
# All ModernGL tests
pytest moderngl_renderer/

# Specific test file
pytest moderngl_renderer/test_project_integration.py -v
```

Test coverage:
- 105 total tests
- Smoke tests (fast sanity checks)
- Property tests (behavior validation)
- Integration tests (end-to-end)

## Development

### Adding New Visual Effects

1. Add pure transformation function to `core.py` or `animation.py`
2. Add GPU rendering to `shell.py` if needed (shaders, buffers)
3. Update `midi_bridge_core.py` to generate new data structures
4. Update `midi_bridge_shell.py` to call new rendering
5. Write tests in `test_*.py` files

### Modifying Shaders

Shaders are defined as Python strings in `shell.py`:

- `VERTEX_SHADER` / `FRAGMENT_SHADER`: Rectangle rendering
- `CIRCLE_VERTEX_SHADER` / `CIRCLE_FRAGMENT_SHADER`: Circle rendering

Follow OpenGL 3.3 core profile syntax.

## Comparison with Legacy Renderer

| Feature | PIL/OpenCV | ModernGL |
|---------|-----------|----------|
| Speed | ~30 fps | ~100-200 fps |
| GPU Usage | Minimal | Full |
| Quality | Good | Excellent |
| Memory | High | Streaming |
| Anti-aliasing | Basic | MSAA + shader-based |

## Future Enhancements

- Motion blur effects (Phase 3b from plan)
- Visual quality comparison tool
- Performance benchmarking suite
- Additional visual effects (particles, etc.)
