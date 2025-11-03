# ModernGL MIDI Renderer Integration Plan

**Date**: November 2, 2025  
**Objective**: Create a working ModernGL-based renderer that integrates with the existing MIDI video pipeline, using the proven architecture from `demo_animation.py`.

## Lessons from Failed GPU-Resident Approach

### What Went Wrong
- Attempted to build "GPU-resident" architecture with pixel-space calculations
- Mixed coordinate systems (pixel space in Python, OpenGL NDC in shaders)
- Over-engineered coordinate conversions caused unfixable bugs
- Notes appeared at wrong positions, moved at half speed, only covered half screen
- 10+ fix attempts, all failed - every change either broke things worse or had no effect

### What Actually Works
- `moderngl_renderer/demo_animation.py` - Renders successfully at 193 FPS (4.8x speedup)
- `moderngl_renderer/animation.py` - Pure functional core with correct coordinate math
- `moderngl_renderer/shell.py` - Simple imperative shell using normalized coords directly
- **Key insight**: Use OpenGL normalized coordinates (-1 to +1) throughout, no pixel conversions

## Architecture Decision

**Use the working `animation.py` + `shell.py` approach, NOT the broken gpu_resident_*.py code.**

The working demo was RIGHT THERE the whole time. We should have adapted it instead of rewriting from scratch.

## Current State Analysis

### What Works ✓
- `demo_animation.py` successfully renders animated notes with timing
- Normalized OpenGL coordinates used consistently throughout
- No complex coordinate space conversions
- Clean functional core / imperative shell separation
- Proven 4.8x speedup over PIL baseline

### What's Broken ✗
- `gpu_resident_core.py`, `gpu_resident_shaders.py`, `gpu_resident_shell.py`
- Coordinate system bugs from pixel↔normalized conversions
- Time-animated shaders never worked correctly
- Over-engineered architecture

### Key Principle
**Keep everything in normalized OpenGL coordinates from start to finish.**  
Don't try to be clever with pixel-space calculations - that's what killed the GPU-resident approach.

## Success Criteria

1. **Functional Parity**: ModernGL renderer produces visually identical output to PIL renderer
2. **Performance**: Achieves 3-5x speedup over PIL (demo already proves this is achievable)
3. **No Coordinate Bugs**: Notes appear at correct positions, move at correct speed, cover full screen
4. **Audio Sync**: Perfect synchronization with audio track
5. **Clean Architecture**: Maintains functional core/imperative shell separation

## Risks & Mitigation

### High Risk: Reintroducing Coordinate Bugs
- **Cause**: Mixing pixel and normalized coordinate systems
- **Mitigation**: Work in normalized coords exclusively, follow demo_animation.py pattern exactly
- **Validation**: Compare output frame-by-frame with PIL renderer

### Medium Risk: Over-Engineering
- **Cause**: Attempting optimizations before basic functionality works
- **Mitigation**: Get it working first, optimize later (Phase 4)
- **Rule**: Any optimization must not break coordinate system
- **Strategy**: Use regression test approach from `how-to-perform-testing.instructions.md`

### Medium Risk: Feature Complexity
- **Issue**: Motion blur, highlight circles, kick drum bars are complex to implement in shaders
- **Mitigation**: Implement incrementally, validate each effect independently
- **Strategy**: Start with basic rectangles, add effects one at a time

### Low Risk: File Organization Mess
- **Issue**: User specifically warned against putting debug/proof-of-concept files in moderngl_renderer/
- **Mitigation**: Keep all work inside moderngl_renderer/, no temporary files
- **Strategy**: Follow existing pattern of core.py, shell.py, animation.py structure

## Architecture Design

### Module Structure (within moderngl_renderer/)

```
moderngl_renderer/
├── core.py              [EXTEND] - Add MIDI-specific pure functions
├── shell.py             [EXTEND] - Add shader-based effects
├── animation.py         [EXTEND] - Add MIDI note visibility logic
├── midi_core.py         [NEW] - Pure MIDI parsing functions
├── midi_effects.py      [NEW] - Effect calculations (blur, highlights)
├── midi_renderer.py     [NEW] - Main orchestration (replaces MidiVideoRenderer class)
└── demo_midi.py         [NEW] - Demo script for testing
```

