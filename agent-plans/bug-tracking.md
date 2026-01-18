## Bug: Broken import after file rename - render_midi_video_shell.py
- **Status**: Fixed
- **Priority**: High
- **Description**: After renaming `midi_video_moderngl.py` to `midi_video_shell.py`, two import statements were not updated, causing runtime failure when using ModernGL renderer
- **Steps to Reproduce**: 
  1. Create project and generate MIDI
  2. Use web UI to render video with ModernGL renderer
  3. Import fails: `ModuleNotFoundError: No module named 'moderngl_renderer.midi_video_moderngl'`
- **Expected Behavior**: ModernGL renderer should work via web UI
- **Actual Behavior**: Import fails at runtime
- **Root Cause**: Missing test coverage for `render_project_video()` with `use_moderngl=True` - the conditional import inside `if use_moderngl:` block was never executed in tests
- **Fixed in Commit**: (current session - 2026-01-18)
- **Follow-up Required**: Add integration test for `render_project_video()` with ModernGL renderer

## Bug: Text lane legend may overlap with next lane
- **Status**: Open
- **Priority**: Medium
- **Description**: Lane labels in video overlay can overlap when multiple instruments share a lane
- **Expected Behavior**: Each subsequent lane label should be on separate line with blank line spacing for multi-line lanes
- **Actual Behavior**: Text overlaps when two lines appear on one lane
- **Proposed Solution**: Put each subsequent lane down one line, with blank line between multi-line lanes

## Bug: Missing instrument labels
- **Status**: Open
- **Priority**: Low
- **Description**: Many instruments in the MIDI visualization don't have lane labels displayed
