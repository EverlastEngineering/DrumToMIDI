# Extract Functional Cores from Shell Files - Plan

## Objective
Extract all functional (pure) code from shell files into dedicated core modules, leaving only I/O, side effects, and orchestration in shell files. Achieve 95%+ test coverage on functional cores while minimizing shell file coverage targets.

## Architecture Principle
**Functional Core, Imperative Shell**
- Core files: Pure functions, no side effects, 95%+ coverage
- Shell files: I/O, GPU, file system, logging - minimal coverage needed

## Analysis of Current Shell Files

### 1. sidechain_shell.py (371 lines, 38% coverage)
**Functional code to extract:**
- ✅ `envelope_follower()` - Pure audio calculation (lines 28-66)
- ✅ `sidechain_compress()` - Pure audio processing (lines 67-148)

**Keep as shell:**
- `process_stems()` - File I/O wrapper
- `cleanup_project_stems()` - Project workflow orchestration
- CLI main() - argparse, user interaction

**New structure:**
- `sidechain_core.py` - Pure audio processing functions
- `sidechain_shell.py` - I/O and orchestration
- `test_sidechain_core.py` - Unit tests for pure functions

### 2. device_shell.py (234 lines, 8% coverage)
**Analysis:** Actually ALL imperative shell already!
- `detect_best_device()` - PyTorch queries, logging
- `get_device_info()` - PyTorch queries, caching
- `validate_device()` - PyTorch queries, fallback
- `print_device_info()` - Console output

**Action:** ✅ No extraction needed - properly architected

### 3. separation_shell.py (306 lines, 8% coverage)
**Functional code to extract:**
- Chunk calculation logic from `_process_with_mdx23c()` (computing overlap-add parameters)
- Audio preprocessing (stereo conversion, padding calculations)

**Keep as shell:**
- Model loading and inference (torch operations)
- Audio file I/O (torchaudio.load/save)
- Progress printing

**Analysis:** Most of this is legitimately imperative (model inference, I/O). Limited extraction value.

**Action:** ⚠️ Low priority - mostly proper shell already

### 4. render_midi_video_shell.py (1284 lines, 15% coverage)
**Functional code to extract:**
- ✅ `pil_to_cv2()` - Pure image conversion (line 64)
- ✅ `cv2_to_pil()` - Pure image conversion (line 78)
- ✅ `cv2_draw_rounded_rectangle()` - Pure drawing math (line 128)
- ✅ `cv2_composite_layer()` - Pure alpha blending (line 176)
- ✅ `cv2_draw_highlight_circle()` - Pure circle drawing (line 204)
- Calculations in `MidiVideoRenderer` class:
  - ✅ `should_draw_highlight()` - Pure time calculation
  - ✅ `calculate_strike_animation_progress()` - Pure math
  - Position/color calculations

**Keep as shell:**
- `MidiVideoRenderer.render()` - FFmpeg, file I/O, preview
- `render_project_video()` - Project orchestration
- Font loading, frame writing

**New structure:**
- `render_video_core.py` - Pure drawing/calculation functions
- `render_midi_video_shell.py` - Renderer class using core functions
- `test_render_video_core.py` - Unit tests

### 5. midi_shell.py (158 lines, tested via test_midi_shell.py)
**Analysis:** Check if any pure functions can be extracted from MIDI parsing

**Action:** Review and extract if needed

## Execution Phases

### Phase 1: Extract sidechain_core.py ⏱️ 30 min
1. Create `sidechain_core.py` with pure functions
2. Update `sidechain_shell.py` to import from core
3. Create `test_sidechain_core.py` with comprehensive tests
4. Verify all tests pass
5. Commit

**Success criteria:**
- `sidechain_core.py` has 95%+ coverage
- `envelope_follower()` and `sidechain_compress()` fully tested
- All existing integration tests still pass

### Phase 2: Extract render_video_core.py ⏱️ 60 min
1. Create `render_video_core.py` with pure drawing functions
2. Update `render_midi_video_shell.py` to import from core
3. Create `test_render_video_core.py` with unit tests
4. Verify all tests pass
5. Commit

**Success criteria:**
- `render_video_core.py` has 95%+ coverage
- All drawing functions have unit tests
- Existing rendering tests still pass

### Phase 3: Review remaining shells ⏱️ 20 min
1. Review `midi_shell.py` for extractable logic
2. Review `separation_shell.py` for extractable logic
3. Document findings
4. Extract if high value found
5. Commit

### Phase 4: Update documentation ⏱️ 15 min
1. Update architecture docs to reflect new core modules
2. Update coverage targets in .coveragerc if needed
3. Update AGENTS.md with new patterns
4. Commit

## Testing Strategy

### For Extracted Cores (95%+ coverage)
- **Unit tests**: Test each function independently
- **Edge cases**: Empty inputs, boundary conditions
- **Property tests**: Verify mathematical properties
- **Fast**: All tests run in < 1 second

### For Shells (minimal coverage)
- **Smoke tests**: Does it run without crashing?
- **Integration tests**: End-to-end via test_integration.py
- **No mocking**: Test real I/O when practical

## Risks & Mitigations

**Risk:** Breaking existing functionality during extraction
**Mitigation:** 
- Run full test suite after each phase
- Commit after each successful phase
- Work in feature branch (extract-functional-cores)

**Risk:** Circular dependencies during import refactoring
**Mitigation:**
- Core modules never import from shell modules
- Shell modules import from core modules
- Keep dependency graph acyclic

**Risk:** Test duplication (testing same logic twice)
**Mitigation:**
- Remove redundant integration tests once core tests exist
- Focus integration tests on I/O and orchestration

## Success Metrics

**Before:**
- sidechain_shell.py: 38% coverage (371 lines)
- render_midi_video_shell.py: 15% coverage (1284 lines)
- Total: ~22% coverage on shell files

**After:**
- sidechain_core.py: 95%+ coverage
- render_video_core.py: 95%+ coverage
- Shell files: 20-40% coverage (I/O paths only)
- Overall coverage: 70%+ (functional cores driving increase)

## Timeline
Total estimated time: 2-3 hours
- Phase 1: 30 min
- Phase 2: 60 min
- Phase 3: 20 min
- Phase 4: 15 min
- Buffer: 15-45 min

## Notes
- Work will be unattended - commit frequently
- Prioritize correctness over speed
- All tests must pass before committing
- Document any surprising findings in results file
