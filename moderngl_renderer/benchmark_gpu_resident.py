"""
Benchmark GPU-resident rendering without FFmpeg bottleneck

Measures pure rendering performance by skipping video encoding.
"""

import time
from midi_parser import parse_midi_file
from midi_types import STANDARD_GM_DRUM_MAP
from moderngl_renderer.gpu_resident_shell import render_midi_to_frames_gpu_resident
from moderngl_renderer.midi_bridge_shell import render_midi_to_frames

def benchmark_renderer(name, renderer_func, notes, duration):
    """Benchmark a renderer function"""
    print(f"\n{'='*60}")
    print(f"Benchmarking: {name}")
    print(f"{'='*60}")
    
    frame_count = 0
    start_time = time.perf_counter()
    
    # Generate frames but don't encode
    for frame in renderer_func(
        notes=notes,
        duration=duration,
        width=1920,
        height=1080,
        fps=60,
        fall_speed_multiplier=1.0
    ):
        frame_count += 1
        # Just count frames, don't process them
    
    elapsed = time.perf_counter() - start_time
    fps = frame_count / elapsed
    
    print(f"Frames: {frame_count}")
    print(f"Time: {elapsed:.2f}s")
    print(f"FPS: {fps:.1f}")
    print(f"Per-frame: {(elapsed / frame_count) * 1000:.3f}ms")
    
    return elapsed, fps


if __name__ == "__main__":
    # Load test MIDI file
    midi_path = "user_files/2 - sdrums/midi/sdrums.mid"
    print(f"Loading MIDI: {midi_path}")
    notes, duration = parse_midi_file(midi_path, STANDARD_GM_DRUM_MAP, tail_duration=3.0)
    print(f"Notes: {len(notes)}, Duration: {duration:.2f}s")
    
    total_frames = int(duration * 60)
    print(f"Total frames to render: {total_frames}")
    
    # Benchmark naive renderer
    naive_time, naive_fps = benchmark_renderer(
        "Naive Renderer (per-frame uploads)",
        render_midi_to_frames,
        notes,
        duration
    )
    
    # Benchmark GPU-resident renderer
    gpu_time, gpu_fps = benchmark_renderer(
        "GPU-Resident Renderer (persistent buffer)",
        render_midi_to_frames_gpu_resident,
        notes,
        duration
    )
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Naive:        {naive_time:.2f}s ({naive_fps:.1f} fps)")
    print(f"GPU-Resident: {gpu_time:.2f}s ({gpu_fps:.1f} fps)")
    print(f"Speedup:      {naive_time / gpu_time:.2f}x")
    print(f"{'='*60}\n")
