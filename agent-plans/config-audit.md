# Configuration Files Audit

## Current Config Files

### 1. config.yaml (100 lines) - MOSTLY DEPRECATED
**Location**: Root directory  
**Used by**: Legacy LarsNet training (no longer used)  
**Loaded by**: Webui supports it, but Python code doesn't use it

**Status breakdown**:
```yaml
global:
  sr: 44100                    # DUPLICATE (in mdx23c config)
  segment: 11.85               # DEPRECATED (LarsNet-specific)
  shift: 2                     # DEPRECATED (LarsNet-specific)
  sample_rate: 44100           # DUPLICATE (in mdx23c config, AND duplicate of 'sr')
  n_workers: 16                # DEPRECATED (LarsNet-specific)
  prefetch_factor: 6           # DEPRECATED (LarsNet-specific)

# inference_models: ...        # DEPRECATED (commented out, LarsNet paths)

data_augmentation:             # DEPRECATED (training-only, LarsNet-specific)
  augmentation_prob: 0.5       
  # ... all training params

kick/snare/toms/hihat/cymbals: # DEPRECATED (LarsNet training params)
  F: 2048                      # STFT frequency bins (training)
  T: 512                       # STFT time frames (training)
  batch_size: 24               # Training batch size
  learning_rate: 1e-4          # Training learning rate
  epochs: 22                   # Training epochs
  training_mode: 'stft'        # Training mode
  model_id: 'default_*_unet'   # Model identifier
```

**Verdict**: **Can be deleted or reduced to minimal stub**. Only `global.sr` might be useful, but it's in mdx23c config too.

---

