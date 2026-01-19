# Phase 5: stems_to_midi/helpers.py Coverage Improvement

## Objective

Increase test coverage for `stems_to_midi/helpers.py` from 66% to 95%+ by adding comprehensive unit tests for uncovered pure functions.

## Context

**Current State:**
- helpers.py: 1370 lines, 66% coverage (402 statements, 137 missing)
- **This is a FUNCTIONAL CORE** - pure functions, no I/O, deterministic
- Already has test_helpers.py with 97 tests
- Missing coverage in 6 major functions

**Why This Matters:**
- stems_to_midi is critical for feature development
- These are core business logic functions (drum detection quality)
- Pure functions are easy to test but currently undertested
- Blocks rapid development with confidence

## Missing Coverage Analysis

### Function 1: `analyze_cymbal_decay_pattern()` (lines 180-237)
- **Missing**: 58 lines
- **Purpose**: Analyze cymbal decay characteristics for classification
- **Inputs**: audio segment, sample rate, onset sample
- **Output**: decay metrics dict
- **Tests Needed**: ~8 tests
  - Synthetic cymbal with fast decay
  - Synthetic cymbal with slow decay
  - Short audio segments
  - No decay detected
  - Edge cases (empty audio, single sample)

### Function 2: `calculate_statistical_params()` (lines 387-416)
- **Missing**: 30 lines
- **Purpose**: Calculate mean, std, percentiles from onset data
- **Inputs**: List of onset data dicts
- **Output**: Statistical parameters dict
- **Tests Needed**: ~5 tests
  - Normal distribution of onsets
  - Skewed distribution
  - Single onset
  - Empty list
  - All same values

### Function 3: `calculate_badness_score()` (lines 445-460)
- **Missing**: 16 lines
- **Purpose**: Score onset quality based on deviation from thresholds
- **Inputs**: onset features, statistical params
- **Output**: badness score (float)
- **Tests Needed**: ~5 tests
  - Perfect onset (score = 0)
  - Bad onset (high score)
  - Onset at mean
  - Edge cases (extreme values)
  - Missing features

### Function 4: `classify_tom_pitch()` - K-means logic (lines 610-624)
- **Missing**: 15 lines
- **Purpose**: Classify tom pitches into high/mid/low using K-means
- **Inputs**: pitch array
- **Output**: classified pitch array (MIDI notes)
- **Tests Needed**: ~6 tests
  - Three distinct pitch clusters
  - Two pitch clusters
  - Single pitch
  - Empty array
  - Edge case: all same pitch
  - Verify MIDI note assignments (high=50, mid=48, low=47)

### Function 5: `filter_onsets_by_spectral()` (lines 800-895)
- **Missing**: 96 lines (LARGEST gap)
- **Purpose**: Filter false positive onsets using spectral analysis
- **Inputs**: onset times, audio, sr, config
- **Output**: filtered onset times
- **Tests Needed**: ~12 tests
  - All onsets pass filter
  - All onsets fail filter
  - Mixed pass/fail
  - Different stem types (kick, snare, hihat)
  - Edge cases (empty onsets, empty audio)
  - Spectral energy calculations
  - Geometric mean calculations
  - Threshold comparisons
  - Confidence score calculations

### Function 6: `calculate_velocities_from_features()` (lines 907-952)
- **Missing**: 46 lines
- **Purpose**: Calculate MIDI velocities from onset features
- **Inputs**: onset features array
- **Output**: velocity array
- **Tests Needed**: ~8 tests
  - Linear velocity mapping
  - Normalized features
  - Features at boundaries (0.0, 1.0)
  - Empty features
  - Single feature
  - Features with outliers
  - Verify velocity range (40-127)

## Test Strategy

### Approach
1. Create synthetic test data (no real audio files needed)
2. Test each function in isolation (unit tests)
3. Focus on edge cases and boundary conditions
4. Use property-based testing where applicable
5. Verify deterministic output

### Test Structure
```python
class TestAnalyzeCymbalDecayPattern:
    def test_fast_decay_cymbal(self):
        """Cymbal with fast decay should have short sustain time"""
        audio = create_synthetic_cymbal(decay_time=0.1)
        result = analyze_cymbal_decay_pattern(audio, sr=22050, onset_sample=0)
        assert result['sustain_time'] < 0.15
        assert result['decay_rate'] > threshold
    
    def test_slow_decay_cymbal(self):
        """Cymbal with slow decay should have long sustain time"""
        # ...
```

### Synthetic Data Helpers
- `create_synthetic_cymbal(decay_time, sr)` - Exponentially decaying noise
- `create_synthetic_onsets(times, sr)` - Audio with onsets at specific times
- `create_onset_features(n, distribution)` - Feature arrays for testing

## Success Criteria

- [ ] helpers.py coverage: 66% → 95%+
- [ ] All 6 uncovered functions have comprehensive tests
- [ ] ~44 new tests added to test_helpers.py
- [ ] All tests pass
- [ ] No regressions in existing tests
- [ ] Tests run fast (<2 seconds for new tests)

## Time Estimate

- Analysis of uncovered functions: 30 minutes
- Write synthetic data helpers: 30 minutes
- Write tests for Function 1 (cymbal decay): 20 minutes
- Write tests for Function 2 (statistical params): 15 minutes
- Write tests for Function 3 (badness score): 15 minutes
- Write tests for Function 4 (classify tom pitch): 20 minutes
- Write tests for Function 5 (spectral filtering): 45 minutes (largest)
- Write tests for Function 6 (velocities): 25 minutes
- Verify coverage and fix gaps: 20 minutes
- **Total: ~4 hours**

## Risks

**Risk**: Functions may have complex dependencies on config structure
- **Mitigation**: Use sample_config() fixture from existing tests

**Risk**: Spectral analysis may be hard to test without understanding algorithm
- **Mitigation**: Focus on boundary conditions and property tests (output shape, ranges)

**Risk**: May uncover bugs in untested code
- **Mitigation**: Fix bugs as found, document in bug-tracking.md

## Dependencies

- Existing fixtures in test_helpers.py
- numpy for synthetic data generation
- scipy for signal processing in synthetic data

## Deliverables

1. Updated test_helpers.py with ~44 new tests
2. Updated coverage report showing 95%+ for helpers.py
3. Documentation of any bugs found
4. Commit with metrics

## Next Steps After Phase 5

**If successful** (95%+ coverage on helpers.py):
- Move to Phase 6: Review processor.py for integration test improvements
- Consider webui improvements (lower priority)

**If blocks are found** (e.g., untestable code due to poor architecture):
- Document architectural issues
- Propose refactoring if needed
- Adjust coverage target

## Notes

This is the **highest priority improvement** for the codebase. stems_to_midi/helpers.py contains core business logic that should be thoroughly tested. Current 66% coverage is unacceptable for a functional core that will undergo rapid feature development.
