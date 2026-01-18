"""
MIDI Video Renderer Demo - Project 13

Demonstrates the ModernGL renderer using the new midi_video_moderngl module.
This file is kept for quick testing/development.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from moderngl_renderer.midi_video_shell import render_midi_to_video_moderngl
    

def main():
    """Demo: Render project 13 using ModernGL"""
    # Project 13 paths
    midi_path = "user_files/13 - srdrums/midi/srdrums.mid"
    audio_path = "user_files/13 - srdrums/srdrums.wav"
    output_path = "moderngl_renderer/test_artifacts/project13_moderngl.mp4"
    # midi_path = "user_files/1 - The Fate Of Ophelia/midi/The Fate Of Ophelia.mid"
    # audio_path = "user_files/1 - The Fate Of Ophelia/The Fate Of Ophelia.wav"
    # output_path = "moderngl_renderer/test_artifacts/project13_moderngl2.mp4"
    
    render_midi_to_video_moderngl(
        midi_path=midi_path,
        output_path=output_path,
        audio_path=audio_path,
        width=1920,
        height=1080,
        fps=60
    )


if __name__ == "__main__":
    main()