### 2. midiconfig.yaml (241 lines) - ACTIVE
**Location**: Root directory  
**Used by**: All MIDI conversion (stems_to_midi/*)  
**Loaded by**: `stems_to_midi/config.py::load_config()`

**Status breakdown**:
```yaml
audio:                         # ACTIVE - used by detection/analysis
  force_mono: true             
  silence_threshold: 0.001     
  min_segment_length: 512      
  peak_window_sec: 0.10        
  sustain_window_sec: 0.2      
  envelope_threshold: 0.1      
  envelope_smooth_kernel: 51   
  default_note_duration: 0.1   
  very_short_duration: 0.01    

onset_detection:               # ACTIVE - global onset settings
  threshold: 0.3               
  delta: 0.01                  
  wait: 3                      
  hop_length: 512              

kick:                          # ACTIVE - per-stem settings
  midi_note: 36                
  onset_threshold: 0.1         
  onset_delta: 0.1             
  onset_wait: 2                
  timing_offset: -0.014        
  geomean_threshold: 70.0      
  # ... spectral ranges
  enable_statistical_filter: false
  # ... statistical params

snare:                         # ACTIVE
  midi_note: 38
  # ... similar structure

toms:                          # ACTIVE
  midi_note_low/mid/high: 45/47/50
  enable_pitch_detection: true
  # ... pitch & spectral params

hihat:                         # ACTIVE
  midi_note_closed/open: 42/46
  detect_open: true
  # ... open/closed detection params

cymbals:                       # ACTIVE
  midi_note: 57
  # ... sustain & spectral params

midi:                          # ACTIVE - MIDI output settings
  min_velocity: 80
  max_velocity: 110
  default_tempo: 120.0
  max_note_duration: 0.5

debug:                         # ACTIVE - debug output
  show_all_onsets: true
  show_spectral_data: true

learning_mode:                 # ACTIVE - calibration workflow
  enabled: false
  export_all_detections: true
  # ... learning params
```

**Verdict**: **All settings are actively used**. No duplicates, no deprecated settings.

---

### 3. mdx_models/config_mdx23c.yaml (70 lines) - ACTIVE
**Location**: mdx_models/  
**Used by**: MDX23C separation model  
**Loaded by**: separation code (lib_v5/nets_new.py, separate.py)

**Status breakdown**:
```yaml
audio:                         # ACTIVE - separation audio params
  chunk_size: 523776           
  dim_f: 1024                  
  dim_t: 1024                  
  hop_length: 512              # POTENTIAL DUPLICATE (midiconfig has hop_length too)
  n_fft: 2048                  
  num_channels: 2              
  sample_rate: 44100           # DUPLICATE (midiconfig.audio, config.global.sr)
  min_mean_abs: 0.000          

model:                         # ACTIVE - MDX23C architecture
  act: gelu
  bottleneck_factor: 4
  # ... model hyperparams

training:                      # ACTIVE (if training MDX23C)
  batch_size: 2
  instruments: [kick, snare, ...]
  # ... training params

loss_multistft:                # ACTIVE (if training)
  fft_sizes: [2048]
  # ... loss function params

inference:                     # ACTIVE - separation inference
  extension: flac
  batch_size: 2
  dim_t: 512
  num_overlap: 4
  normalize: false
```

**Verdict**: **All settings actively used**. `hop_length` and `sample_rate` duplicated across files but used in different contexts.

---

## Duplication Analysis

### Critical Duplicates (Same Concept, Different Contexts)

1. **sample_rate / sr**
   - `config.yaml::global.sr`: 44100 (DEPRECATED)
   - `config.yaml::global.sample_rate`: 44100 (DEPRECATED, duplicate of sr)
   - `midiconfig.yaml::audio.sample_rate`: NOT PRESENT (uses onset_detection.hop_length)
   - `mdx23c.yaml::audio.sample_rate`: 44100 (ACTIVE - separation)
   - **Verdict**: Only mdx23c version is active. midiconfig assumes 44100 implicitly.

2. **hop_length**
   - `midiconfig.yaml::onset_detection.hop_length`: 512 (ACTIVE - onset detection)
   - `mdx23c.yaml::audio.hop_length`: 512 (ACTIVE - separation STFT)
   - **Verdict**: Different purposes, both needed. Not a conflict.

3. **Stem names: kick/snare/toms/hihat/cymbals**
   - `config.yaml::kick/snare/etc`: Training params (DEPRECATED)
   - `midiconfig.yaml::kick/snare/etc`: MIDI conversion params (ACTIVE)
   - `mdx23c.yaml::training.instruments`: Model training (ACTIVE if training)
   - **Verdict**: Same names, different purposes. midiconfig is the only one used for inference.

---

## WebUI Integration

**What webui expects** (from `config_schema.py`):

```python
CONFIG_SCHEMA = {
    'global': True,      # Dict - expects config.yaml structure
    'audio': True,       # Dict - could be midiconfig OR config
    'separation': True,  # Dict - NOT IN ANY FILE YET
    'kick': True,        # Dict - both config.yaml and midiconfig have this
    # ... other stems
}

MIDICONFIG_SCHEMA = {
    'audio': True,       # Dict - midiconfig structure
    'onset_detection': True,
    'kick': True,
    # ... stems
    'midi': True,
    'debug': True,
    'learning_mode': True,
}
```

**Current state**:
- Webui supports loading both `config.yaml` and `midiconfig.yaml` from projects
- Schema validation exists for both file types
- **PROBLEM**: `CONFIG_SCHEMA` expects `separation` section that doesn't exist anywhere
- Python code (stems_to_midi) only loads `midiconfig.yaml`, ignores `config.yaml`

---

## Recommendations

### Option 1: Keep Separate (Minimal Changes)
1. **DELETE** config.yaml entirely (100% deprecated)
2. **KEEP** midiconfig.yaml as-is (100% active)
3. **KEEP** mdx23c config in mdx_models/ (separation-specific)
4. **UPDATE** webui schemas to remove config.yaml support
5. **ADD** webui support for mdx23c config viewing (read-only)

**Pros**: Simple, minimal risk, clear separation of concerns  
**Cons**: Three config files (but each serves different purpose)

### Option 2: Consolidate MIDI + Python Settings (Medium Effort)
1. **DELETE** config.yaml (deprecated)
2. **CREATE** new unified config:
   ```yaml
   audio:
     sample_rate: 44100      # Used by both separation and MIDI
   
   separation:               # MDX23C settings
     model: "mdx23c"
     chunk_size: "auto"
     # ... mdx23c params
   
   midi:                     # All current midiconfig content
     onset_detection: ...
     kick: ...
     # ... everything from midiconfig.yaml
   ```
3. **KEEP** mdx_models/config_mdx23c.yaml for model training
4. **UPDATE** all loaders to use new structure

**Pros**: Single source of truth for inference settings  
**Cons**: More code changes, migration needed

### Option 3: Audit First, Decide Later (What User Wants)
1. Mark all deprecated settings in config.yaml with `# DEPRECATED`
2. Add comments to duplicates explaining which is authoritative
3. Update this audit with findings
4. Make decision after seeing full picture

**This is where we are now** ✅

---

## Next Steps

1. Should we delete config.yaml entirely? (It's 100% unused)
2. Should we consolidate midiconfig + mdx23c settings?
3. Should we keep them separate (separation vs MIDI conversion)?
4. What does webui need to support?
