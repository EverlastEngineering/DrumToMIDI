# ModernGL MIDI Renderer Migration Plan

**Date**: November 2, 2025  
**Objective**: Migrate MIDI video rendering from PIL/OpenCV hybrid approach to pure ModernGL GPU rendering, eliminating PIL dependency entirely.

## Current State

### demo_animation.py (Inspiration)
- GPU-accelerated rendering via ModernGL
- Follows functional core/imperative shell pattern
- Uses test note data (hardcoded drum pattern)
- Renders to numpy array frames, then saves to video via FFmpeg
- Clean separation: `core.py` (pure functions), `shell.py` (GPU ops), `animation.py` (timing math)
- Already has animation system with note visibility windows and frame scene building

### render_midi_to_video.py (Current Production)
- 1,324 lines - monolithic file structure
- Uses PIL for drawing with rounded rectangles and alpha blending
- OpenCV for canvas operations and video encoding
- Full MIDI parsing with tempo map support
- Complex lane management and note rendering logic
- Supports kick drum (screen-wide bars) and regular note lanes
- Has motion blur, highlight circles, fade effects
- Includes project management integration
- **Critical**: Has tests via `test_cv2_rendering.py` that must not break

### Key Functional Differences
1. **MIDI Parsing**: `render_midi_to_video.py` has sophisticated tempo map parsing - `demo_animation.py` uses simple test notes
2. **Lane Management**: Production code has complex drum mapping, lane filtering, kick drum special handling
3. **Visual Effects**: Production has motion blur, highlight pulses, velocity-based brightness, alpha fading
4. **Output Integration**: Production integrates with project manager, audio sync, FFmpeg with audio tracks

## Success Criteria

1. **Functional Parity**: New ModernGL renderer produces visually identical output to current PIL/OpenCV renderer
2. **Performance**: Achieves >100 FPS rendering (vs current ~40 FPS with PIL)
3. **No Breaking Changes**: All existing tests pass without modification
4. **Clean Architecture**: Maintains functional core/imperative shell separation
5. **No PIL Dependency**: Zero PIL imports in rendering pipeline

## Risks & Mitigation

### High Risk: Breaking Existing Tests
- **Mitigation**: Extract and test each component independently before integration
- **Strategy**: Create new modules alongside existing code, run parallel testing
- **Validation**: Use `test_cv2_rendering.py` as regression test suite

### Medium Risk: Visual Fidelity Differences
- **Issue**: GPU rendering may have subtle differences in anti-aliasing, alpha blending
- **Mitigation**: Create baseline comparison tests with tolerance thresholds
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

### Phase 0: Establish Data Contract (COMPLETED ✓)
**Goal**: Define shared types between MIDI parsing and rendering  
**Duration**: 1 phase  
**Risk**: Low - pure type definitions with no side effects

**Tasks**:
1. ✓ Create `midi_types.py` with shared data contract
2. ✓ Define `MidiNote` (renderer-agnostic), `DrumNote` (with rendering metadata)
3. ✓ Define `DrumMapping` and `MidiSequence` types
4. ✓ Include `STANDARD_GM_DRUM_MAP` configuration
5. ✓ Add conversion/validation helper functions
6. ✓ Create comprehensive test suite (38 tests)

**Validation**:
- [x] All type tests pass (38/38 passing in 0.05s)
- [x] Immutability enforced (frozen dataclasses)
- [x] Clear documentation of contract
- [x] No breaking changes to existing code

**Results**: See `moderngl-midi-renderer.results.md` Phase 0

### Phase 1: Extract Core Functions (No GPU Work)
**Goal**: Extract and test MIDI parsing and calculation logic  
**Duration**: 1 phase  
**Risk**: Low - pure refactoring with existing tests

**Tasks**:
1. Create `midi_core.py` with MIDI parsing functions extracted from render_midi_to_video.py
2. Update parsing to use `MidiNote` and `DrumNote` types from `midi_types.py`
3. Create `midi_effects.py` with effect calculation functions
4. Add comprehensive unit tests for all extracted functions
5. Ensure `test_cv2_rendering.py` still passes (render_midi_to_video.py unchanged)

**Validation**:
- [ ] All extracted functions have unit tests
- [ ] Parsing produces `MidiNote` → `DrumNote` conversions correctly
- [ ] `pytest test_cv2_rendering.py` passes
- [ ] No functionality changes to render_midi_to_video.py

