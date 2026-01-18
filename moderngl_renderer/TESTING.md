# ModernGL Renderer Testing Strategy

## Overview

The ModernGL renderer follows the **functional core, imperative shell** pattern with appropriate testing for each layer.

## Test Coverage by Module

### Functional Core (100% coverage)
- `core.py` - Pure coordinate/data transformations
- `animation.py` - Time-based calculations
- `midi_animation.py` - MIDI to animation conversion
- `midi_video_core.py` - Video rendering calculations

These modules contain only pure functions and are fully unit tested.

### Imperative Shell (Level 1 & 2 integration tests)
- `shell.py` - GPU operations, shader execution, I/O

## Shader Testing Strategy

**Shaders are not directly tested.** They are implementation details of the GPU rendering pipeline.

Instead, we test shader behavior through the observable outputs:

### Level 1: Smoke Tests (Fast ~0.3s)
Verify basic GPU operations work without crashing:
- Context creation/cleanup
- Empty scene rendering
- Single rectangle rendering
- Output dimensions are correct

### Level 2: Property Tests (Robust ~0.5s)
Verify behavioral invariants that should hold regardless of shader changes:
- **Color correctness**: Red rectangles produce pixels with red > green/blue
- **Glow effects**: Glow increases overall brightness
- **Transparency**: Different brightness values produce different intensities
- **Resolution independence**: Different resolutions produce correctly sized output
- **Frame independence**: Sequential renders don't interfere
- **Outline rendering**: `no_outline` flag changes output
- **Rounded corners**: Corner radius produces smooth alpha transitions
- **Time-based effects**: Time parameter affects sparkle animation
- **Glow offset**: Glow offset parameter shifts the glow effect
- **Circle rendering**: Circles have correct colors and brightness
- **Circle overlay**: Circles overlay correctly on rectangles

### Why This Works

Property tests are **implementation-agnostic**:
- Changing blur radius won't break tests
- Modifying shader code won't break tests (unless behavior changes)
- Adding new visual effects won't require test updates

Tests verify the **"what"** (behavior), not the **"how"** (implementation).

### What About Visual Regression?

For pixel-perfect visual validation, use **Level 3: Regression Tests**:
- Marked with `@pytest.mark.slow` and `@pytest.mark.regression`
- Run manually before releases
- Compare against known-good baseline images
- Catch subtle visual changes

These are intentionally separate from CI/CD to avoid brittleness.

## Test Organization

```
moderngl_renderer/
├── core.py                      # Pure functions
├── test_core.py                 # 100% unit test coverage
├── animation.py                 # Pure functions
├── test_animation.py            # 100% unit test coverage
├── midi_video_core.py           # Pure functions
├── test_midi_video_core.py      # 100% unit test coverage
├── shell.py                     # GPU operations (shaders here)
├── test_shell.py                # Level 1 & 2 integration tests
├── midi_video_shell.py          # Video rendering pipeline
├── test_midi_video_moderngl.py  # Level 1 & 2 integration tests
└── test_visual_quality.py       # Level 3 regression tests
```

## Running Tests

```bash
# All tests (fast, runs in CI)
pytest moderngl_renderer/ -m "not slow"

# With coverage (excluding slow tests)
pytest moderngl_renderer/ --cov=moderngl_renderer -m "not slow"

# Include slow integration tests (video rendering, FFmpeg)
pytest moderngl_renderer/ -m "slow"

# All tests including slow
pytest moderngl_renderer/
```

## Test Development Guidelines

### When Adding New Shaders
1. **Don't** write shader-specific tests
2. **Do** add Level 2 property tests for observable behavior
3. **Do** ensure the public API remains testable

### When Modifying Visual Effects
1. Run full test suite to verify properties still hold
2. If properties change, update property tests
3. Update regression baselines if visual output changes intentionally

### When Refactoring
1. Tests should survive refactoring (they test behavior, not implementation)
2. If tests break during refactoring, they may be over-specified
3. Focus on testing the public interface

## Key Principle

> **Test the interface, not the implementation.**
> 
> Shaders are implementation details. We test their effects through observable outputs.
