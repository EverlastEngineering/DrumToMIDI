# Full GPU Rendering Pipeline - Plan

## Context
Current implementation is MUCH slower than PIL because it does frame-by-frame GPU rendering with constant CPU↔GPU transfers. Notes also render upside down due to coordinate system bug.

## Goal
Implement true batched GPU rendering where ALL frames are rendered on GPU in one pass, eliminating per-frame CPU↔GPU transfers.

## Current Problems
1. **Performance**: Frame-by-frame rendering = thousands of CPU↔GPU roundtrips
2. **Coordinate bug**: Notes moving UP instead of DOWN
3. **Visual quality**: Missing PIL effects (motion blur, highlights, proper glow)
4. **Architecture**: Added GPU overhead without removing PIL bottleneck

## Approach

### Phase 1: Pre-compute All Frame Scenes (CPU)
- Convert all MIDI notes to rectangle data for each frame
- Use existing `build_frame_scene()` from moderngl_renderer
- Adapt MIDI note format to ModernGL format
- Store all frame scenes in memory

### Phase 2: Batch GPU Rendering
- Use `render_frames_to_array()` to render all frames on GPU
- Single upload, GPU renders all frames, single download
- Get numpy array of all frames (no PIL conversion needed)

### Phase 3: UI/Legend Overlay
- For elements that need text (progress bar, legend):
  - Option A: Render on GPU as rectangles (no text)
  - Option B: Pre-render text as textures, composite on GPU
  - Option C: Quick PIL overlay after GPU render (compromise)
- Start with Option C for speed, optimize later if needed

### Phase 4: Direct to FFmpeg
- Feed frames directly from numpy array to FFmpeg
- No PIL conversion needed for notes
- Minimal PIL for UI overlay only

## Risks
1. **Memory**: All frames in memory could be large (~1-2GB for 3min video)
2. **Note format mismatch**: MIDI DrumNote vs ModernGL dict format
3. **Coordinate systems**: Need to fix the upside-down bug
4. **UI rendering**: May need text rendering on GPU or PIL hybrid

## Success Criteria
- [ ] Render 30-second video in <10 seconds (target: 4-5x faster than PIL)
- [ ] Notes fall DOWN correctly
- [ ] Visual quality acceptable (glow, colors, smooth animation)
- [ ] Memory usage reasonable (<4GB for typical song)
- [ ] All existing features work (kick drum, lanes, strike line, UI)

## Rollback Plan
If performance doesn't improve or memory is too high, we can:
1. Keep PIL rendering (it works)
2. Use ModernGL only for specific effects (blur/glow)
3. Implement streaming batch rendering (render 60 frames at a time)
