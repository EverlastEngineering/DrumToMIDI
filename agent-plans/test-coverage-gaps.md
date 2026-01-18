# Test Coverage Gap Analysis

## Issue: Broken Import Passed Tests (2026-01-18)

### What Happened
After renaming `midi_video_moderngl.py` → `midi_video_shell.py`, two import statements were not updated:
- `render_midi_video_shell.py` line 1011
- `moderngl_renderer/midi_video_shell.py` line 12 (docstring)

**Result**: All 530 tests passed, but web UI video rendering failed at runtime with `ModuleNotFoundError`.

### Root Cause
The broken import is inside a conditional block that's never executed in tests:

```python
def render_project_video(..., use_moderngl=False):
    if use_moderngl:  # ← This path is NEVER tested
        from moderngl_renderer.midi_video_moderngl import ...  # ← Broken import
```

**Current Test Coverage**:
- ✅ `test_midi_video_moderngl.py` - Tests ModernGL renderer directly
- ✅ `test_integration.py` - Tests MIDI parsing and frame rendering
- ❌ **MISSING**: Integration test for `render_project_video()` with `use_moderngl=True`

### Coverage Stats
- `render_midi_video_shell.py`: 15% coverage
- **Problem**: The 85% uncovered code includes critical integration paths

### Why This Matters
This is a **regression detection failure** - the kind caught by end-to-end tests but missed by unit tests. It reveals:

1. **Imperative shell code** (file I/O, process spawning, GPU setup) is under-tested
2. **Integration paths** between modules aren't validated
3. **Conditional imports** create invisible test gaps

### Pattern Recognition
Similar risks exist in other shell files with conditional logic:
- `separation_shell.py` (8% coverage) - Model loading paths
- `device_shell.py` (8% coverage) - Device detection branches
- `sidechain_shell.py` (38% coverage) - Audio processing paths

## Recommended Testing Strategy

### Tier 1: Smoke Tests (PRIORITY)
Add fast integration tests (~0.5s each) that exercise actual code paths:

```python
def test_render_project_video_with_moderngl(test_project_fixture):
    """Smoke test: Verify ModernGL path doesn't crash on import"""
    # Doesn't need to produce perfect output, just needs to run
    render_project_video(
        test_project_fixture,
        use_moderngl=True,
        fps=1,  # Minimal frames for speed
        # ... minimal config
    )
    # Assert: No import errors, output file exists
```

**Coverage Target**: Execute each major code path at least once

### Tier 2: Property Tests
Already well-covered in ModernGL renderer tests. These verify behavior, not exact output.

### Tier 3: Regression Tests
Mark with `@pytest.mark.slow` - full video rendering validation.

## Action Items

### Immediate (Phase 2 - Test Coverage)
- [ ] Add smoke test for `render_project_video(use_moderngl=True)`
- [ ] Add smoke test for `render_project_video(use_opencv=True)`
- [ ] Verify both audio path options work
- [ ] Test with/without MIDI files present (error handling)

### Short-term (Phase 2)
- [ ] Add integration tests for `separation_shell.py` model loading
- [ ] Add integration tests for `device_shell.py` device detection
- [ ] Add integration tests for `sidechain_shell.py` audio processing

### Long-term (Phase 4)
- [ ] Extract functional cores from mixed modules
- [ ] Move imperative logic to dedicated shell files
- [ ] Increase shell test coverage to 60-80% (smoke + property tests)

## Prevention Strategy

### Code Review Checklist
When renaming files:
1. ✅ Update imports (grep for old filename)
2. ✅ Update documentation
3. ✅ Update test file references
4. ✅ **Run end-to-end test** via web UI or CLI
5. ✅ Check coverage report for dropped lines

### Testing Philosophy
**For imperative shells**:
- Don't aim for 100% coverage (too expensive for I/O code)
- DO ensure every major code path executes at least once
- Focus on "does it crash?" over "is output perfect?"

**Coverage targets**:
- Functional cores: 95-100% (cheap to test, high value)
- Imperative shells: 60-80% (smoke tests for all paths)
- Integration points: 100% (critical failure points)

## Lessons Learned

1. **File renames are risky** - imports can hide in conditional blocks
2. **High test count ≠ good coverage** - 530 tests missed a critical path
3. **Shell code needs different testing** - smoke tests > unit tests
4. **Runtime-only failures are expensive** - catch in CI, not production

## References
- Bug tracking: `agent-plans/bug-tracking.md` (entry added 2026-01-18)
- Testing guide: `.github/instructions/how-to-perform-testing.instructions.md`
- Coverage audit: `agent-plans/codebase-audit-2026.results.md`
