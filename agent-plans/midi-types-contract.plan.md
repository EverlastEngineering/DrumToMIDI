# MIDI Types Contract - Shared Data Model

**Date**: November 2, 2025  
**Objective**: Establish a clear data contract between MIDI parsing and rendering systems, enabling decoupled development of MIDI extraction and rendering implementations.

## Context

The current `render_midi_to_video.py` has MIDI parsing tightly coupled to the renderer. The ModernGL renderer migration requires a clean separation. By establishing a shared type contract first, we can:

1. Extract MIDI parsing independently of rendering
2. Allow multiple renderers (PIL, ModernGL, future) to consume the same data
3. Make testing easier with standardized interfaces
4. Enable better type checking and IDE support

## Current State

### render_midi_to_video.py
- Has `DrumNote` dataclass with: `midi_note`, `time`, `velocity`, `lane`, `color`
- Has `DRUM_MAP` dictionary mapping MIDI notes to lane definitions
- MIDI parsing in `parse_midi()` method creates `DrumNote` instances directly
- Renderer consumes `List[DrumNote]` and duration

### moderngl_renderer
- Uses plain dictionaries with: `'time'`, `'lane'`, `'velocity'`
- No MIDI parsing capability yet (uses test data)
- Would benefit from standardized note structure

## Solution: Three-Tier Type System

### Tier 1: MidiNote (Pure MIDI Data)
**Purpose**: Renderer-agnostic, contains only data from MIDI file  
**Fields**: `midi_note`, `time`, `velocity`, `channel`, `duration`  
**Used by**: MIDI parsers, MIDI analysis tools, any system needing raw MIDI

### Tier 2: DrumNote (Rendering Metadata)
**Purpose**: MIDI + spatial/visual information for rendering  
**Fields**: `midi_note`, `time`, `velocity`, `lane`, `color`, `name`  
**Used by**: Video renderers that need lane layout and colors

### Tier 3: MidiSequence (Complete Context)
**Purpose**: Full MIDI file representation with metadata  
**Fields**: `notes`, `duration`, `tempo_map`, `ticks_per_beat`, `time_signature`  
**Used by**: Complete rendering pipeline, analysis tools

## Implementation

### File Created: `midi_types.py`

Located at project root (not in moderngl_renderer - this is shared infrastructure).

**Contents**:
- `MidiNote` dataclass (frozen, immutable)
- `DrumNote` dataclass (frozen, immutable)
- `DrumMapping` dataclass (drum map entries)
- `MidiSequence` dataclass (complete sequence container)
- Conversion functions between types
- Validation functions
- Standard GM drum map constant

**Design Principles**:
- All dataclasses are frozen (immutable)
- Pure data structures, no behavior
- Conversion functions are pure
- Validation raises ValueError on invalid data
- Type hints throughout

## Integration Plan

### Phase 1: Adopt Types in render_midi_to_video.py ✓ COMPLETED
**Goal**: Use new shared types, maintain backward compatibility  
**Risk**: Low - mostly adding imports and type aliases

**Tasks**:
1. Import `DrumNote` from `midi_types` (replace local definition)
2. Import `STANDARD_GM_DRUM_MAP` (rename local `DRUM_MAP`)
3. Update type hints to use shared types
4. Ensure all tests still pass

**Validation**:
- `pytest test_cv2_rendering.py` passes
- No functionality changes
- Type checking passes (`mypy` if used)

### Phase 2: Create Standalone MIDI Parser
**Goal**: Extract MIDI parsing to standalone module  
**Risk**: Low - pure extraction with clear interface

**Tasks**:
1. Create `midi_parser.py` with pure MIDI parsing functions
2. Extract `parse_midi()` logic from renderer class
3. Extract tempo map building logic
4. Return `MidiSequence` with `List[MidiNote]`
5. Add comprehensive unit tests

**Validation**:
- Parser tests pass with various MIDI files
- Parser is independent (no rendering imports)
- Existing render code still works

### Phase 3: Create Drum Mapper Module
**Goal**: Separate drum mapping logic from parsing and rendering  
**Risk**: Low - configuration-driven mapping

**Tasks**:
1. Create `drum_mapper.py` with mapping functions
2. Function: `apply_drum_map(notes: List[MidiNote], drum_map: DrumMapDict) -> List[DrumNote]`
3. Function: `filter_unused_lanes(notes: List[DrumNote]) -> Tuple[List[DrumNote], Dict]`
4. Support loading drum maps from config files
5. Add unit tests

**Validation**:
- Mapper tests pass
- Different drum maps produce correct lane assignments
- Lane filtering works correctly

### Phase 4: Integrate with render_midi_to_video.py
**Goal**: Use new parser and mapper in existing renderer  
**Risk**: Medium - changing working code, must not break tests

**Tasks**:
1. Replace `parse_midi()` method with calls to parser and mapper
2. Keep same interface to rendering code
3. Simplify renderer class (less code)
4. All existing tests pass

**Validation**:
- All existing tests pass unchanged
- Rendered videos are identical
- Code is simpler/shorter