### Phase 2: Extend Animation System for MIDI
**Goal**: Adapt animation.py to handle MIDI notes instead of test data  
**Duration**: 1 phase  
**Risk**: Low - building on proven animation system

**Tasks**:
1. Add MIDI note structure to `animation.py` (compatible with DrumNote dataclass)
2. Extend `build_frame_scene()` to handle kick drum (screen-wide bars)
3. Add lane-based positioning functions
4. Create integration tests with real MIDI files

**Validation**:
- [ ] `test_animation.py` passes with new MIDI note types
- [ ] Frame scenes correctly represent kick drums and regular lanes
- [ ] Existing demo_animation.py still works

### Phase 3: Implement GPU Effects (Shaders)
**Goal**: Add visual effects to GPU rendering pipeline  
**Duration**: 2-3 phases (complex)  
**Risk**: Medium - shader programming, visual fidelity

**Tasks**:
1. **Phase 3a: Basic Visual Parity**
   - Extend shaders in `shell.py` for rounded rectangles (already done)
   - Add alpha blending support
   - Add per-note brightness (velocity-based)
   - Test against baseline images

2. **Phase 3b: Motion Blur Effect**
   - Implement multi-pass rendering for blur layers
   - Add temporal offsets to shader
   - Validate blur quality against PIL version

3. **Phase 3c: Highlight Circles**
   - Add circle primitive rendering
   - Implement pulse animation in shader
   - Add glow effect (layered circles with alpha)

**Validation**:
- [ ] Baseline comparison tests pass (tolerance: ±5 per RGB channel)
- [ ] Visual inspection confirms no quality loss
- [ ] Performance >100 FPS on reference hardware

### Phase 4: Build midi_renderer.py Orchestration
**Goal**: Create complete MIDI rendering pipeline using ModernGL  
**Duration**: 1 phase  
**Risk**: Low - assembling tested components

**Tasks**:
1. Create `midi_renderer.py` with main render function
2. Integrate MIDI parsing (midi_core)
3. Integrate frame generation (animation)
4. Integrate GPU rendering (shell)
5. Add FFmpeg video encoding with audio sync
6. Add project manager integration

**Validation**:
- [ ] Complete MIDI file renders to video
- [ ] Audio sync works correctly
- [ ] Performance targets met (>100 FPS)

### Phase 5: Integration and Regression Testing
**Goal**: Ensure production readiness and backward compatibility  
**Duration**: 1 phase  
**Risk**: Medium - final validation

**Tasks**:
1. Create `demo_midi.py` demonstrating full pipeline
2. Run full regression test suite
3. Compare output videos frame-by-frame with PIL version
4. Document performance improvements
5. Update `render_midi_to_video.py` to optionally use new renderer

**Validation**:
- [ ] All tests pass (`pytest`)
- [ ] Frame-by-frame comparison within tolerance
- [ ] Performance benchmarks documented
- [ ] User documentation updated

### Phase 6: Replace PIL Renderer (Optional/Future)
**Goal**: Make ModernGL renderer the default  
**Duration**: 1 phase  
**Risk**: Low - already validated

**Tasks**:
1. Add `--renderer` flag to `render_midi_to_video.py` (choices: 'pil', 'moderngl')
2. Default to 'moderngl' with fallback to 'pil'
3. Deprecation notice for PIL renderer
4. Update all relevant documentation

**Deferred**: This phase should only happen after Phase 5 validation in production use.

## Key Design Decisions

### 1. No Shader Refactoring of render_midi_to_video.py in Early Phases
The current `render_midi_to_video.py` must remain untouched until Phase 5+. Extract functions into new modules, but leave original file as-is to avoid breaking tests.

### 2. Functional Core Pattern Throughout
All new code follows strict functional core/imperative shell:
- `*_core.py` modules: Pure functions only
- `*_renderer.py`, `shell.py`: Side effects isolated here
- No GPU operations in core modules
- No calculations in shell modules

### 3. Progressive Visual Enhancement
Implement effects in order of complexity:
1. Basic rectangles with alpha
2. Rounded corners (already working)
3. Velocity-based brightness
4. Motion blur
5. Highlight circles with pulse

Each step must pass visual regression tests before proceeding.

### 4. Parallel Testing Strategy
- Keep PIL renderer working throughout migration
- Add comparison tests that render same MIDI with both renderers
- Use image diff tools to quantify visual differences
- Define acceptable tolerance (recommendation: ±5 per RGB channel)

## Testing Strategy

### Unit Tests (Functional Core)
- Test all MIDI parsing functions with various MIDI files
- Test effect calculations with boundary conditions
- Test coordinate transformations
- Fast execution (<0.1s total)

