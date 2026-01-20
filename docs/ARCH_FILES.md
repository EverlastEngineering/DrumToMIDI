# File and Folder Reference

Quick reference for all files and directories in the project.

## Root Directory Structure

```
larsnet/
├── README.md              # Project overview and quick start
├── AGENTS.md              # Instructions for AI agents
├── CONTRIBUTING.md        # Development guidelines
├── TODO.md                # Project roadmap
├── docs/                  # User and architecture documentation
│   ├── ARCH_*.md         # Architecture documentation (C4 model)
│   └── *.md              # User guides
├── agent-plans/           # Architecture decision records
├── webui/                 # Web application
├── stems_to_midi/         # Detection and MIDI conversion
├── moderngl_renderer/     # GPU-accelerated video rendering
├── lib_v5/                # External MDX model library
├── mdx_models/            # Pre-trained model weights (Git LFS)
├── user_files/            # User project storage
├── archive/               # Archived research tools
├── *.py                   # Core modules and CLI scripts
├── test_*.py              # Unit tests
├── *.sh                   # Development convenience scripts
├── midiconfig*.yaml       # MIDI conversion configuration
├── environment.yml        # Conda environment definition
├── pytest.ini             # Test configuration
├── ruff.toml              # Linter configuration
└── docker-compose.yaml    # Docker setup
```

## Architecture Documentation

| File | Purpose |
|------|---------|
| `ARCH_C1_OVERVIEW.md` | System context, user workflows, C1 diagram |
| `ARCH_C2_CONTAINERS.md` | Application containers, C2 diagram |
| `ARCH_C3_COMPONENTS.md` | Code structure, C3 diagram, package details |
| `ARCH_DATA_FLOW.md` | Audio → MIDI → Video pipeline |
| `ARCH_LAYERS.md` | Functional core vs imperative shell pattern |
| `ARCH_FILES.md` | This file - directory reference |

## Core Python Modules

### MIDI System
| File | Lines | Coverage | Purpose |
|------|-------|----------|---------|
| `midi_types.py` | 64 | 95% | Type contracts (MidiNote, MidiEvent, MidiFile) |
| `midi_parser.py` | 3 | 100% | Parse MIDI files to structured data |
| `midi_core.py` | 80 | 78% | MIDI operations (transpose, quantize, filter) |
| `midi_shell.py` | 27 | 78% | File I/O wrapper for MIDI operations |
| `midi_render_core.py` | 84 | 100% | Layout calculations for video rendering |

### Separation System
| File | Lines | Coverage | Purpose |
|------|-------|----------|---------|
| `separation_shell.py` | 142 | 8% | Audio stem separation orchestration |
| `mdx23c_optimized.py` | 226 | 11% | MDX23C model inference |
| `mdx23c_utils.py` | 176 | 47% | Model loading and configuration |
| `device_shell.py` | 118 | 8% | GPU device management (CUDA/MPS/CPU) |
| `sidechain_shell.py` | 143 | 38% | Bleed reduction between stems |

### Other Core Modules
| File | Lines | Coverage | Purpose |
|------|-------|----------|---------|
| `project_manager.py` | 195 | 68% | Project state and file management |
| `render_midi_video_shell.py` | 573 | 15% | Video rendering orchestration |

## CLI Scripts

| File | Purpose |
|------|---------|
| `separate.py` | Separate drum audio into 5 stems |
| `sidechain_cleanup.py` | Remove bleed between kick and snare |
| `stems_to_midi_cli.py` | Convert stems to MIDI file |
| `render_midi_to_video.py` | Create Rock Band-style visualization |

## Development Scripts

| File | Purpose |
|------|---------|
| `test_coverage.sh` | Run pytest with coverage report |
| `run_tests.sh` | Quick test run (no coverage) |
| `lint.sh` | Run ruff linter |
| `start_webui.sh` | Start web UI development server |

## Package: `stems_to_midi/`

Audio detection and MIDI conversion package.

