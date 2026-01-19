# Comprehensive Architecture Analysis

Analysis of all code modules to identify functional core / imperative shell separation status and coverage gaps.

## Summary

### Already Well-Architected ✅

**Root-Level Shells** (Phases 1-3):
- `sidechain_shell.py` + `sidechain_core.py` (100% core coverage)
- `render_midi_video_shell.py` + `render_video_core.py` (100% core coverage)
- `midi_shell.py` + `midi_core.py` (78% core coverage)
- `separation_shell.py` (proper imperative shell, 8% expected)
- `device_shell.py` (proper imperative shell, 8% expected)

**stems_to_midi Package** (Already Excellent):
- `helpers.py` - **FUNCTIONAL CORE** (66% coverage - needs improvement)
- `detection.py` - Algorithm coordinators using librosa (91% coverage - good)
- `midi.py` - **FUNCTIONAL CORE** (100% coverage - excellent!)
- `learning.py` - Mixed core/shell (95% coverage - excellent!)
- `config.py` - Config dataclasses (92% coverage - excellent!)
- `processor.py` - **IMPERATIVE SHELL** (65% coverage - acceptable for shell)

**webui Package** (Already Good):
- `config_engine.py` - **FUNCTIONAL CORE** (91% coverage - excellent!)
- `config_schema.py` - **FUNCTIONAL CORE** (85% coverage - good)
- `config.py` - Config classes (100% coverage - excellent!)
- `jobs.py` - Job orchestration (50% coverage - shell with some logic)
- `app.py` - Flask app (65% coverage - shell, acceptable)
- `api/*` - REST endpoints (18-77% coverage - shells, mostly acceptable)

### Coverage Improvement Opportunities 🎯

**Priority 1: stems_to_midi/helpers.py**
- Status: **FUNCTIONAL CORE** with only 66% coverage
- Lines: 1370 lines of pure functions
- Missing: 402 lines, 137 missing (33%)
- Missing coverage in:
  - `analyze_cymbal_decay_pattern()` (lines 180-237) - 58 lines
  - `calculate_statistical_params()` (lines 387-416) - 30 lines  
  - `calculate_badness_score()` (lines 445-460) - 16 lines
  - `classify_tom_pitch()` internal logic (lines 610-624) - 15 lines
  - `filter_onsets_by_spectral()` complex branches (lines 800-895) - 96 lines
  - `calculate_velocities_from_features()` branches (lines 907-952) - 46 lines
- **Action**: Add tests for uncovered pure functions
- **Impact**: HIGH - this is core business logic

**Priority 2: stems_to_midi/processor.py**
- Status: **IMPERATIVE SHELL** with 65% coverage
- Lines: 305 lines
- Missing: 108 lines (35%)
- Contains orchestration logic that might be testable
- Missing coverage in:
  - Error handling paths
  - Edge case validation
  - Some orchestration paths
- **Action**: Review if shell coverage can be improved via integration tests
- **Impact**: MEDIUM - some orchestration logic could have higher coverage

**Priority 3: webui/jobs.py**
- Status: Mixed (Job classes + orchestration)
- Coverage: 50%
- Lines: 202 lines
- Missing: 101 lines
- Contains `JobQueue` class that has testable state management
- **Action**: Extract pure job state logic to core if valuable
- **Impact**: MEDIUM - job queue is critical infrastructure

