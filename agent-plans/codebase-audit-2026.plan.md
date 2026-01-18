# DrumToMIDI Codebase Audit Plan

**Created**: January 17, 2026  
**Purpose**: Systematic audit of code quality, test coverage, architecture patterns, and technical debt

---

## Executive Summary

This audit identifies areas for stabilization and cleanup across the DrumToMIDI codebase. The project has grown organically with multiple rendering backends, a web UI with brittle settings synchronization, and inconsistent application of functional core / imperative shell patterns.

---

## 1. Architecture Assessment

### 1.1 Functional Core / Imperative Shell Compliance

**Well-Structured Modules** ✅
| Module | Core | Shell | Status |
|--------|------|-------|--------|
| MIDI parsing | `midi_core.py` | `midi_shell.py` | ✅ Clean separation |
| MIDI types | `midi_types.py` | N/A | ✅ Pure data contracts |
| ModernGL renderer | `moderngl_renderer/core.py` | `moderngl_renderer/shell.py` | ✅ Clean separation |
| Project manager | `project_manager.py` (pure funcs) | Same file (I/O funcs) | ⚠️ Mixed in same file |
| Config engine | `webui/config_engine.py` | `webui/api/config.py` | ✅ Clean separation |

**Modules Needing Refactoring** ❌
| Module | Lines | Issue |
|--------|-------|-------|
| `separate.py` | 183 | Mixes CLI, orchestration, and side effects |
| `separation_utils.py` | 306 | Mixes pure logic with file I/O |
| `stems_to_midi.py` | 430 | CLI orchestration mixed with processing |
| `sidechain_cleanup.py` | 378 | Side effects throughout |
| `render_midi_to_video.py` | 1288 | Large file with mixed concerns |
| `mdx23c_optimized.py` | 550 | ML model handling with side effects |

### 1.2 Code Duplication & Consolidation

**Rendering Systems (Multiple Implementations)**
- `moderngl_renderer/` - Current GPU renderer (7,302 lines)
- `moderngl_renderer/retired/` - Old GPU implementations (still present)
- `render_midi_to_video.py` - 1,288 lines (appears to duplicate some moderngl work)
- `midi_render_core.py` - 446 lines

**Recommendation**: Consolidate rendering to single moderngl implementation, remove retired code.

### 1.3 Module Naming Conflicts

- `stems_to_midi.py` (file) vs `stems_to_midi/` (package) - requires importlib workarounds in `webui/api/operations.py` line 68

---

## 2. Test Coverage Assessment

### 2.1 Current Test Files

| Test File | Lines | Target Module |
|-----------|-------|---------------|
| `test_midi_types.py` | 607 | `midi_types.py` |
| `test_midi_render_core.py` | 515 | `midi_render_core.py` |
| `test_project_manager.py` | 481 | `project_manager.py` |
| `webui/test_api.py` | 556 | Web API |
| `webui/test_config_engine.py` | 395 | Config parsing |
| `test_mdx_performance.py` | 386 | MDX23C performance |
| `test_midi_parser.py` | 202 | MIDI parsing |
| `test_midi_core.py` | 162 | MIDI core functions |
| `test_midi_shell.py` | 125 | MIDI file I/O |
| `test_separate.py` | 66 | Separation (minimal) |
| **Total** | **~5,238** | |

### 2.2 Coverage Gaps

**Untested or Minimally Tested**
- [ ] `separation_utils.py` - Core separation logic
- [ ] `sidechain_cleanup.py` - Audio processing
- [ ] `stems_to_midi/` package - Conversion logic
- [ ] `device_utils.py` - Device detection
- [ ] `mdx23c_utils.py` - Model utilities
- [ ] Web UI JavaScript files (no tests)

**Integration Test Gaps**
- [ ] End-to-end project workflow (separate → cleanup → midi → video)
- [ ] Docker container testing
- [ ] Web API integration tests with actual file processing

### 2.3 Test Quality Issues

- Many tests are property-based (good) but some rely on file fixtures
- No coverage reporting configured in `pytest.ini`
- Slow tests properly marked but coverage metrics unknown

---

## 3. Web UI Settings Architecture (Critical Issue)

### 3.1 Current State

The settings system requires manual synchronization across **four locations**:

1. **HTML** (`webui/templates/index.html`) - Form elements with hardcoded IDs
2. **JavaScript** (`webui/static/js/settings.js`) - Hardcoded defaults per operation
3. **Python API** (`webui/api/operations.py`) - Parameter extraction
4. **YAML Config** (`midiconfig.yaml`, `config.yaml`) - Actual values

**Example of Brittleness** (settings.js lines 176-243):
```javascript
switch (operation) {
    case 'separate':
        settings.device = this.settings['device'] || 'auto';
        settings.overlap = parseInt(this.settings['overlap']) || 4;
        // ... hardcoded defaults
```

### 3.2 Existing Infrastructure Not Utilized

`webui/config_engine.py` has a `to_ui_control()` method that generates UI specifications:
```python
def to_ui_control(self) -> Dict[str, Any]:
    return {
        'key': self.key,
        'type': self.field_type,
        'value': self.value,
        'label': self._format_label(),
        'description': self.comment,
        'validation': {...}
    }
```

This infrastructure exists but is **not connected to the frontend**.

### 3.3 Recommended Solution

**Schema-Driven Settings Architecture**:

