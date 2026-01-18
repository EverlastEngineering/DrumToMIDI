# Archive Directory

This directory contains code that was removed from the main codebase during cleanup but preserved for historical reference and potential future use.

## Contents

### `benchmarks/`
Performance benchmarking and profiling scripts that are not part of the regular test suite:
- `benchmark_opencv_rendering.py` - OpenCV drawing performance tests
- `profile_rendering.py` - Rendering profiling utilities

### `examples/`
Example scripts and usage demonstrations:
- `example_mdx23c_usage.py` - MDX23C model usage example

### `demos/`
Demo applications from moderngl_renderer:
- `demo_animation.py` - Animation demonstration (9% coverage)
- `demo_midi_video.py` - MIDI video demo
- `test_demo_animation.py` - Tests for demo_animation

### `debugging/`
Debugging utilities and experimental optimizers:
- `debugging_scripts/` - Complete debugging toolkit with documentation
  - Analysis tools (kick/snare bleed, onset detection)
  - Optimization experiments (Bayesian, random search, threshold)
  - Timing verification utilities
  - See `debugging_scripts/README.md` and `debugging_scripts/INDEX.md` for full documentation

## Why Archived?

These files were archived during Phase 1.5 (Dead Code Audit, January 2026) because:
- 0% or very low test coverage
- Not imported by production code
- Standalone utilities or examples
- Still potentially useful for reference or future development

## Restoration

To restore any of these files to production:
1. Copy file back to appropriate location
2. Add tests if needed
3. Update imports and documentation
4. Ensure proper integration with current codebase
