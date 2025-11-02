"""
Project Integration for ModernGL MIDI Renderer

Provides integration between the ModernGL renderer and the project management system.
This module bridges the gap between project_manager.py conventions and the ModernGL pipeline.

Architecture: Imperative Shell
- Orchestrates file I/O, parsing, rendering, and encoding
- Uses functional cores from other modules for logic
- Handles project structure navigation and metadata updates
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Import MIDI parser
from midi_parser import parse_midi_file
from midi_types import STANDARD_GM_DRUM_MAP

# Import ModernGL renderer components
from moderngl_renderer.midi_bridge_shell import render_midi_to_frames
from moderngl_renderer.gpu_resident_shell import render_midi_to_frames_gpu_resident
from moderngl_renderer.ffmpeg_encoder import FFmpegEncoder


def render_project_video_moderngl(
    project: Dict[str, Any],
    width: int = 1920,
    height: int = 1080,
    fps: int = 60,
    audio_source: Optional[str] = 'original',
    fall_speed_multiplier: float = 1.0,
    use_gpu_resident: bool = True
) -> None:
    """
    Render MIDI to video using ModernGL GPU renderer for a specific project.
    
    This is the ModernGL equivalent of render_project_video() from render_midi_to_video.py.
    Uses GPU-accelerated rendering via ModernGL for improved performance.
    
    Args:
        project: Project info dictionary from project_manager
        width: Video width in pixels (default: 1920)
        height: Video height in pixels (default: 1080)
        fps: Frames per second (default: 60)
        audio_source: Audio source selection - None (no audio), 'original', or 'alternate_mix/{filename}'
        fall_speed_multiplier: Speed multiplier for falling notes (1.0 = default, 0.5 = half speed, 2.0 = double speed)
        use_gpu_resident: Use GPU-resident architecture (uploads all notes once) for 10x+ speedup
    
    Side Effects:
        - Reads MIDI file from project/midi/ directory
        - Reads audio file from project root or alternate_mix/ directory
        - Writes video to project/video/ directory
        - Updates project metadata with video_rendered status
        - Prints progress messages to stdout
    """
    from project_manager import update_project_metadata  # Import here to avoid circular dependency
    
    project_dir = project["path"]
    
    print(f"\n{'='*60}")
    print(f"Rendering Video (ModernGL GPU) - Project {project['number']}: {project['name']}")
    print(f"{'='*60}\n")
    
    # Find MIDI files in project/midi/ directory
    midi_dir = project_dir / "midi"
    if not midi_dir.exists():
        print(f"ERROR: No midi/ directory found in project.")
        print("Run stems_to_midi.py first!")
        sys.exit(1)
    
    midi_files = list(midi_dir.glob("*.mid"))
    if not midi_files:
        print(f"ERROR: No MIDI files found in {midi_dir}")
        print("Run stems_to_midi.py first!")
        sys.exit(1)
    
    # Use first MIDI file
    midi_file = midi_files[0]
    if len(midi_files) > 1:
        print(f"Found {len(midi_files)} MIDI files, using: {midi_file.name}")
    else:
        print(f"Using MIDI file: {midi_file.name}")
    
    # Output to project/video/ directory
    video_dir = project_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # Resolve audio file path based on audio_source
    audio_file = None
    video_basename = midi_file.stem  # Default to MIDI name if no audio
    
    if audio_source:
        if audio_source == 'original':
            # Look for original audio file in project root
            audio_extensions = ['.wav', '.mp3', '.flac', '.aiff', '.aif']
            for ext in audio_extensions:
                potential_audio = project_dir / f"{project['name']}{ext}"
                if potential_audio.exists():
                    audio_file = str(potential_audio)
                    video_basename = Path(audio_file).stem
                    break
            
            if not audio_file:
                print("WARNING: Original audio requested but not found in project root")
                print(f"Looked for: {project['name']}{{.wav,.mp3,.flac,.aiff,.aif}}")
        
        elif audio_source.startswith('alternate_mix/'):
            # Use alternate audio file
            alternate_audio_path = project_dir / audio_source
            if alternate_audio_path.exists():
                audio_file = str(alternate_audio_path)
                video_basename = Path(audio_file).stem
            else:
                print(f"WARNING: Alternate audio '{audio_source}' not found")
        else:
            print(f"WARNING: Unknown audio_source value: {audio_source}")
    
    # Generate output filename
    output_file = video_dir / f"{video_basename}.mp4"
    
    print(f"Rendering video to: {output_file}")
    print(f"Settings: {width}x{height} @ {fps}fps")
    print(f"Note fall speed: {fall_speed_multiplier}x")
    if audio_file:
        print(f"Including audio: {Path(audio_file).name}")
    else:
        print("Audio: None")
    print()
    
    # Parse MIDI file
    print("Parsing MIDI file...")
    drum_notes, total_duration = parse_midi_file(
        str(midi_file),
        drum_map=STANDARD_GM_DRUM_MAP,
        tail_duration=3.0
    )
    print(f"Found {len(drum_notes)} drum notes, duration: {total_duration:.2f}s")
    
    # Calculate rendering parameters
    total_frames = int(total_duration * fps)
    
    print(f"Total frames: {total_frames}")
    
    # Select renderer
    if use_gpu_resident:
        print("Using GPU-resident renderer (optimized architecture)...")
        frame_generator = render_midi_to_frames_gpu_resident(
            notes=drum_notes,
            duration=total_duration,
            width=width,
            height=height,
            fps=fps,
            fall_speed_multiplier=fall_speed_multiplier
        )
    else:
        print("Using naive renderer (per-frame uploads)...")
        frame_generator = render_midi_to_frames(
            notes=drum_notes,
            width=width,
            height=height,
            fps=fps,
            duration=total_duration,
            fall_speed_multiplier=fall_speed_multiplier
        )
    
    # Encode to video
    with FFmpegEncoder(
        output_path=str(output_file),
        width=width,
        height=height,
        fps=fps,
        audio_path=audio_file
    ) as encoder:
        frame_count = 0
        for frame in frame_generator:
            encoder.write_frame(frame)
            frame_count += 1
            
            # Progress indicator every 60 frames (1 second at 60fps)
            if frame_count % 60 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Progress: {frame_count}/{total_frames} frames ({progress:.1f}%)", end='\r')
        
        print()  # New line after progress
    
    print(f"\nRendering complete!")
    print(f"Video saved to: {output_file}")
    
    # Update project metadata
    update_project_metadata(project_dir, {
        "status": {
            "separated": project["metadata"]["status"].get("separated", False) if project["metadata"] else False,
            "cleaned": project["metadata"]["status"].get("cleaned", False) if project["metadata"] else False,
            "midi_generated": project["metadata"]["status"].get("midi_generated", False) if project["metadata"] else False,
            "video_rendered": True
        }
    })
    
    print("Project status updated")