### Phase 5: Integrate with moderngl_renderer
**Goal**: Add MIDI support to ModernGL renderer  
**Risk**: Low - adding new capability, not changing existing

**Tasks**:
1. Update `animation.py` to accept `DrumNote` or dict
2. Add conversion functions if needed
3. Create `demo_midi.py` that uses real MIDI files
4. Add tests with actual MIDI files

**Validation**:
- ModernGL can render real MIDI files
- Performance targets met
- Visual quality matches PIL renderer

## Benefits

### Immediate
- ✓ Clear contract documented
- ✓ Type safety improved
- ✓ Standard drum map extracted from code

### Short-term (After Phase 4)
- MIDI parsing testable independently
- Multiple renderers can use same parser
- Drum maps configurable without code changes
- Easier to add new MIDI features

### Long-term
- Support for different instrument types (not just drums)
- MIDI analysis tools can reuse parser
- Community can contribute drum maps
- A/B testing different renderers with same data

## Testing Strategy

### Unit Tests (Pure Functions)
**midi_types.py**:
- Test dataclass creation
- Test validation functions (valid and invalid cases)
- Test conversion functions
- Fast (<0.1s)

**midi_parser.py** (Phase 2):
- Test with various MIDI files
- Test tempo map extraction
- Test edge cases (no tempo, multiple tracks)
- Medium speed (<1s)

**drum_mapper.py** (Phase 3):
- Test mapping with different drum maps
- Test lane filtering
- Test multi-mapping (one MIDI note → multiple lanes)
- Fast (<0.1s)

### Integration Tests
**render_midi_to_video.py** (Phase 4):
- Existing test suite (`test_cv2_rendering.py`)
- Add tests for new parser integration
- Ensure videos are identical

**moderngl_renderer** (Phase 5):
- Add MIDI file rendering tests
- Visual regression tests
- Performance benchmarks

## Dependencies

### Required
- None! Uses only Python standard library + existing dependencies

### No Changes Needed
- `mido` (already installed) - used by parser
- `numpy` (already installed) - used by renderer
- All existing dependencies remain

## Files

### New Files
- ✓ `midi_types.py` (~280 lines) - Data contracts and utilities
- `midi_parser.py` (~200 lines) - Phase 2
- `drum_mapper.py` (~150 lines) - Phase 3

### Modified Files (Later Phases)
- `render_midi_to_video.py` (~50 lines changed) - Phase 1, 4
- `moderngl_renderer/animation.py` (~30 lines added) - Phase 5
- `moderngl_renderer/demo_midi.py` (new demo) - Phase 5

### Test Files
- `test_midi_types.py` (~150 lines) - Immediate
- `test_midi_parser.py` (~200 lines) - Phase 2
- `test_drum_mapper.py` (~150 lines) - Phase 3

## Success Criteria

### Phase 1 (Adoption)
- [ ] render_midi_to_video.py uses shared types
- [ ] All existing tests pass
- [ ] No functionality changes

### Phase 2 (Parser)
- [ ] MIDI parser is standalone and tested
- [ ] Returns standardized MidiSequence
- [ ] Works with various MIDI file formats

### Phase 3 (Mapper)
- [ ] Drum mapping is configuration-driven
- [ ] Lane filtering works correctly
- [ ] Multi-mapping supported

### Phase 4 (Integration - PIL)
- [ ] render_midi_to_video.py uses new modules
- [ ] Code is simpler (~100 lines removed)
- [ ] All tests pass
- [ ] Videos are identical

### Phase 5 (Integration - ModernGL)
- [ ] ModernGL can render real MIDI files
- [ ] Performance >100 FPS
- [ ] Visual quality matches PIL

## Risks & Mitigation

### Low Risk: Type Compatibility
**Issue**: DrumNote structure might need adjustment  
**Mitigation**: Created as frozen dataclass, easy to version  
**Strategy**: Add new fields without removing old ones

### Low Risk: Performance
**Issue**: Immutable dataclasses might have overhead  
**Mitigation**: Python dataclasses are efficient, frozen adds safety  
**Strategy**: Benchmark if concerns arise

### Medium Risk: Breaking Changes
**Issue**: Changing render_midi_to_video.py might break tests  
**Mitigation**: Incremental changes, run tests after each step  
**Strategy**: Keep existing interface while internals change

## Next Steps

1. ✓ Create `midi_types.py` with type definitions
2. Create `test_midi_types.py` with comprehensive tests
3. Begin Phase 1: Update render_midi_to_video.py imports
4. Validate all tests still pass
5. Proceed to Phase 2: Extract parser

## Open Questions

1. **Q**: Should we support non-drum MIDI instruments?  
   **A**: Not initially, but design allows for extension with new note types

2. **Q**: Should drum maps be in YAML config files?  
   **A**: Phase 3 will add config file support, keeping code constant as default

3. **Q**: How to handle custom/non-GM drum maps?  
   **A**: Phase 3 mapper will support loading custom maps from user config

## References

- Type definitions: `midi_types.py`
- Current renderer: `render_midi_to_video.py`
- ModernGL renderer: `moderngl_renderer/`
- Instructions: `general.instructions.md`
