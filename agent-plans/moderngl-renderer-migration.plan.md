# ModernGL Renderer Migration Plan

## Goal
Replace CPU-based PIL rendering with GPU-accelerated ModernGL for 100x+ performance improvement in video generation.

## Current State Analysis
- **Rendering Method**: PIL (Python Imaging Library) - CPU-based
- **Performance**: ~60 FPS video takes minutes to render
- **Bottleneck**: CPU drawing operations (rounded rectangles, alpha blending, anti-aliasing)
- **Current File**: `render_midi_to_video.py` using PIL ImageDraw
- **Layer System**: Multiple RGBA layers composited together

## Target State
- **Rendering Method**: ModernGL - GPU-accelerated OpenGL
- **Performance**: Render same video in seconds
- **Approach**: Offscreen framebuffer rendering, direct video frame export
- **Shaders**: GLSL vertex/fragment shaders for effects

## Phases

### Phase 1: Setup & Infrastructure (POC)
**Goal**: Render a single static frame with ModernGL to validate approach

**Tasks**:
1. Add ModernGL dependency to environment.yml
2. Create OpenGL context (headless/offscreen)
3. Create framebuffer matching video dimensions (1920x1080)
4. Implement basic shader (vertex + fragment)
5. Render simple geometry (single note rectangle)
6. Export frame to NumPy array → image file
7. Validate no window/display required (headless rendering)

**Success Criteria**:
- ModernGL context initializes successfully on macOS
- Single frame renders with solid color rectangle
- Frame exports to valid PNG/JPEG format
- No window/display required (headless)
- Code runs in Docker container

**Risks**:
- OpenGL context creation on macOS (may need EGL or specific backend)
- Docker container may need additional OpenGL dependencies
- Framebuffer format compatibility with video encoder

**Estimated Complexity**: Low
**Estimated Time**: 1-2 hours

---

### Phase 2: Core Geometry Rendering
**Goal**: Render all note types with correct positions and colors

**Tasks**:
1. Implement rounded rectangle shader with anti-aliasing
2. Batch render multiple notes in single draw call
3. Implement velocity-based brightness calculation
4. Add alpha transparency support for layering
5. Render kick drum bars (wider rectangles)
6. Render strike line and lane markers
7. Implement camera/viewport transformations

**Success Criteria**:
- Notes render at correct positions matching PIL version
- Colors and brightness match original implementation
- Alpha blending works correctly for overlapping notes
- Performance improvement visible (5-10x minimum)
- All 4 drum lanes (hihat, snare, kick, toms) render correctly

**Risks**:
- Shader complexity for rounded corners with good anti-aliasing
- Batching efficiency with varying colors/positions
- Coordinate system differences between PIL and OpenGL

**Estimated Complexity**: Medium
**Estimated Time**: 3-4 hours

---

### Phase 3: Effects & Polish
**Goal**: Add motion blur, glow, highlights matching original quality

**Tasks**:
1. Implement motion blur via shader or multi-pass rendering
2. Add glow effect for strike highlights
3. Implement smooth pulsing animations for active notes
4. Add UI elements (progress bar, legend, FPS counter)
5. Optimize shader performance (minimize draw calls)
6. Add configurable quality settings

**Success Criteria**:
- Visual quality matches or exceeds PIL version
- All effects render correctly and smoothly
- Performance 50x+ faster than original
- Effects configurable via config.yaml

**Risks**:
- Shader complexity for advanced effects may reduce performance
- Multi-pass rendering overhead
- Motion blur quality vs performance tradeoff

**Estimated Complexity**: High
**Estimated Time**: 4-6 hours

---

### Phase 4: Integration & Testing
**Goal**: Full integration with existing pipeline, validation

**Tasks**:
1. Replace PIL rendering pipeline completely in render_midi_to_video.py
2. Ensure FFmpeg integration works with new frame format
3. Test with various MIDI files (simple, complex, edge cases)
4. Benchmark performance improvements
5. Add fallback to PIL if ModernGL unavailable (--use-pil flag)
6. Update documentation (MIDI_VISUALIZATION_GUIDE.md)
7. Add tests for rendering pipeline

**Success Criteria**:
- All test MIDI files render correctly
- Video output quality validated (no visual regressions)
- Performance metrics documented (100x+ improvement target)
- No regressions in functionality
- Docker container works with ModernGL
- Tests pass in CI/CD

**Risks**:
- Edge cases in MIDI parsing/timing
- Color/brightness differences requiring calibration
- Platform-specific OpenGL issues
- FFmpeg compatibility with new frame format

**Estimated Complexity**: Medium
**Estimated Time**: 2-3 hours

---

## Architecture Changes

### Before (PIL):
```
MIDI Parse → Note Calculations → PIL Drawing (CPU) → FFmpeg → Video
                                       ↓
                                  Very Slow (minutes)
                                  ~30-60 FPS render speed
```

### After (ModernGL):
```
MIDI Parse → Note Calculations → GPU Shaders → Framebuffer → FFmpeg → Video
                                       ↓
                                  Very Fast (seconds)
                                  1000+ FPS render speed
```

### Key Components:

1. **Shader System**:
   - Vertex shader: Position/transform geometry
   - Fragment shader: Colors, anti-aliasing, effects
   - Uniform buffers: Pass configuration data
   - Instanced rendering: Draw many notes efficiently

2. **Geometry Batching**:
   - Upload all visible notes as vertex buffer
   - Single draw call per frame per geometry type
   - Minimize state changes

3. **Framebuffer Management**:
   - Offscreen rendering (no window required)
   - Direct pixel readback to NumPy array
   - Compatible with FFmpeg stdin input
   - Double buffering for smooth operation

## Dependencies
- `moderngl` - Core OpenGL bindings for Python
- `moderngl-window` (optional) - Context creation helpers
- Existing: `numpy`, `mido`, `opencv-python`, `ffmpeg-python`

## File Structure
```
/Users/jasoncopp/Source/GitHub/larsnet/
├── render_midi_to_video.py (modified - new ModernGL backend)
├── moderngl_renderer.py (new - core rendering logic)
├── shaders/
│   ├── note_vertex.glsl (new - vertex shader)
│   ├── note_fragment.glsl (new - fragment shader with rounded corners)
│   ├── glow_fragment.glsl (new - post-process glow effect)
│   └── blur_fragment.glsl (new - motion blur effect)
└── config.yaml (modified - add rendering backend options)
```

## Rollback Plan
- Keep PIL code path as fallback (`--renderer=pil` flag)
- Document differences in rendering behavior
- Validate output with test suite before full migration
- Feature flag in config.yaml to switch renderers
- Git branch allows easy rollback if issues found

## Success Metrics
- **Performance**: 100x+ faster than PIL (target: <10s for 3-minute song @ 60 FPS)
- **Quality**: Visual output matches or exceeds original
- **Reliability**: Handles all existing MIDI files without errors
- **Maintainability**: Shader code documented and understandable
- **Platform Support**: Works on macOS (native + Docker), Linux (Docker)

## Testing Strategy
1. Visual regression tests (compare PIL vs ModernGL output)
2. Performance benchmarks (render time comparison)
3. Edge case MIDI files (empty, very dense, timing edge cases)
4. Memory usage monitoring (GPU vs CPU memory)
5. Cross-platform testing (macOS, Docker Linux)
