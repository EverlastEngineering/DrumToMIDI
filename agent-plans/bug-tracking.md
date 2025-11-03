## Bug: GPU-Resident Renderer Coordinate System Completely Broken
- **Status**: Open - Unsolved
- **Priority**: Critical
- **Description**: Notes render at wrong positions, move at half speed, only travel half the screen
- **Symptoms**:
  - Notes appear halfway down screen regardless of timing
  - Notes only move through ~50% of screen height (should be 85%)
  - Notes move at approximately half the expected speed
  - Every attempted fix either makes them upside-down or keeps same wrong behavior
- **What Was Tried**:
  1. Flipping coordinate formulas - made things worse
  2. Removing framebuffer flip - made notes upside down
  3. Changing shader addition/subtraction - wrong direction or no movement
  4. Adjusting time calculations - didn't affect position
- **Mathematical Verification** (all formulas check out mathematically):
  - `strike_line_y_norm = 1.0 - (918/1080) * 2.0 = -0.7` ✓
  - Shader converts back: `((1.0-(-0.7))/2.0)*1080 = 918` ✓
  - Falling: `y = 918 + (-2.0 * 432) = 54` ✓
  - But actual output doesn't match!
- **Key Observations**:
  - PIL renderer works perfectly with same input
  - GPU calculations verified correct on paper
  - Problem must be in how shader executes or how OpenGL interprets coordinates
  - Possibly related to viewport, framebuffer orientation, or NDC interpretation
- **Files Involved**:
  - `moderngl_renderer/gpu_resident_core.py` - Python coordinate conversions
  - `moderngl_renderer/gpu_resident_shaders.py` - GLSL shader with animation
  - `moderngl_renderer/gpu_resident_shell.py` - Framebuffer reading
- **Recommendation**: Compare with working non-GPU-resident ModernGL renderer to see differences

## Legacy Bug Notes

moderngl doesn't work
You're on a mac, you don't need docker.
Use `conda activate larsnet-midi` once before any commands to get in the right space.
Use project 13 to troubleshoot right now like this:
`python render_midi_to_video.py 13`
and like this to use moderngl:
`python render_midi_to_video.py 13 --use-moderngl`
`render_midi_to_video.py` has the code for PIL rendering.
- By default it uses the PIL renderer which works fine.