### Extracted Common Functions (from render_midi_to_video.py)

These should go into new core modules:

1. **midi_core.py** (Pure Functions):
   - `parse_midi_file()` - MIDI file parsing with tempo map
   - `build_tempo_map()` - Global tempo map construction
   - `map_midi_to_lanes()` - Drum map and lane assignment
   - `filter_unused_lanes()` - Lane optimization
   - `calculate_note_alpha()` - Existing pure function
   - `calculate_brightness()` - Existing pure function
   - `apply_brightness_to_color()` - Already in moderngl core.py

2. **midi_effects.py** (Pure Functions):
   - `calculate_motion_blur_layers()` - Compute blur offsets and alphas
   - `calculate_highlight_pulse()` - Pulse animation math
   - `calculate_kick_bar_dimensions()` - Screen-wide bar sizing
   - `get_brighter_outline_color()` - Existing pure function

3. **midi_renderer.py** (Imperative Shell):
   - Orchestrates MIDI parsing, frame generation, GPU rendering
   - Interfaces with project manager
   - Handles FFmpeg video encoding with audio sync
   - Replaces `MidiVideoRenderer` class with functional approach

## Implementation Phases

### Phase 1: Adapt animation.py for MIDI Data
**Goal**: Make the working animation system accept DrumNote input  
**Duration**: 2-4 hours  
**Risk**: Low - extending working code

**Tasks**:
1. Create `midi_animation.py` bridge module
   - Convert `List[DrumNote]` → animation-compatible note format
   - Map MIDI lanes to normalized X positions (-1 to +1 range)
   - Calculate note colors from MIDI drum mapping data
   - Handle kick drum (lane -1) as full-width bar

2. Add strike line and visual elements to shell.py
   - Render strike line at y = -0.6 (85% down in normalized coords)
   - Add vertical lane markers
   - Add background lane coloring

3. Test with simple MIDI file
   - Use project 13 (srdrums) which has 63 notes, 14s duration
   - Verify notes appear at correct positions
   - Verify notes fall at correct speed
   - Compare with PIL renderer output frame-by-frame

**Validation**:
- [ ] Notes render at correct X positions for each lane
- [ ] Notes appear at top of screen and fall to strike line
- [ ] Strike line visible at 85% down (y = -0.6 normalized)
- [ ] Output visually matches PIL renderer
- [ ] No coordinate system bugs

**Coordinate Conversion Reference**:
```python
# If you must convert from existing PIL pixel-based code:
def pixel_to_normalized_y(pixel_y, height):
    """Convert PIL pixel Y (0=top) to OpenGL normalized (-1=bottom, +1=top)"""
    normalized_progress = pixel_y / height  # 0.0 to 1.0
    screen_height_norm = 2.0  # Range from -1 to +1
    return 1.0 - (normalized_progress * screen_height_norm)

# Strike line example:
# PIL: y_pixels = 918 (at 85% down)
# OpenGL: y_norm = 1.0 - (918/1080) * 2.0 = -0.7
```

**But better**: Work in normalized coordinates from the start, avoid pixel conversions entirely.

### Phase 2: Integrate with render_midi_to_video.py
**Goal**: Make `--use-moderngl` flag use the working animation approach  
**Duration**: 2-3 hours  
**Risk**: Low - integrating tested components

**Tasks**:
1. Create `render_midi_moderngl()` function
   - Accept same parameters as PIL renderer (width, height, fps, config, etc.)
   - Use `animation.py` + `shell.py` under the hood
   - Stream frames directly to FFmpeg encoder

2. Handle audio synchronization
   - Ensure frame timing matches audio exactly
   - No lookahead time offset - start at t=0 like PIL renderer
   - Verify sync doesn't drift over long videos

3. Add progress reporting
   - Match PIL renderer's progress output format
   - Show FPS, frame count, estimated time remaining
   - Don't spam console - update every second

**Validation**:
- [ ] `python render_midi_to_video.py 13 --use-moderngl` produces correct output
- [ ] Video matches PIL renderer output visually (frame-by-frame comparison)
- [ ] Audio stays synchronized throughout entire video
- [ ] Achieves 3-5x speedup over PIL renderer
- [ ] Progress output is clear and helpful