```
stems_to_midi/
├── __init__.py
├── config.py              # Configuration dataclass (92% coverage)
├── detection.py           # Onset detection algorithms (91% coverage)
├── helpers.py             # Analysis utilities (66% coverage)
├── learning.py            # Threshold calibration (95% coverage)
├── midi.py                # MIDI file generation (100% coverage)
├── processor.py           # Main orchestrator (65% coverage)
└── optimization/          # CLI threshold tuning tools
    ├── extract_features.py
    └── optimize.py
```

### Key Responsibilities
- **detection.py**: Find drum hits using energy and spectral analysis
- **helpers.py**: RMS calculation, spectral features, hi-hat classification
- **learning.py**: Learn optimal thresholds from labeled data
- **midi.py**: Convert detections to MIDI file format
- **processor.py**: Orchestrate full stems → MIDI pipeline

## Package: `webui/`

Flask-based web application for browser UI.

```
webui/
├── app.py                 # Flask application entry point
├── config.py              # Flask configuration
├── config_engine.py       # Settings management (91% coverage)
├── config_schema.py       # Settings validation schema
├── jobs.py                # Background job queue (50% coverage)
├── api/                   # REST API endpoints
│   ├── __init__.py
│   ├── config.py         # Settings API (54% coverage)
│   ├── downloads.py      # File download endpoints (18% coverage)
│   ├── job_status.py     # Job tracking API (38% coverage)
│   ├── operations.py     # Separation/conversion ops (48% coverage)
│   ├── projects.py       # Project CRUD (69% coverage)
│   └── upload.py         # File upload endpoint (77% coverage)
├── static/               # Frontend assets
│   ├── css/
│   ├── js/
│   │   ├── app.js
│   │   ├── config.js
│   │   ├── operations.js
│   │   ├── projects.js
│   │   └── settings.js
│   └── img/
└── templates/            # HTML templates
    └── index.html
```

