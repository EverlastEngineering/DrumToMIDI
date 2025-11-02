# GPU-Resident ModernGL Architecture Plan

**Date**: November 2, 2025  
**Objective**: Redesign ModernGL renderer to keep all geometry on GPU, eliminating per-frame CPU→GPU uploads for 10x+ performance improvement.

## Problem Analysis

### Current Architecture (Naive Approach)
```
For each frame (3,264 times for 54s video):
  1. CPU: build_frame_from_drum_notes() - convert notes to rectangles
  2. CPU: Filter visible notes based on time window
  3. CPU→GPU: Upload ~10-50 rectangle instances
  4. GPU: Render rectangles with instancing
  5. GPU→CPU: Read framebuffer (2MB transfer)
  6. CPU: Send to FFmpeg
```

**Problems**:
- Rebuilds same geometry 3,264 times (notes don't change!)
- CPU→GPU upload bandwidth wasted
- Python loop overhead per note per frame
- GPU sits idle during CPU processing

**Result**: Only 2.17x speedup (121 fps vs 56 fps)

### Target Architecture (GPU-Resident)
```
At initialization (once):
  1. CPU: Pre-compute ALL note geometry for entire song
  2. CPU→GPU: Upload complete note buffer (one-time cost)
  3. GPU: Store in persistent buffer

For each frame:
  1. CPU: Update time uniform only (4 bytes)
  2. GPU: Vertex shader culls invisible notes
  3. GPU: Vertex shader animates note positions
  4. GPU: Fragment shader handles fade/glow
  5. GPU→CPU: Read framebuffer (unavoidable for FFmpeg)
```

**Benefits**:
- Zero per-frame geometry uploads
- GPU does visibility culling (parallel)
- GPU does position animation (parallel)
- Minimal CPU involvement

**Expected Result**: 10-15x speedup (500-800 fps rendering)

## Technical Design

### Phase 1: Static Geometry Buffer

**Goal**: Upload all notes once, render entire song from GPU memory.

#### Data Structure

```glsl
// Per-note instance data (uploaded once)
struct NoteInstance {
    vec4 base_position;    // x, y, width, height in normalized coords
    vec4 color;            // r, g, b, brightness
    vec2 timing;           // start_time, end_time
    float lane;            // lane index
    float note_type;       // 0=regular, 1=kick
};
```

#### Vertex Shader (New)

```glsl
#version 330 core

// Per-vertex attributes (quad corners)
in vec2 in_position;

// Per-instance attributes (each note)
in vec4 base_position;
in vec4 color;
in vec2 timing;
in float lane;
in float note_type;

// Uniforms (updated per frame)
uniform float u_current_time;
uniform float u_pixels_per_second;
uniform float u_strike_line_y;
uniform vec2 u_screen_size;

// Outputs
out vec4 v_color;
out float v_alpha;

void main() {
    float start_time = timing.x;
    float time_delta = u_current_time - start_time;
    
    // Calculate vertical position based on time
    float pixel_offset = time_delta * u_pixels_per_second;
    float y_pixel = u_strike_line_y - pixel_offset;
    
    // Convert to normalized coords
    float y_norm = (y_pixel / u_screen_size.y) * 2.0 - 1.0;
    
    // Visibility culling on GPU
    if (y_norm < -1.2 || y_norm > 1.2) {
        // Move off-screen (GPU will discard)
        gl_Position = vec4(2.0, 2.0, 0.0, 1.0);
        v_alpha = 0.0;
        return;
    }
    
    // Calculate position
    vec2 pos = base_position.xy;
    pos.y = y_norm;
    
    // Apply corner offset from in_position
    vec2 size = base_position.zw;
    pos += in_position * size;
    
    gl_Position = vec4(pos, 0.0, 1.0);
    
    // Calculate alpha fade
    float distance_from_strike = abs(y_pixel - u_strike_line_y);
    v_alpha = 1.0 - smoothstep(0.0, u_screen_size.y * 0.3, distance_from_strike);
    
    v_color = color;
}
```

#### Implementation Steps

1. **Modify midi_bridge_core.py**:
   - `precompute_all_note_instances()` - Convert all notes to GPU format once
   - Returns numpy array of NoteInstance structs

2. **Modify shell.py**:
   - Add `upload_persistent_buffer()` - Create GPU buffer, upload once
   - Add `set_time_uniform()` - Update only time per frame
   - Modify vertex shader to animate positions

3. **Modify midi_bridge_shell.py**:
   - `render_midi_to_frames()` initialization uploads buffer once
   - Per-frame loop only updates time uniform

### Phase 2: GPU Visibility Culling

**Goal**: Let GPU decide which notes to draw, remove CPU filtering.

#### Current CPU Code (Remove)
```python
# This loops every frame in Python - SLOW
visible_notes = []
for note in notes:
    time_until_hit = note.time - current_time
    if -config.passthrough_time <= time_until_hit <= config.lookahead_time:
        visible_notes.append(note)
```

#### New GPU Shader Code (Fast)
```glsl
// Vertex shader decides visibility
void main() {
    float time_delta = u_current_time - start_time;
    
    // GPU culling - happens in parallel for all notes
    if (time_delta < -u_lookahead_time || time_delta > u_passthrough_time) {
        gl_Position = vec4(2.0, 2.0, 0.0, 1.0);  // Off-screen
        return;
    }
    
    // Continue with visible note rendering...
}
```

### Phase 3: Static Elements Buffer

**Goal**: Strike line, lane markers, background lanes uploaded once.

#### Data Structure
```python
# Static UI elements - uploaded once at initialization
static_elements = {
    'strike_line': Rectangle(x=-1.0, y=strike_y, w=2.0, h=0.01, color=white),
    'lane_markers': [Circle(...) for each lane],
    'background_lanes': [Line(...) for each lane]
}
```

#### Rendering
```python
def render_frame(ctx, time):
    # Draw static elements (from GPU buffer)
    ctx.render_static_buffer()
    
    # Draw animated notes (from GPU buffer with time uniform)
    ctx.set_uniform('u_current_time', time)
    ctx.render_notes_buffer()
    
    # Read framebuffer
    return read_framebuffer(ctx)
```

## Performance Expectations

### Benchmark Breakdown

**Current (Naive)**:
- 3,264 frames in 27 seconds = 121 fps average
- Per frame: ~8ms total
  - ~4ms CPU processing (build geometry, filter notes)
  - ~2ms GPU rendering
  - ~2ms framebuffer readback

**Target (GPU-Resident)**:
- Per frame budget: ~1.2ms total
  - ~0.1ms CPU (update time uniform)
  - ~0.5ms GPU rendering
  - ~0.6ms framebuffer readback (unavoidable)
  
- Expected: 800+ fps rendering throughput
- For 54s video: ~4-5 seconds total time
- **Speedup**: 5-6x over naive, 12x over PIL

### Bottleneck Analysis

After GPU-resident optimization, bottleneck becomes:
1. **Framebuffer readback** (2MB per frame, 60 times/second)
2. **FFmpeg encoding** (H.264 compression)

These are unavoidable - we need CPU frames for video encoding.

## Implementation Phases

### Phase A: Persistent Buffer Architecture (This Work)
- [ ] Modify `midi_bridge_core.py`: Add `precompute_all_instances()`
- [ ] Modify `shell.py`: Add persistent buffer support
- [ ] Modify vertex shader: Time-based animation
- [ ] Modify `midi_bridge_shell.py`: Upload once, render many
- [ ] Test: Validate output identical to current
- [ ] Benchmark: Measure speedup

**Success Metrics**:
- Zero geometry uploads after initialization
- 5-10x speedup over current implementation
- Pixel-perfect match to current output

### Phase B: Static Elements Optimization
- [ ] Add strike line to static buffer
- [ ] Add lane markers to static buffer
- [ ] Add background lanes to static buffer
- [ ] Render static buffer once per frame
- [ ] Benchmark: Measure additional speedup

### Phase C: Advanced Effects
- [ ] GPU-based motion blur (shader)
- [ ] GPU-based glow effects (compute shader?)
- [ ] GPU-based highlight circles
- [ ] All animation math in shaders

## Validation Strategy

### Performance Testing
```bash
# Benchmark current (naive)
time python render_midi_to_video.py 2 --use-moderngl --no-audio

# Benchmark after Phase A
time python render_midi_to_video.py 2 --use-moderngl --no-audio

# Compare frame times
# Current: ~8ms per frame
# Target: ~1.2ms per frame
```

### Visual Testing
```python
# Render same frame with both implementations
naive_frame = render_frame_naive(notes, time=10.0)
optimized_frame = render_frame_optimized(notes, time=10.0)

# Allow small differences from floating point
diff = np.abs(naive_frame - optimized_frame).max()
assert diff < 5, f"Visual difference too large: {diff}"
```

### Regression Testing
- All existing ModernGL tests must pass
- Visual quality comparison with PIL renderer
- Validate note positions at key timestamps

## Technical Constraints

### Memory Considerations
- Typical song: 1,000 notes × 48 bytes = 48KB (trivial)
- Long song: 10,000 notes × 48 bytes = 480KB (still trivial)
- GPU memory is not a concern for MIDI data

### OpenGL Limitations
- Maximum instances per draw call: typically millions (no issue)
- Vertex shader complexity: minimal (position + fade)
- Fragment shader complexity: minimal (color + rounded corners)

### FFmpeg Integration
- Must maintain CPU-side framebuffer reads
- Cannot optimize away the readback
- This is the ultimate bottleneck (hardware limited)

## Success Criteria

1. **Performance**: 800+ fps rendering (10x+ improvement)
2. **Visual Fidelity**: Pixel-perfect match to current output
3. **Architecture**: Zero per-frame geometry uploads
4. **Tests**: All existing tests pass
5. **Benchmarks**: Documented performance improvements

## Risks

### High Risk: Shader Complexity
- **Issue**: Time-based animation in shader might have precision issues
- **Mitigation**: Use high-precision floats, test at extreme durations
- **Fallback**: Keep CPU-side position calculation if needed

### Medium Risk: Visual Differences
- **Issue**: GPU math might differ slightly from CPU
- **Mitigation**: Extensive visual comparison tests
- **Acceptance**: Small differences (<5 pixel intensity) acceptable

### Low Risk: Buffer Upload Overhead
- **Issue**: Initial upload might be slow for long songs
- **Mitigation**: This is one-time cost, amortized over thousands of frames
- **Measurement**: Even 100ms upload is negligible for 54s video

## Next Steps

1. Read general.instructions.md for architecture patterns ✓
2. Create Phase A plan file: `gpu-resident-architecture.plan.md` ✓
3. Create Phase A results file: `gpu-resident-architecture.results.md`
4. Begin implementation of persistent buffer architecture
5. Validate with benchmarks and visual comparison
6. Commit after each sub-phase completion
