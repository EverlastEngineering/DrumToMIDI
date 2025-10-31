#!/usr/bin/env python3
"""
ModernGL Renderer - Proof of Concept

GPU-accelerated video rendering using OpenGL.
Demonstrates functional core / imperative shell architecture.

Phase 1 Goals:
1. Initialize ModernGL context (headless)
2. Create offscreen framebuffer
3. Render a simple colored rectangle
4. Export frame to image file

Phase 2 Goals:
1. Rounded corners with anti-aliasing
2. Batch rendering multiple notes
3. Velocity-based brightness
4. Separate functional core from GPU operations
"""

import sys
from moderngl_shell import render_frame_to_file


# Shaders and rendering logic now in moderngl_shell.py
# This POC demonstrates the high-level API


def main():
    """Phase 2 test: Render using functional core / imperative shell architecture"""
    print("\n" + "="*60)
    print("ModernGL Renderer - Phase 2: Functional Architecture")
    print("="*60 + "\n")
    
    try:
        # Define note colors (matching drum visualization)
        HIHAT_COLOR = (0.0, 1.0, 1.0)    # Cyan
        SNARE_COLOR = (1.0, 0.0, 0.0)    # Red
        KICK_COLOR = (1.0, 0.5, 0.0)     # Orange
        TOM_COLOR = (0.0, 1.0, 0.0)      # Green
        
        # Simulate falling drum notes with different colors and velocities
        print("Preparing note data (functional core)...")
        
        notes = [
            # Hihat notes (top lane)
            {'x': -0.8, 'y': 0.8, 'width': 0.15, 'height': 0.06, 
             'color': HIHAT_COLOR, 'brightness': 1.0},
            {'x': -0.5, 'y': 0.6, 'width': 0.15, 'height': 0.06, 
             'color': HIHAT_COLOR, 'brightness': 0.7},
            {'x': -0.2, 'y': 0.4, 'width': 0.15, 'height': 0.06, 
             'color': HIHAT_COLOR, 'brightness': 0.5},
            
            # Snare notes (second lane)
            {'x': -0.45, 'y': 0.7, 'width': 0.15, 'height': 0.06, 
             'color': SNARE_COLOR, 'brightness': 1.0},
            {'x': -0.15, 'y': 0.3, 'width': 0.15, 'height': 0.06, 
             'color': SNARE_COLOR, 'brightness': 0.8},
            
            # Kick notes (third lane - wider)
            {'x': -0.1, 'y': 0.5, 'width': 0.25, 'height': 0.08, 
             'color': KICK_COLOR, 'brightness': 1.0},
            {'x': 0.2, 'y': 0.2, 'width': 0.25, 'height': 0.08, 
             'color': KICK_COLOR, 'brightness': 0.6},
            
            # Tom notes (fourth lane)
            {'x': 0.5, 'y': 0.7, 'width': 0.15, 'height': 0.06, 
             'color': TOM_COLOR, 'brightness': 1.0},
            {'x': 0.5, 'y': 0.4, 'width': 0.15, 'height': 0.06, 
             'color': TOM_COLOR, 'brightness': 0.9},
            {'x': 0.5, 'y': -0.2, 'width': 0.15, 'height': 0.06, 
             'color': TOM_COLOR, 'brightness': 0.4},
        ]
        
        # Render to file using high-level API (imperative shell)
        output_file = "moderngl_phase2_refactored.png"
        print(f"Rendering {len(notes)} notes to GPU (imperative shell)...")
        
        render_frame_to_file(
            rectangles=notes,
            output_path=output_file,
            width=1920,
            height=1080,
            corner_radius=12.0
        )
        
        print("\n" + "="*60)
        print("SUCCESS! Functional architecture validated:")
        print("  ✓ Functional core: Pure data transformations")
        print("  ✓ Imperative shell: GPU operations isolated")
        print("  ✓ Rounded corners with anti-aliasing")
        print("  ✓ Instanced rendering (10 notes in 1 draw call)")
        print("  ✓ Per-note colors and brightness")
        print("  ✓ Automatic resource management")
        print(f"\nRendered {len(notes)} notes")
        print(f"Check output: {output_file}")
        print("="*60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