### Phase 3: Add Missing Visual Elements
**Goal**: Match all features of PIL renderer  
**Duration**: 3-4 hours  
**Risk**: Medium - shader complexity

**Tasks**:
1. Legend layer
   - Show instrument names with colors
   - Position in corner like PIL version
   - Render as texture overlay

2. Progress bar / time display
   - Current time and total duration
   - Progress percentage bar
   - Text rendering via texture

3. Highlight circles at strike line
   - Glow effect when notes hit strike line
   - Fade out animation over ~200ms
   - Layer multiple circles with alpha for glow

**Validation**:
- [ ] Feature parity with PIL renderer - all visual elements present
- [ ] Text is readable and properly positioned
- [ ] Highlights appear at correct timing
- [ ] Still maintains 3-5x performance advantage

### Phase 4: Optimization (Future - Optional)
**Goal**: Further improve performance without breaking correctness  
**Duration**: TBD  
**Risk**: HIGH - coordinate bugs lurk here

**ONLY attempt Phase 4 after Phases 1-3 are stable and working!**

Possible optimizations:
- Batch upload static elements once (strike line, lanes, legend)
- GPU visibility culling in vertex shader
- Persistent note buffer with instanced rendering
- Shader-based motion blur (vs multi-pass rendering)

**CRITICAL RULE**: Any optimization must not reintroduce coordinate system bugs.

**Testing Protocol**:
1. Run full test suite before and after optimization
2. Compare output frame-by-frame - must be pixel-identical
3. If ANY coordinate bugs appear, REVERT immediately
4. Document performance gains vs risk

**Validation**:
- [ ] Output is pixel-identical to pre-optimization version
- [ ] Performance improvement is measurable (>10% speedup)
- [ ] No coordinate system bugs
- [ ] All tests still pass
**Goal**: Make ModernGL renderer the default  
**Duration**: 1 phase  
**Risk**: Low - already validated

## Implementation Guidelines

### Coordinate System Rules (CRITICAL)
1. **Work in normalized OpenGL coords everywhere** (-1 to +1)
2. **Never convert to pixel space and back** - this was the source of all bugs in gpu_resident_*.py
3. **Y-axis convention: +1.0 = top, -1.0 = bottom** - stick to OpenGL NDC convention
4. **Framebuffer flip is correct** - keep `np.flipud()` in read_framebuffer()
5. **When in doubt, check demo_animation.py** - it's the working reference

### Testing Strategy

Follow the 3-tier testing approach from `how-to-perform-testing.instructions.md`:

**Level 1: Smoke Tests** (~0.3s)
- Rendering doesn't crash
- Output has correct dimensions (1920x1080)
- Basic operations complete without errors

**Level 2: Property Tests** (~0.5s)
- Notes appear in correct lane positions
- Notes move from top to bottom (not backwards)
- Notes cover full screen height (not just 50%)
- Colors match MIDI drum mapping
- Strike line at 85% down

**Level 3: Regression Tests** (~2-5s, marked `@pytest.mark.slow @pytest.mark.regression`)
- Pixel-perfect baseline comparisons
- Run manually or pre-release only
- Update baselines when intentional visual changes made

**Coverage Target**: Level 2 tests alone should provide 85-90% coverage of GPU shell code.

### Before Starting Each Session
1. Run `python -m moderngl_renderer.demo_animation` and verify it works
2. Check output at `moderngl_renderer/test_artifacts/animation_demo.mp4`
3. Review coordinate system rules above
4. Remember: **Simple is better than clever**

### File Organization
- Keep all work inside `moderngl_renderer/` directory
- Follow existing pattern: `core.py`, `shell.py`, `animation.py`
- No temporary or debug files in project root
- Test files: `test_*.py` in same directory as code under test

## Dependencies

### Already Available
- `moderngl` - GPU rendering library
- `numpy` - Array operations
- `mido` - MIDI file parsing (used by existing render_midi_to_video.py)
- `ffmpeg` - Video encoding

### No New Dependencies Required
This plan adds zero new dependencies.

## Success Metrics

### Must Have (Phase 2 Complete)
- ModernGL renderer produces visually identical output to PIL renderer
- Audio synchronization is perfect (no drift)
- No coordinate system bugs (notes at correct positions, correct speed, full screen height)
- 3x+ performance improvement over PIL

