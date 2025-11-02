# GPU-Resident Architecture - Results Tracking

**Started**: November 2, 2025  
**Status**: In Progress

## Phase A: Persistent Buffer Architecture

### Tasks
- [x] Create `gpu_resident_shaders.py`: Time-animated vertex shaders
- [x] Create `gpu_resident_core.py`: Pre-compute all note instances
- [x] Create `gpu_resident_shell.py`: Persistent buffer management
- [x] Integrate with project_integration.py
- [x] Benchmark against naive implementation
- [x] Fix `.copy()` bug causing 3x slowdown
- [x] Identify real bottlenecks

### Metrics Tracking

**Naive Implementation** (Baseline):
- Test: Project 2, 54.40s video, 3,264 frames
- Pure rendering: 15.03s (217 fps)
- With FFmpeg: 26.75s (122 fps)
- Rendering: 56.2% of time, FFmpeg: 43.8%

**GPU-Resident** (Implemented):
- Pure rendering: 11.62s (281 fps) ← 1.29x faster
- With FFmpeg: 23.16s (141 fps) ← 1.16x faster overall
- Rendering: 50.2% of time, FFmpeg: 49.8%
- Per-frame breakdown:
  - GPU render: 0.030ms (33x faster than naive!)
  - Framebuffer readback: 3.6ms (hardware limited)
  - FFmpeg encode: ~3.5ms (CPU-bound)

**Analysis**:
- ✓ GPU rendering is 33x faster (0.030ms vs 1.0ms)
- ✗ Framebuffer readback dominates (3.6ms) - PCIe bandwidth limit
- ✗ FFmpeg encoding dominates overall (50% of time) - CPU H.264 compression
- Result: 29% speedup in rendering, 16% overall due to external bottlenecks

### Decision Log

#### 2025-11-02: Architecture Design
- **Decision**: Implement persistent buffer with time-based vertex shader animation
- **Rationale**: Current approach uploads geometry every frame, wasting bandwidth
- **Expected Impact**: 5-10x speedup by eliminating per-frame CPU→GPU transfers
- **Alternative Considered**: Keep current architecture, optimize Python loops
- **Why Rejected**: Would still have fundamental CPU→GPU bottleneck

#### 2025-11-02: Implementation Complete
- **Result**: GPU rendering IS 33x faster (0.030ms vs 1.0ms per frame)
- **Reality Check**: Bottlenecked by framebuffer readback (3.6ms) and FFmpeg (3.5ms)
- **Lesson Learned**: Optimizing one part of pipeline doesn't help if other parts dominate
- **Next Steps**: Need GPU-accelerated video encoding or eliminate readback

### Issues Encountered

#### Missing `.copy()` After Flip
- **Symptom**: 3x slowdown (83s vs 27s) with GPU-resident
- **Root Cause**: `np.flipud()` returns non-contiguous array view
- **Impact**: FFmpeg had to copy data, causing massive overhead
- **Fix**: Added `.copy()` to ensure contiguous memory
- **Result**: Performance improved to expected level (23s)

#### Attribute Mismatch in VAO
- **Symptom**: KeyError: 'in_lane' when creating vertex array
- **Root Cause**: Shader didn't have `in_lane` or `in_note_type` attributes
- **Fix**: Removed unused attributes from both shader and instance data structure
- **Lesson**: VAO attribute names must exactly match shader inputs

### Code Changes

**New Files Created**:
- `moderngl_renderer/gpu_resident_shaders.py` - Time-animated vertex shaders
- `moderngl_renderer/gpu_resident_core.py` - Pre-compute all note instances
- `moderngl_renderer/gpu_resident_shell.py` - Persistent buffer GPU context
- `moderngl_renderer/benchmark_gpu_resident.py` - Performance testing

**Modified Files**:
- `moderngl_renderer/project_integration.py` - Added `use_gpu_resident` parameter

**Key Implementation Details**:
- Instance data: 4 vec4 + 3 vec3 + 2 vec2 + 2 vec2 = 48 bytes per note
- Typical song: 1000 notes × 48 bytes = 48KB (trivial GPU memory)
- Upload happens ONCE at initialization
- Per-frame: only 4-byte time uniform update
- GPU shader handles visibility culling and position animation

## Phase B: Static Elements Optimization

### Tasks
- [ ] Add strike line to static buffer
- [ ] Add lane markers to static buffer  
- [ ] Add background lanes to static buffer
- [ ] Benchmark incremental improvement

### Metrics Tracking
(To be filled after Phase A completion)

## Phase C: Advanced Effects

### Tasks
- [ ] GPU-based motion blur
- [ ] GPU-based glow effects
- [ ] GPU-based highlight circles

### Metrics Tracking
(To be filled after Phase B completion)

## Overall Progress

- [x] Problem identified: CPU/GPU thrashing
- [x] Architecture designed: GPU-resident approach
- [ ] Phase A: Persistent buffers
- [ ] Phase B: Static elements
- [ ] Phase C: Advanced effects
- [ ] Final validation and benchmarks