1. Define settings schema in YAML with metadata (type, min, max, default, description)
2. Backend serves settings schema via API endpoint
3. Frontend renders settings dynamically from schema
4. Settings changes persist to YAML via existing config_engine.py
5. Remove all hardcoded settings from HTML and JavaScript

---

## 4. Code Quality Tools

### 4.1 Missing Tools

| Tool | Purpose | Priority |
|------|---------|----------|
| **pytest-cov** | Coverage reporting | High |
| **ruff** | Fast Python linter | High |
| **mypy** | Type checking (some type hints exist) | Medium |
| **pre-commit** | Automated checks | Medium |
| **Black/ruff-format** | Code formatting | Low |

### 4.2 Existing Configuration

- `pytest.ini` - Configured with slow/regression markers
- `# type: ignore` comments present - indicates type checking awareness
- No `.pre-commit-config.yaml`
- No `pyproject.toml` for tool configuration

---

## 5. Technical Debt Inventory

### 5.1 Dead Code

| Location | Description | Status |
|----------|-------------|--------|
| `moderngl_renderer/retired/` | 8 Python files of old implementations | ✅ Removed in Phase 1 |
| Multiple demo files | `demo_*.py` files in renderer | ⚠️ Needs analysis |
| Benchmark files | May be one-off experiments | ⚠️ Needs analysis |
| Root-level scripts | `example_*.py`, `profile_*.py`, `benchmark_*.py` | ⚠️ Needs analysis |
| Debugging scripts | `debugging_scripts/` directory | ⚠️ Review utility vs dead code |

**Detection Strategy:**
1. **Import analysis** - Search codebase for `from X import` and `import X` to find orphaned files
2. **Naming patterns** - Files matching `demo_*.py`, `example_*.py`, `benchmark_*.py`, `profile_*.py`, `test_*.py` (not in proper test directories)
3. **Git history** - Files with no commits in 6+ months (indicates abandonment)
4. **Coverage at 0%** - Files never executed by test suite or imports
5. **Manual review** - User confirmation before deletion

### 5.2 Documentation Staleness Risk

- 39 agent plan files in `agent-plans/` - some may be outdated
- Multiple guide files (SETUP_*.md, *_GUIDE.md) need freshness check
- TODO.md has 385 lines of planned features

### 5.3 Configuration Sprawl

- Root level: `config.yaml`, `midiconfig.yaml`, `midiconfig_calibrated.yaml`
- Per-project configs copied to each project folder
- Web UI has separate config engine but configs don't fully integrate

---

## 6. Prioritized Action Items

### Phase 1: Stabilization (1-2 weeks) ✅ COMPLETE

- [x] **Add pytest-cov** - Establish coverage baseline
- [x] **Add ruff** - Automated linting with auto-fix
- [x] **Run coverage report** - Identify actual gaps
- [x] **Clean retired code** - Remove `moderngl_renderer/retired/`
- [x] **Fix module naming** - Rename `stems_to_midi/` package to avoid conflict

### Phase 1.5: Dead Code Audit (NEW - 3-5 days)

- [ ] **Inventory all Python files** - Catalog every .py file with purpose classification
- [ ] **Check import usage** - Find files never imported by production code
- [ ] **Identify demo/benchmark files** - Classify test helpers vs actual dead code
- [ ] **Git history analysis** - Find files untouched for 6+ months
- [ ] **Create dead code candidates list** - Document findings for review
- [ ] **Archive or remove** - Move to archive/ or delete after user approval

### Phase 2: Test Coverage (2-3 weeks)

- [ ] **Add tests for `separation_utils.py`** - Core separation logic
- [ ] **Add tests for `sidechain_cleanup.py`** - Audio processing
- [ ] **Add tests for `stems_to_midi/` package** - Conversion logic
- [ ] **Reach 80% coverage** on functional core modules

### Phase 3: Web UI Refactoring (2-3 weeks)

- [ ] **Define settings schema** - YAML with metadata
- [ ] **Create settings API endpoint** - Serve schema dynamically
- [ ] **Refactor JavaScript** - Render settings from schema
- [ ] **Remove hardcoded settings** - From HTML and JS
- [ ] **Test settings persistence** - End-to-end

### Phase 4: Architecture Cleanup (Ongoing)

- [ ] **Extract cores from mixed modules** - separation_utils, sidechain_cleanup
- [ ] **Consolidate rendering** - Single path through moderngl
- [ ] **Unify project_manager.py** - Split to core/shell files
- [ ] **Archive old plans** - Move completed plans to archive folder

---

## 7. Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Test Coverage | Unknown | 80%+ on core modules |
| Lint Errors | Unknown | 0 |
| Type Check Errors | Unknown | 0 critical |
| Settings Sync Points | 4 | 1 (schema-driven) |
| Retired Code | ~8 files | 0 |

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| B~~Start Docker container and run existing tests to establish baseline~~ ✅ Done (native Mac)
2. ~~Add pytest-cov and generate initial coverage report~~ ✅ Done (64% baseline)
3. ~~Add ruff and fix critical linting issues~~ ✅ Done (365 errors identified)
4. ~~Create results tracking file for this audit~~ ✅ Done
5. **Run dead code audit** - Identify and catalog unused files
6. **Improve test coverage** - Target 80% on functional cores (Phase 2)
7. **Schema-driven settings** - Refactor web UI (Phase 3)m | Implement incrementally |

---

## Next Steps

1. Start Docker container and run existing tests to establish baseline
2. Add pytest-cov and generate initial coverage report
3. Add ruff and fix critical linting issues
4. Create results tracking file for this audit
