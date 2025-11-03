# ModernGL Renderer Integration Plan

## Context
The ModernGL renderer (`demo_midi_video.py`) is fully functional with:
- Notes falling at correct speeds (kick and regular notes synchronized)
- Proper coordinate system (notes start offscreen, fall continuously)
- Fade effect after passing strike line
- Lane markers and strike line rendering
- 100+ FPS performance (1.8x real-time speedup)

Need to integrate this into the main `render_midi_to_video.py` workflow.

## Architecture
The integration should follow functional core / imperative shell pattern:
- **Functional core**: `midi_animation.py` (pure functions, already done)
- **Imperative shell**: New module for ModernGL rendering with side effects

## Phases

### Phase 1: Extract Core Rendering Function
**Goal**: Move `render_midi_to_video()` from demo to a proper module

**Tasks**:
1. Create `moderngl_renderer/midi_video_moderngl.py`
2. Move `render_midi_to_video()` function with all helpers
3. Keep the functional core (`midi_animation.py`) separate
4. Add proper error handling and progress reporting
5. Add docstrings and type hints

**Success Criteria**:
- Function accepts same params as demo
- Can be imported and called from other modules
- No demo-specific code (hardcoded paths)
- Clean interface matching existing PIL renderer

### Phase 2: Integrate with render_midi_to_video.py
**Goal**: Add `--use-moderngl` flag to main script

**Tasks**:
1. Add `use_moderngl` parameter to `render_project_video()`
2. Branch logic: if `use_moderngl`, call ModernGL renderer, else use PIL
3. Pass through all necessary parameters (width, height, fps, audio)
4. Ensure output paths and project structure work correctly

**Success Criteria**:
- `python render_midi_to_video.py --use-moderngl` works
- Same output path structure as PIL renderer
- Audio sync works correctly
- Project metadata updated correctly

### Phase 3: Add Missing Visual Elements
**Goal**: Match feature parity with PIL renderer

**Tasks**:
1. Add legend (instrument names with colors) - optional for Phase 3
2. Add progress bar at top (current time / total duration) - optional
3. Add highlight circles at strike line - deferred to Phase 4

Note: May defer legend/progress to later if complexity too high. Core rendering is priority.

**Success Criteria**:
- Visual output matches or exceeds PIL quality
- Performance maintained (>90 FPS)
- All elements render correctly

### Phase 4: Testing and Documentation
**Goal**: Ensure quality and maintainability

**Tasks**:
1. Write unit tests for coordinate conversions
2. Write integration test comparing outputs
3. Update documentation (MIDI_VISUALIZATION_GUIDE.md)
4. Add performance benchmarks
5. Update README with ModernGL option

**Success Criteria**:
- All tests pass
- Documentation complete
- Users can switch between renderers easily

## Risks
1. **Audio sync issues**: FFmpeg stdin piping must work identically to PIL version
2. **Missing visual elements**: Legend/progress bar may be complex to add
3. **Platform differences**: ModernGL may behave differently on different GPUs
4. **Performance regression**: Must maintain >90 FPS on target hardware

## Success Metrics
- **Performance**: >100 FPS on Mac M1, >60 FPS on older hardware
- **Quality**: Visual output indistinguishable from PIL (except improvements)
- **Compatibility**: Works with all existing projects
- **Maintainability**: Clean separation of functional core and imperative shell

## Decision Log
- Using `midi_animation.py` as functional core (no changes needed)
- Creating new `midi_video_moderngl.py` for imperative shell
- Keeping demo file for testing/development reference
- Deferring legend/progress bar to Phase 3 (can be added incrementally)