### Nice to Have (Phase 3 Complete)
- All visual elements present (legend, progress bar, highlights)
- 5x+ performance improvement
- Users prefer ModernGL output quality

### Stretch Goal (Phase 4 - Optional)
- 10x+ performance improvement
- Real-time preview capability (>60 FPS for 1080p)
- GPU-resident architecture working correctly (without coordinate bugs)

## Timeline Estimate

- **Phase 1**: 2-4 hours (adapt existing working code for MIDI data)
- **Phase 2**: 2-3 hours (integration with main pipeline)
- **Phase 3**: 3-4 hours (add visual elements)
- **Phase 4**: TBD (optimization is optional, only if needed)

**Total for working renderer: 7-11 hours of focused work**

## Expected File Changes

### New Files
- `moderngl_renderer/midi_animation.py` (~150 lines) - Bridge MIDI → animation format
- `moderngl_renderer/midi_renderer.py` (~200 lines) - Main entry point
- `moderngl_renderer/test_midi_animation.py` (~100 lines) - Tests

### Modified Files  
- `moderngl_renderer/shell.py` (+50 lines) - Add strike line, lane markers
- `moderngl_renderer/animation.py` (+30 lines) - Support DrumNote format
- `render_midi_to_video.py` (+20 lines) - Add `--use-moderngl` flag

### Deprecated (Do Not Use)
- `moderngl_renderer/gpu_resident_core.py` - Broken coordinate system
- `moderngl_renderer/gpu_resident_shaders.py` - Over-engineered
- `moderngl_renderer/gpu_resident_shell.py` - Never worked correctly

Add warning comments to gpu_resident_*.py files: "DO NOT USE - coordinate system bugs, use shell.py + animation.py instead"

## Commit Strategy

Phase-based commits with descriptive summaries:

```
Phase 1: refactor(moderngl): adapt animation.py for MIDI DrumNote input - strike line, lane mapping
Phase 2: feat(moderngl): integrate MIDI renderer with render_midi_to_video.py pipeline  
Phase 3: feat(moderngl): add legend, progress bar, highlight effects
Phase 4: perf(moderngl): optimize rendering performance (only if needed)
```

Each commit includes:
- Metrics: tests passing, FPS achieved, coverage percentage
- Brief summary of what works now

## Next Steps

1. **Read this plan thoroughly** - understand the architecture decision
2. **Run the demo**: `python -m moderngl_renderer.demo_animation`
   - Watch the video output at `moderngl_renderer/test_artifacts/animation_demo.mp4`
   - Verify demo still works (proves architecture is sound)
3. **Study the working code**:
   - Read `moderngl_renderer/animation.py` - understand coordinate math
   - Read `moderngl_renderer/shell.py` - understand GPU rendering approach
   - Read `moderngl_renderer/demo_animation.py` - see how they connect
4. **Start Phase 1**: Create `midi_animation.py` bridge module
   - Convert DrumNote → animation format
   - Map MIDI lanes to normalized X positions
   - Test with project 13 (simple 63-note file)
5. **Test constantly** - verify each piece works before moving on

## Key Takeaways from Failed Approach

1. **The working demo was RIGHT THERE** - demo_animation.py had the correct architecture all along
2. **Don't over-engineer** - pixel-space abstractions introduced unfixable bugs
3. **Coordinate conversions are deadly** - stick to one coordinate system (normalized OpenGL)
4. **Simple beats clever** - shell.py + animation.py is simple and works
5. **Test the basics first** - smoke tests would have caught the coordinate bugs immediately

## Remember

> "The GPU-resident approach failed because we tried to be clever with coordinate conversions. The demo_animation.py approach succeeds because it's straightforward: normalized coordinates everywhere, no fancy optimizations, just clean functional code. Use what works."

## References

- Existing instructions: `general.instructions.md`, `how-to-perform-testing.instructions.md`
- Current renderer: `render_midi_to_video.py`
- ModernGL demo: `moderngl_renderer/demo_animation.py`
- Test suite: `test_cv2_rendering.py`
- Animation system: `moderngl_renderer/animation.py`
