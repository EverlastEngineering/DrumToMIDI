# Bug Tracking

## Bug: MPS batch_size > 1 slower than batch_size=1
- **Status**: Fixed
- **Priority**: High
- **Description**: MPS device performs worse with higher batch sizes even at low overlap
- **Expected Behavior**: Higher batch sizes should improve performance
- **Actual Behavior**: batch_size=1 consistently faster than 2 or 4 across all overlap values
- **Fixed in Commit**: Changed MPS batch size logic to always use batch_size=1
- **Root Cause**: MPS unified memory architecture has different parallelization characteristics

## Bug: Legend shows all instruments even when lanes are filtered
- **Status**: Fixed
- **Priority**: Medium
- **Description**: When lanes are reduced because the MIDI has no instruments for that lane, the legend in the video still shows all instruments from DRUM_MAP
- **Expected Behavior**: Legend should only show instruments that are actually used in the song
- **Actual Behavior**: Legend shows all 11 instruments regardless of which are present
- **Root Cause**: Legend was cached before lane filtering logic determined which instruments are used
- **Fixed in Commit**: Modified `_get_cached_legend_layer()` to accept `used_notes` parameter and filter legend to only show instruments present in the MIDI file

## Bug: Alternate audio upload only accepts WAV files
- **Status**: Fixed
- **Priority**: Low
- **Description**: Upload alternate mix feature only accepted WAV files, but FFmpeg can handle many audio formats
- **Expected Behavior**: Should accept all common audio formats that FFmpeg supports
- **Actual Behavior**: API rejected non-WAV files with error message
- **Root Cause**: Backend validation was hardcoded to only check for .wav extension
- **Fixed in Commit**: Updated `upload_alternate_audio()` to accept WAV, MP3, FLAC, AIFF, AAC, OGG, and M4A formats. Updated documentation in WEBUI_SETUP.md and WEBUI_API.md.

## Bug: ModernGL renderer missing critical visual elements
- **Status**: Open
- **Priority**: High
- **Description**: ModernGL renderer only draws notes and highlight circles, missing multiple visual layers present in PIL renderer
- **Expected Behavior**: Should render complete visualization matching PIL renderer output
- **Actual Behavior**: Missing: strike line (horizontal bar), lane markers (circles), background lanes (vertical lines), UI layer (progress/time), legend layer (instrument names)
- **Root Cause**: Initial implementation focused only on note rendering, didn't port all visual elements from PIL renderer
- **Impact**: Videos look incomplete, users see bare notes without context

## Bug: ModernGL renderer performance bottleneck - CPU/GPU thrashing
- **Status**: Open
- **Priority**: High  
- **Description**: Only 2.17x speedup over PIL renderer despite GPU acceleration, should be much faster
- **Expected Behavior**: 10x+ speedup with proper GPU utilization
- **Actual Behavior**: Every frame does full CPU→GPU upload of all note geometry and GPU→CPU readback
- **Root Cause**: Architecture processes each frame independently:
  1. build_frame_from_drum_notes() converts notes to rectangles in Python (CPU)
  2. Uploads rectangle data to GPU
  3. Renders on GPU
  4. Reads framebuffer back to CPU
  This CPU↔GPU roundtrip per frame negates GPU benefits
- **Solution Direction**: 
  1. Pre-compute all note geometry once at initialization
  2. Upload ALL notes to GPU buffer once
  3. Each frame: only update time uniform and visibility culling on GPU via shaders
  4. Keep geometry resident on GPU, avoid per-frame uploads
  5. Stream read-back can remain since FFmpeg needs CPU frames anyway