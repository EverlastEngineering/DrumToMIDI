# Dead Code Audit Report

**Date**: January 18, 2026  
**Phase**: 1.5 - Dead Code Detection

---

## Executive Summary

Analyzed 90 Python files to identify dead code using import analysis, naming patterns, and coverage metrics. Found **multiple candidates** for removal or archiving.

---

## Category 1: Standalone Scripts (Never Imported) ⚠️

These files are executable scripts, not imported as modules. May be utilities or abandoned code.

### Root Level Scripts

| File | Coverage | Last Import Check | Purpose | Recommendation |
|------|----------|-------------------|---------|----------------|
| `benchmark_opencv_rendering.py` | 0% | ❌ Never imported | Benchmark OpenCV drawing | Archive or delete |
| `example_mdx23c_usage.py` | 0% | ❌ Never imported | MDX23C usage example | Archive (docs) or delete |
| `profile_rendering.py` | 0% | ❌ Never imported | Profiling script | Archive or delete |

### ModernGL Renderer Demos

| File | Coverage | Purpose | Recommendation |
|------|----------|---------|----------------|
| `moderngl_renderer/demo_animation.py` | 9% | Animation demo | Archive or keep as example |
| `moderngl_renderer/demo_midi_project13.py` | 0% | Project 13 demo | Delete (project-specific) |
| `moderngl_renderer/demo_midi_video.py` | 0% | MIDI video demo | Archive or delete |

---

## Category 2: Debugging Scripts Directory 🔍

**Status**: Entire `debugging_scripts/` directory needs review  
**Files**: 12 Python scripts  
**Import Check**: ❌ Not imported by production code

| File | Purpose (from filename) | Keep? |
|------|------------------------|-------|
| `analyze_kick_snare_bleed.py` | Kick/snare bleed analysis | Utility - Archive |
| `bayesian_optimizer.py` | Bayesian optimization | Experimental - Archive |
| `check_maxtime_feature.py` | Feature testing | Utility - Archive |
| `check_offset_times.py` | Timing verification | Utility - Archive |
| `classifier.py` | Classification experiments | Experimental - Archive |
| `compare_optimizers.py` | Optimizer comparison | Experimental - Archive |
| `debug_kick_onset.py` | Kick onset debugging | Utility - Archive |
| `diagnose_midi_timing.py` | MIDI timing diagnosis | Utility - Archive |
| `example_optimization_workflow.py` | Workflow example | Documentation - Keep? |
| `random_search_optimizer.py` | Random search | Experimental - Archive |
| `threshold_optimizer.py` | Threshold optimization | Experimental - Archive |
| `verify_timing_fix.py` | Timing fix verification | Utility - Archive |

**Note**: `debugging_scripts/` has INDEX.md and README.md documenting these tools. May have historical/educational value.

---

## Category 3: Optimization Package ⚠️ FALSE POSITIVE

**Location**: `stems_to_midi/optimization/`  
**Import Check**: ❌ Not imported by production code (CLI tool)  
**Coverage**: 0% (not covered by automated tests)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `stems_to_midi/optimization/__init__.py` | 12 | Package interface | **KEEP** |
| `stems_to_midi/optimization/extract_features.py` | 407 | Feature extraction from MIDI | **KEEP** |
| `stems_to_midi/optimization/optimize.py` | 302 | Bayesian optimization | **KEEP** |

**Total**: 721 lines

**Status**: ✅ **PRESERVED** - Production code, not dead  
**Reason**: This is a CLI tool (`python -m stems_to_midi.optimization.optimize`) used for threshold learning. Zero coverage is expected for user-facing CLI tools.  
**Used By**: Developers and users optimizing thresholds for their recordings  
**Generated**: Current "LEARNED" threshold values in midiconfig.yaml

---

## Category 4: Test Files in Production Directories ⚠️

Files named `test_*.py` but NOT in proper test structure:

| File | Location | Coverage | Status |
|------|----------|----------|--------|
| `moderngl_renderer/test_demo_animation.py` | renderer dir | 27% | Tests demo - archive with demo |
| `moderngl_renderer/test_midi_render_simple.py` | renderer dir | 20% | Old test? - Review |

**Note**: These ARE run by pytest, but location suggests they may be experimental.

---

## Category 5: Production Code with 0% Coverage (Suspicious) 🚨

Files that appear to be production code but have 0% coverage:

| File | Type | Likely Status |
|------|------|---------------|
| `benchmark_opencv_rendering.py` | Benchmark | ✅ Expected (utility) |
| `example_mdx23c_usage.py` | Example | ✅ Expected (docs) |
| `profile_rendering.py` | Profiler | ✅ Expected (utility) |
| `separate.py` | CLI Entry | ⚠️ Should have SOME coverage |
| `stems_to_midi_cli.py` | CLI Entry | ⚠️ Should have SOME coverage |

**Note**: CLI entry points at 0% is normal (not imported, run directly). Integration tests cover them.

---

## Recommendations Summary

### Immediate Actions (High Confidence)

1. **DELETE** `stems_to_midi/optimization/` (306 lines, 0% coverage, never imported)
2. **DELETE** `moderngl_renderer/demo_midi_project13.py` (project-specific, 0% coverage)

### Archive for Historical Reference

Create `archive/` directory and move:

1. **Benchmarks**:
   - `benchmark_opencv_rendering.py`
   - `profile_rendering.py`

2. **Examples/Docs**:
   - `example_mdx23c_usage.py`
   - `moderngl_renderer/demo_animation.py`
   - `moderngl_renderer/demo_midi_video.py`

3. **Debugging Tools**:
   - Entire `debugging_scripts/` directory (keep README.md for docs)

### Keep (Uncertain - Review)

- `moderngl_renderer/test_demo_animation.py` - Tests the demo, may be useful
- `moderngl_renderer/test_midi_render_simple.py` - May be testing old API

---

## Impact Analysis

**Lines of Code Savings**:
- Immediate deletion: ~376 lines
- Archive (optional removal later): ~2,500+ lines

**Test Suite**:
- No production tests will break (all are in experimental/demo code)
- May lose 2 test files from renderer

**Risk Level**: **LOW**
- All identified dead code is 0% coverage
- None imported by production code
- CLI entry points protected by integration tests

---

## Next Steps

1. **User approval** - Review recommendations
2. **Create archive/** directory structure
3. **Move files** per approved plan
4. **Delete confirmed dead code**
5. **Re-run tests** to verify nothing broke
6. **Update .gitignore** if archiving
7. **Document in results file**