### Integration Tests (Animation System)
- Test frame scene generation with real MIDI data
- Test lane filtering and mapping
- Test visibility window calculations
- Medium execution (<1s total)

### Visual Regression Tests (GPU Rendering)
**Level 1: Smoke Tests** (<0.5s)
- Scene renders without crashing
- Output has correct dimensions
- All frame times produce valid output

**Level 2: Property Tests** (<2s)
- Notes appear in correct lanes
- Colors match MIDI velocity
- Alpha fading works correctly
- Kick drums span full width

**Level 3: Regression Tests** (5-10s, marked `@pytest.mark.slow`)
- Pixel-perfect comparison with baselines
- Run manually before releases
- Update baselines when intentional changes made

### Performance Tests
- Measure FPS for standardized MIDI file
- Compare against PIL baseline
- Must achieve >100 FPS target
- Document in results file

## Dependencies

### Required
- `moderngl` - Already installed
- `numpy` - Already installed
- `mido` - Already installed (MIDI parsing)
- `ffmpeg` - Already available (video encoding)

### No New Dependencies
This migration adds zero new dependencies.

## Success Metrics

### Performance
- **Target**: >100 FPS for 1920x1080 @ 60fps output
- **Baseline**: ~40 FPS with PIL renderer
- **Minimum Acceptable**: 80 FPS (2x improvement)

### Quality
- **Visual Fidelity**: ±5 RGB per channel vs PIL version
- **Anti-aliasing**: No visible stair-stepping on curves
- **Alpha Blending**: Smooth transparency transitions

### Code Quality
- **Test Coverage**: >85% on functional core
- **Tests Passing**: 100% of existing tests
- **Architecture**: Clean separation of concerns
- **Documentation**: All public functions documented

## File Changes Summary

### New Files
- `midi_types.py` (~275 lines) ✓ COMPLETED
- `test_midi_types.py` (~608 lines) ✓ COMPLETED
- `moderngl_renderer/midi_core.py` (~200 lines)
- `moderngl_renderer/midi_effects.py` (~150 lines)
- `moderngl_renderer/midi_renderer.py` (~300 lines)
- `moderngl_renderer/demo_midi.py` (~100 lines)
- `moderngl_renderer/test_midi_core.py` (~150 lines)
- `moderngl_renderer/test_midi_effects.py` (~100 lines)
- `moderngl_renderer/test_midi_renderer.py` (~200 lines)

### Modified Files
- `moderngl_renderer/core.py` (+50 lines - coordinate helpers)
- `moderngl_renderer/shell.py` (+100 lines - effect shaders)
- `moderngl_renderer/animation.py` (+80 lines - MIDI note support)
- `render_midi_to_video.py` (Phase 6 only - add renderer option)

### Unchanged Files
- All existing tests remain unchanged until Phase 5
- `demo_animation.py` continues working
- Project manager integration unchanged

## Commit Strategy

Each phase gets a single commit after completion:

```
Phase 1: "feat(moderngl): extract MIDI core functions - parsing and effects"
Phase 2: "feat(moderngl): extend animation system for MIDI notes"
Phase 3a: "feat(moderngl): implement basic visual effects in GPU"
Phase 3b: "feat(moderngl): add motion blur shader effect"
Phase 3c: "feat(moderngl): add highlight circle pulse effect"
Phase 4: "feat(moderngl): complete MIDI renderer orchestration"
Phase 5: "feat(moderngl): integrate and validate MIDI renderer"
Phase 6: "feat(moderngl): make GPU renderer default option"
```

Each commit message includes:
- Tests passing count
- Performance metrics (FPS)
- Lines added/changed

## Open Questions

1. **Q**: Should motion blur be implemented as multi-pass rendering or single-pass shader effect?
   **A**: [To be determined in Phase 3b based on performance testing]

2. **Q**: How to handle drum map configuration (currently hardcoded in render_midi_to_video.py)?
   **A**: [Extract to config.yaml in Phase 1]

3. **Q**: Should we support both PIL and ModernGL renderers long-term?
   **A**: [Defer until Phase 6 based on user feedback]

## References

- Existing instructions: `general.instructions.md`, `how-to-perform-testing.instructions.md`
- Current renderer: `render_midi_to_video.py`
- ModernGL demo: `moderngl_renderer/demo_animation.py`
- Test suite: `test_cv2_rendering.py`
- Animation system: `moderngl_renderer/animation.py`