**Priority 4: webui/api/* modules**
- Status: **IMPERATIVE SHELLS** (REST endpoints)
- Coverage: 18-77% (varies by module)
- Most are proper shells with Flask request/response handling
- Some contain validation/transformation logic that could be extracted
- **Action**: Review each API module for extractable pure logic
- **Impact**: LOW-MEDIUM - mostly proper shells, extraction would be minor

## Detailed Module Analysis

### stems_to_midi Package

#### helpers.py (FUNCTIONAL CORE - 66% coverage) 🔴
```
Lines: 1370
Covered: 265 (66%)
Missing: 137 lines in several functions
```

**Coverage Gaps:**
- `analyze_cymbal_decay_pattern()` (180-237): Cymbal analysis logic - 58 lines UNCOVERED
- `calculate_statistical_params()` (387-416): Statistical calculations - 30 lines UNCOVERED
- `calculate_badness_score()` (445-460): Quality scoring - 16 lines UNCOVERED
- `classify_tom_pitch()` K-means logic (610-624): Pitch classification - 15 lines UNCOVERED
- `filter_onsets_by_spectral()` branches (800-895): Complex spectral filtering - 96 lines UNCOVERED
- `calculate_velocities_from_features()` (907-952): Velocity calculation - 46 lines UNCOVERED

**Why This Matters:**
- These are PURE FUNCTIONS - should be 95%+ coverage
- Core business logic for drum detection quality
- Currently undertested despite being easily testable

**Recommendation:**
Add targeted unit tests for uncovered functions. All are pure, deterministic, no I/O.

#### detection.py (Algorithm Coordinator - 91% coverage) ✅
```
Lines: 91
Covered: 83 (91%)
Missing: 8 lines
```

**Architecture:** Proper imperative shell using librosa
- Coordinates onset detection
- Calls pure helpers for transformations
- 91% is excellent for algorithm coordinators

**Recommendation:** Coverage is excellent, no action needed.

#### midi.py (FUNCTIONAL CORE - 100% coverage) ✅
```
Lines: 41
Covered: 41 (100%)
Missing: 0 lines
```

**Perfect example of functional core with complete coverage.**

#### learning.py (Mixed - 95% coverage) ✅
```
Lines: 144
Covered: 137 (95%)
Missing: 7 lines
```

**Excellent coverage.** Contains both I/O (MIDI file loading) and pure logic (threshold calculation). Well-tested.

#### processor.py (IMPERATIVE SHELL - 65% coverage) 🟡
```
Lines: 305
Covered: 197 (65%)
Missing: 108 lines
```

**Architecture:** Imperative shell orchestrating the pipeline
- Loads audio files (I/O)
- Calls detection algorithms
- Calls pure helpers
- Coordinates multi-step workflow

**Missing coverage in:**
- Error handling paths (67-70, 117-118)
- Edge cases (168-220) - 53 lines
- Validation branches (492-495, 516, 540-541)
- Some orchestration paths (598-632) - 35 lines

**Analysis:**
For a shell, 65% is acceptable but could be higher. Some missing coverage is in:
1. Error paths (hard to test, acceptable)
2. Edge case validation (should be testable via integration tests)
3. Some orchestration logic (integration testable)

**Recommendation:**
Review if integration tests can cover more orchestration paths. May not need extraction.

### webui Package

#### config_engine.py (FUNCTIONAL CORE - 91% coverage) ✅
```
Lines: 197
Covered: 179 (91%)
Missing: 18 lines
```

**Excellent functional core for YAML parsing/validation.** Well-documented as "functional core". High coverage is appropriate.

#### config_schema.py (FUNCTIONAL CORE - 85% coverage) ✅
```
Lines: 26
Covered: 22 (85%)
Missing: 4 lines
```

**Good coverage for schema validation logic.**

#### jobs.py (Mixed - 50% coverage) 🟡
```
Lines: 202
Covered: 101 (50%)
Missing: 101 lines
```

**Contains:**
- `Job` dataclass with state management
- `JobQueue` class with threading
- `StdoutCapture` for log capturing

**Missing coverage in:**
- Job queue thread management (133-147) - 15 lines
- Stdout capture edge cases (160-214) - 55 lines
- Job execution paths (362-388) - 27 lines

**Analysis:**
This is mixed:
- Job state logic is testable
- Thread coordination is harder to test
- Stdout capture is I/O-ish

**Recommendation:**
Could extract pure job state logic to a core if worthwhile, but 50% may be acceptable given threading complexity.

#### api/* modules (REST endpoints - 18-77% coverage) 🟡
```
webui/api/config.py: 54% (92 lines, 42 missing)
webui/api/downloads.py: 18% (76 lines, 62 missing)
webui/api/job_status.py: 38% (77 lines, 48 missing)
webui/api/operations.py: 48% (127 lines, 66 missing)
webui/api/projects.py: 69% (154 lines, 48 missing)
webui/api/upload.py: 77% (30 lines, 7 missing)
```

**Architecture:** Imperative shells (Flask REST endpoints)
- Request parsing
- Response formatting
- Calling other modules

**Analysis:**
These are proper shells. Coverage varies:
- `upload.py` (77%) - Good
- `projects.py` (69%) - Good
- `operations.py` (48%) - Acceptable for shell
- `job_status.py` (38%) - Lower than expected
- `config.py` (54%) - Some logic might be extractable
- `downloads.py` (18%) - Very low, may have untested error paths

**Recommendation:**
Review if any contain validation/transformation logic that could be extracted to cores. Most are likely proper shells.

#### app.py (Flask App - 65% coverage) ✅
```
Lines: 72
Covered: 47 (65%)
Missing: 25 lines
```

**Proper imperative shell.** Flask app initialization, CORS setup, route registration. 65% is acceptable.

## Recommendations

### Immediate Actions (High Priority)

1. **stems_to_midi/helpers.py - Add missing tests** 🔴
   - Target: 95%+ coverage (from 66%)
   - Add tests for:
     - `analyze_cymbal_decay_pattern()` - 58 lines
     - `calculate_statistical_params()` - 30 lines
     - `calculate_badness_score()` - 16 lines
     - `classify_tom_pitch()` K-means logic - 15 lines
     - `filter_onsets_by_spectral()` branches - 96 lines
     - `calculate_velocities_from_features()` - 46 lines
   - **Impact**: Critical - these are core business logic functions
   - **Effort**: Medium (pure functions, no I/O, straightforward to test)
   - **Priority**: P0 - Do this first

### Medium Priority Actions

2. **Review stems_to_midi/processor.py orchestration** 🟡
   - Target: 75%+ coverage (from 65%)
   - Add integration tests for:
     - Edge case validation paths
     - Error handling scenarios
     - Orchestration branches
   - **Impact**: Medium - better test coverage for main pipeline
   - **Effort**: Medium (need integration test fixtures)
   - **Priority**: P1 - After helpers.py

3. **Review webui/jobs.py for extraction** 🟡
   - Target: Extract pure job state logic if valuable
   - Current: 50% coverage with threading complexity
   - **Impact**: Medium - job queue is critical but mostly imperative
   - **Effort**: Low-Medium (assess extraction value)
   - **Priority**: P2 - Optional improvement

4. **Review webui/api/* for extractable logic** 🟡
   - Target: Identify any validation/transformation logic
   - Look for pure functions hiding in endpoints
   - **Impact**: Low-Medium - most are proper shells
   - **Effort**: Low (code review, likely minimal extraction)
   - **Priority**: P3 - Optional cleanup

### Overall Assessment

**Good News:**
- Architecture is already largely correct ✅
- Most modules follow functional core / imperative shell ✅
- Several cores already have excellent coverage (midi.py 100%, learning.py 95%, config_engine.py 91%) ✅

**The Problem:**
- **stems_to_midi/helpers.py** is a FUNCTIONAL CORE with only 66% coverage 🔴
- This is the main gap blocking "rapid development with high confidence"
- 261 lines of uncovered pure business logic

**The Solution:**
1. **Phase 5**: Add comprehensive tests for stems_to_midi/helpers.py uncovered functions
2. **Phase 6** (optional): Review processor.py and webui modules for improvements

**Estimated Effort:**
- Phase 5 (helpers.py tests): 2-3 hours (add ~40-50 new tests for uncovered pure functions)
- Phase 6 (optional improvements): 1-2 hours (review + selective improvements)

**Expected Outcome:**
- stems_to_midi/helpers.py: 66% → 95%+ coverage
- Overall project: 68% → 73-75% coverage
- **High confidence for rapid stems_to_midi feature development** ✅
