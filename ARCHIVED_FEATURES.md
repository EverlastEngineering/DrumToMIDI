# Archived Features & Tools

**Purpose**: Track archived code that may be needed in the future. Prevents "out of sight, out of mind" during development.

**Archive Location**: `archive/` (excluded from git, pytest, and main codebase)

---

## Threshold Optimization Toolkit

### Production Integration: `stems_to_midi/optimization/` ✅ ACTIVE

**Location**: `stems_to_midi/optimization/` (in main codebase)  
**Size**: 721 lines (3 Python files)  
**Status*They Do

**Production system** (`stems_to_midi/optimization/`): Integrated Bayesian optimization that learns from your labeled project data and outputs optimal thresholds.

**Research tools** (archived): Standalone scripts for algorithm comparison and experimentation (Bayesian, Grid Search, Random Search).

The production system wason -m stems_to_midi.optimization.optimize 4 --stem hihat`

### Research Tools: `archive/debugging/debugging_scripts/` 📚 ARCHIVED

**Location**: `archive/debugging/debugging_scripts/`  
**Size**: 3,325 lines (12 Python files + comprehensive documentation)  
**Status**: Research/utility scripts, used to develop optimization methods

Standalone research scripts for threshold experimentation (not integrated with pipeline)

### What It Does

Provides machine learning-based optimization for drum detection thresholds using three methods:
1. **Bayesian Optimization** (recommended) - Intelligent, sample-efficient threshold discovery
2. **Grid Search** - Exhaustive testing for verification
3. **Random Search** - Fast exploration for high-dimensional spaces

These tools were used to generate the "LEARNED" threshold values in [midiconfig.yaml](midiconfig.yaml):
- Hi-hat open detection: `open_geomean_min: 262.0`, `open_sustain_ms: 100`
- Hi-hat spectral filtering: `geomean_threshold: 20.0`, `min_strength_threshold: 0.1`
- Kick statistical filtering parameters
- Timing offsets and onset detection parameters

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `bayesian_optimizer.py` | Gaussian Process-based threshold optimization | 423 |
| `threshold_optimizer.py` | Grid search for exhaustive verification | ~300 |
| `random_search_optimizer.py` | Random sampling for exploration | ~200 |
| `compare_optimizers.py` | Run all methods and compare results | ~150 |
| `classifier.py` | Feature importance analysis | ~100 |
| `example_optimization_workflow.py` | Educational demo of workflow | ~200 |

### Documentation

| Document | Purpose |
|----------|---------|
| **QUICK_START.md** | 5-minute getting started guide |
| **OPTIMIZATION_METHODS.md** | Technical comparison of algorithms (440 lines) |
| **README.md** | Comprehensive usage guide |
| **INDEX.md** | Navigation and file directory |
| **CHEAT_SHEET.md** | Command reference |
| **ARCHITECTURE.md** | System design and data flow |

### When You Might Need This

✅ **User wants to optimize detection for their specific drum recordings**  
**Use production system** (`stems_to_midi/optimization/`):
✅ **User wants to optimize detection for their specific drum recordings**  
✅ **Adding new instrument types that need threshold tuning**  
✅ **Debugging why certain hits are being missed or falsely detected**

**Use archived research tools**:
✅ **Research: comparing different optimization algorithms**  
✅ **Teaching/learning how optimization methods work**  
✅ **Prototyping new optimization approaches**

### How to Use

**Production optimization** (recommended):
```bash
# Already integrated, just run it:
python -m stems_to_midi.optimization.optimize 4 --stem hihat
```

**Research tools** (for experimentation):
```bash
cd archive/debugging/debugging_scripts
python bayesian_optimizer.py  # Compare with other methods
python compare_optimizers.py  # Run all methods
```
### Dependencies

```bash
pip install scikit-optimize  # For Bayesian optimization
pip install pandas numpy matplotlib  # Already installed
```

### Quick Usage Example

```bash
# Generate training data
python stems_to_midi_cli.py <PROJECT> --stems hihat 2>&1 | tee /tmp/hihat.log

# Label open hi-hat timestamps in data.csv (see QUICK_START.md)

# Run Bayesian optimization
cd archive/debugging/debugging_scripts
python bayesian_optimizer.py

# Results exported to bayesian_optimal_rules.csv
```

---

## Benchmarking & Profiling Tools

**Location**: `archive/benchmarks/`  
**Size**: ~800 lines (3 files)

| File | Purpose | When Needed |
|------|---------|-------------|
| `benchmark_opencv_rendering.py` | Compare OpenCV vs ModernGL rendering speed | Performance regression testing |
| `profile_rendering.py` | Detailed profiling of rendering pipeline | Optimizing render performance |

**Use Case**: Performance baseline when optimizing rendering code.

---

## Example & Demo Code

**Location**: `archive/examples/`, `archive/demos/`  
**Size**: ~1,200 lines (4 files)

| File | Purpose |
|------|---------|
| `example_mdx23c_usage.py` | Reference implementation for MDX23C separation |
| `demo_animation.py` | ModernGL animation system demo |
| `demo_midi_video.py` | MIDI visualization demo |

**Use Case**: Code examples when implementing new features or onboarding developers.

---

## Notes for Future Developers

1. **Don't delete the archive** - These tools have documentation value even if not actively used
2. **Git history preserves everything** - Deleted code can be recovered with `git show <commit>:<path>`
3. **Update this file** - When archiving new code, document it here with use cases
4. **Consider extraction** - If you need archived code frequently, it should be restored to the main codebase

---

**Last Updated**: January 18, 2026  
**Phase**: Codebase Audit 2026 - Phase 1.5 (Dead Code Cleanup)