### Key Responsibilities
- **app.py**: Flask routes, startup, CORS configuration
- **api/**: RESTful endpoints for all operations
- **config_engine.py**: Schema-driven settings system
- **jobs.py**: Async job queue with progress tracking
- **static/js/**: Frontend JavaScript (vanilla, no framework)

## Package: `moderngl_renderer/`

GPU-accelerated video rendering using ModernGL.

```
moderngl_renderer/
├── __init__.py
├── animation.py           # Animation curves and easing (98% coverage)
├── core.py                # GPU primitives (100% coverage)
├── midi_animation.py      # MIDI-specific animations (94% coverage)
├── midi_video_core.py     # Video layout logic (58% coverage)
├── midi_video_shell.py    # GPU rendering shell (9% coverage)
├── shell.py               # Rendering orchestration (62% coverage)
└── text_overlay_shell.py  # Text rendering (12% coverage)
```

### Key Responsibilities
- **core.py**: Basic GPU operations (rectangles, blending, shaders)
- **animation.py**: Easing functions, fade curves, timing
- **midi_animation.py**: Note appearance/disappearance animations
- **midi_video_core.py**: Calculate note positions and colors
- **shell.py**: Orchestrate GPU context, frame rendering, encoding

## External Libraries

### `lib_v5/`
External MDX model library (excluded from coverage).

```
lib_v5/
├── mdxnet.py              # MDX network architecture
├── modules.py             # Building blocks
└── tfc_tdf_v3.py          # TFC-TDF model variant
```

**Purpose**: PyTorch model definitions for MDX23C architecture.

### `mdx_models/` (Git LFS)
Pre-trained model weights.

```
mdx_models/
├── BS-Rofo-SW-Fixed.ckpt          # Legacy model (699 MB)
├── BS-Rofo-SW-Fixed.yaml          # Legacy config
├── config_mdx23c.yaml             # MDX23C config
└── drumsep_5stems_mdx23c_jarredou.ckpt  # Main model (420 MB)
```

**Note**: Stored with Git LFS, not full files in repository.

## Configuration Files

| File | Purpose |
|------|---------|
| `midiconfig.yaml` | MIDI conversion settings (onset detection, spectral filtering) |
| `midiconfig_calibrated.yaml` | Optimized thresholds from learning |
| `environment.yml` | Conda environment definition |
| `conda-lock.yml` | Locked dependency versions |
| `pytest.ini` | Test runner configuration |
| `ruff.toml` | Linter rules and exclusions |
| `.coveragerc` | Coverage tool configuration |
| `.gitignore` | Git ignore patterns |
| `.gitattributes` | Git LFS configuration |

## Documentation: `docs/`

User-facing and architecture documentation.

```
docs/
├── ARCH_C1_OVERVIEW.md    # System context diagram (C4 Level 1)
├── ARCH_C2_CONTAINERS.md  # Container diagram (C4 Level 2)
├── ARCH_C3_COMPONENTS.md  # Component diagram (C4 Level 3)
├── ARCH_DATA_FLOW.md      # Audio processing pipeline
├── ARCH_LAYERS.md         # Functional core vs imperative shell
├── ARCH_FILES.md          # This file - directory reference
├── SETUP_MAC_NATIVE.md    # Mac native installation guide
├── SETUP_WINDOWS_GPU.md   # Windows GPU setup
├── STEMS_TO_MIDI_GUIDE.md # Detection system details
├── MIDI_VISUALIZATION_GUIDE.md  # Rendering details
├── SIDECHAIN_CLEANUP_GUIDE.md   # Bleed reduction
├── MDX23C_GUIDE.md        # Model usage guide
├── WEBUI_SETUP.md         # Web UI user guide
├── WEBUI_API.md           # REST API documentation
├── WEBUI_CONFIG_ENGINE.md # Settings system design
├── WEBUI_SETTINGS.md      # Available settings
├── ML_TRAINING_GUIDE.md   # Model training (WIP)
├── LEARNING_MODE.md       # Threshold calibration
├── ARCHIVED_FEATURES.md   # Deprecated features
├── DEPENDENCIES.md        # Environment notes
├── LARSNET.md             # Historical attribution
├── MDX23C_PERFORMANCE.md  # Performance benchmarks
├── MPS_PERFORMANCE_IMPROVEMENTS.md  # Mac GPU optimization
├── TESTING_MDX_PERFORMANCE.md       # Testing methodology
├── TRAINING_DATA_SHARING.md         # Dataset info
└── ALTERNATE_AUDIO_FEATURE.md       # Future feature
```

## Agent Plans: `agent-plans/`

Architecture decision records and planning documents.

```
agent-plans/
├── bug-tracking.md
├── codebase-audit-2026.plan.md
├── codebase-audit-2026.results.md
├── dead-code-audit.md
├── file-management-refactor.plan.md
├── file-management-refactor.results.md
├── full-gpu-rendering.plan.md
├── full-gpu-rendering.results.md
├── gpu-resident-architecture.plan.md
├── gpu-resident-architecture.results.md
├── hihat-detection-improvements.md
├── larsnet-to-stemtomidi-rename.plan.md
├── larsnet-to-stemtomidi-rename.results.md
├── mac-native-mps-support.plan.md
├── mac-native-mps-support.results.md
├── mdx-performance-optimization.plan.md
├── mdx-performance-optimization.results.md
├── midi-types-contract.plan.md
├── midi-types-contract.results.md
└── ...
```

**Purpose**: Track major refactoring efforts, architectural decisions, and their outcomes.

## Tests

### Unit Tests (Co-located with modules)
| File | Tests | Purpose |
|------|-------|---------|
| `test_midi_types.py` | 224 lines | Test MIDI data structures |
| `test_midi_core.py` | 66 lines | Test MIDI operations |
| `test_midi_parser.py` | 83 lines | Test MIDI parsing |
| `test_midi_render_core.py` | 204 lines | Test render layout |
| `test_midi_shell.py` | 60 lines | Test MIDI I/O |
| `test_project_manager.py` | 273 lines | Test project management |
| `test_mdx23c_utils.py` | 89 lines | Test model utilities |
| `test_separate.py` | 29 lines | Test separation |
| `stems_to_midi/test_*.py` | 1330 lines | Test detection pipeline |
| `moderngl_renderer/test_*.py` | 1159 lines | Test GPU rendering |
| `webui/test_*.py` | 813 lines | Test web API |

### Integration Tests
| File | Purpose |
|------|---------|
| `test_integration.py` | End-to-end pipeline tests |
| `test_compare_renderers.py` | Renderer parity tests |
| `test_coordinate_system.py` | Coordinate space tests |

### Performance Tests
| File | Purpose |
|------|---------|
| `test_mdx_performance.py` | Benchmark separation speed |
| `test_pure_opencv_speed.py` | Benchmark rendering speed |

## VSCode Configuration: `.vscode/`

```
.vscode/
├── tasks.json             # Auto-lint on project open
├── extensions.json        # Recommended extensions
└── settings.json          # Workspace settings (if exists)
```

## Docker Setup

| File | Purpose |
|------|---------|
| `Dockerfile` | Image definition (PyTorch + dependencies) |
| `docker-compose.yaml` | Service configuration, ports, volumes |

## User Storage: `user_files/`

Runtime directory for user projects.

```
user_files/
├── .gitkeep
└── <project_name>/        # Created at runtime
    ├── drums.wav          # Original audio
    ├── separated_stems/   # 5 stem files
    ├── midiconfig.yaml    # MIDI conversion config
    ├── output.mid         # Generated MIDI
    └── output.mp4         # Visualization video
```

**Note**: Only `.gitkeep` is tracked by git, rest is runtime data.

## Archived Code: `archive/`

Historical code preserved for reference.

```
archive/
├── README.md              # Archive guide
├── debugging/
│   └── debugging_scripts/ # Research optimization tools
│       ├── README.md
│       ├── ARCHITECTURE.md
│       ├── INDEX.md
│       └── *.py           # 20+ optimization scripts
└── benchmarks/
    ├── benchmark_opencv_rendering.py
    └── profile_rendering.py
```

**Purpose**: Preserve research tools and experiments without cluttering main codebase.

## GitHub Configuration: `.github/`

```
.github/
├── instructions/          # Agent development guidelines
│   ├── bug-tracking.instructions.md
│   ├── general.instructions.md
│   ├── how-to-perform-testing.instructions.md
│   ├── writing-documentation.instructions.md
│   └── you-can-edit-your-own-instructions.instructions.md
└── workflows/             # CI/CD (if exists)
```

## File Naming Conventions

### Functional Cores
- `*_core.py` - Pure logic, no side effects
- `*_types.py` - Type definitions and contracts
- `*/detection.py` - Detection algorithms
- `*/helpers.py` - Utility functions

### Imperative Shells
- `*_shell.py` - I/O, GPU, orchestration
- `separate.py`, `render_*.py` - CLI entry points
- `project_manager.py` - State management

### Tests
- `test_*.py` - Co-located with tested code
- `*/test_*.py` - Package-level tests

### Configuration
- `*config*.yaml` - YAML configuration files
- `*.ini` - INI-style configuration (pytest, etc.)
- `*.toml` - TOML configuration (ruff, etc.)

### Documentation
- `ARCH_*.md` - Architecture documentation
- `README.md` - Entry point
- `docs/*.md` - User guides
- `agent-plans/*.md` - ADRs and planning

## File Size Reference

| Category | Typical Size | Notes |
|----------|--------------|-------|
| Core modules | 80-200 lines | Focused, single responsibility |
| Shell modules | 140-570 lines | Orchestration, multiple I/O ops |
| Test files | 60-270 lines | Comprehensive edge cases |
| Model weights | 420-699 MB | Stored in Git LFS |
| User audio | 10-50 MB | Per stem, temporary |
| Generated MIDI | 5-20 KB | Compact binary format |
| Rendered video | 100-500 MB | Depends on length and quality |

## Related Documentation

- [ARCH_C1_OVERVIEW.md](ARCH_C1_OVERVIEW.md) - Start here for system overview
- [ARCH_C3_COMPONENTS.md](ARCH_C3_COMPONENTS.md) - Code structure details
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow
