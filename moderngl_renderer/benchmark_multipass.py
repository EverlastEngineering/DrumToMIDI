#!/usr/bin/env python3
"""
Benchmark script to compare single-pass vs multi-pass rendering performance.
Uses the existing demo_animation.py workflow.
"""

import time
import subprocess
import sys

def benchmark_branch(branch_name, output_label):
    """Checkout a branch and run the demo, measuring time."""
    
    print(f"\n{'='*60}")
    print(f"Benchmarking: {output_label}")
    print(f"Branch: {branch_name}")
    print(f"{'='*60}\n")
    
    # Checkout branch
    subprocess.run(['git', 'checkout', branch_name], check=True, capture_output=True)
    
    # Run demo and measure time
    start = time.perf_counter()
    result = subprocess.run([sys.executable, 'demo_animation.py'], check=True, capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    
    # Parse FPS from output (looks for "  FPS: 215.6" line)
    fps = None
    for line in result.stdout.split('\n'):
        if line.strip().startswith('FPS:'):
            try:
                fps = float(line.split(':')[1].strip())
                break
            except:
                pass
    
    print(f"\n{output_label} Results:")
    print(f"  Total time: {elapsed:.2f}s")
    if fps:
        print(f"  Average FPS: {fps:.1f}")
    print(f"  Time per frame: {elapsed/300*1000:.2f}ms (300 frames)")
    
    return elapsed, fps

if __name__ == '__main__':
    print("Multi-pass vs Single-pass Rendering Benchmark")
    print("=" * 60)
    
    # Benchmark single-pass (original branch)
    single_time, single_fps = benchmark_branch('feature/moderngl-renderer-poc', 'Single-Pass')
    
    # Benchmark multi-pass (current branch)
    multi_time, multi_fps = benchmark_branch('feature/moderngl-multipass-renderer', 'Multi-Pass')
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Single-Pass: {single_time:.2f}s" + (f" ({single_fps:.1f} FPS)" if single_fps else ""))
    print(f"Multi-Pass:  {multi_time:.2f}s" + (f" ({multi_fps:.1f} FPS)" if multi_fps else ""))
    
    if multi_time > single_time:
        slowdown = (multi_time / single_time - 1) * 100
        print(f"\nMulti-pass is {slowdown:.1f}% slower")
    else:
        speedup = (single_time / multi_time - 1) * 100
        print(f"\nMulti-pass is {speedup:.1f}% faster")
    
    # Return to multi-pass branch
    subprocess.run(['git', 'checkout', 'feature/moderngl-multipass-renderer'], check=True, capture_output=True)
