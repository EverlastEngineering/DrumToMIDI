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
from moderngl_renderer.shell import render_frame_to_file


# Shaders and rendering logic now in moderngl_shell.py
# This POC demonstrates the high-level API


def main():
    """Phase 2 complete: Render with strike line, lane markers, and notes"""
    print("\n" + "="*60)
    print("ModernGL Renderer - Phase 2: Complete Visualization")
    print("="*60 + "\n")
    
    try:
        from moderngl_renderer.core import (
            create_strike_line, 
            create_lane_markers,
            create_background_lanes,
            get_lane_x_position
        )
        
        # Define lanes
        lanes = ['hihat', 'snare', 'kick', 'tom']
        
        # Define note colors (matching drum visualization)
        HIHAT_COLOR = (0.0, 1.0, 1.0)    # Cyan
        SNARE_COLOR = (1.0, 0.0, 0.0)    # Red
        KICK_COLOR = (1.0, 0.5, 0.0)     # Orange
        TOM_COLOR = (0.0, 1.0, 0.0)      # Green
        
        print("Building scene (functional core)...")
        
        # Create background lanes
        backgrounds = create_background_lanes(
            lanes=lanes,
            colors={
                'hihat': (0.0, 0.1, 0.1),
                'snare': (0.1, 0.0, 0.0),
                'kick': (0.1, 0.05, 0.0),
                'tom': (0.0, 0.1, 0.0)
            },
            brightness=0.3
        )
        
        # Create lane dividers
        lane_markers = create_lane_markers(
            lanes=lanes,
            color=(0.3, 0.3, 0.3),
            thickness=0.003
        )
        
        # Create strike line
        strike_line = create_strike_line(
            y_position=0.7,
            color=(1.0, 1.0, 1.0),
            thickness=0.008
        )
        
        # Create notes positioned in lanes
        notes = []
        for i, (lane, color) in enumerate([
            ('hihat', HIHAT_COLOR),
            ('snare', SNARE_COLOR),
            ('kick', KICK_COLOR),
            ('tom', TOM_COLOR)
        ]):
            lane_x = get_lane_x_position(lane, lanes)
            note_width = 0.25 if lane == 'kick' else 0.15
            
            # Multiple notes per lane at different heights
            notes.extend([
                {
                    'x': lane_x - note_width/2, 
                    'y': 0.9 - i*0.05, 
                    'width': note_width, 
                    'height': 0.06,
                    'color': color, 
                    'brightness': 1.0
                },
                {
                    'x': lane_x - note_width/2, 
                    'y': 0.5 - i*0.04, 
                    'width': note_width, 
                    'height': 0.06,
                    'color': color, 
                    'brightness': 0.8
                },
                {
                    'x': lane_x - note_width/2, 
                    'y': 0.0 - i*0.03, 
                    'width': note_width, 
                    'height': 0.06,
                    'color': color, 
                    'brightness': 0.5
                },
            ])
        
        # Combine all elements in render order (back to front)
        all_elements = backgrounds + lane_markers + [strike_line] + notes
        
        # Render to file using high-level API (imperative shell)
        output_file = "moderngl_phase2_complete.png"
        print(f"Rendering complete scene to GPU (imperative shell)...")
        print(f"  - {len(backgrounds)} lane backgrounds")
        print(f"  - {len(lane_markers)} lane dividers")
        print(f"  - 1 strike line")
        print(f"  - {len(notes)} notes")
        print(f"  - Total: {len(all_elements)} elements in 1 draw call")
        
        render_frame_to_file(
            rectangles=all_elements,
            output_path=output_file,
            width=1920,
            height=1080,
            corner_radius=12.0
        )
        
        print("\n" + "="*60)
        print("SUCCESS! Phase 2 COMPLETE:")
        print("  ✓ Lane backgrounds with subtle colors")
        print("  ✓ Lane divider markers")
        print("  ✓ Strike line visualization")
        print("  ✓ Notes aligned to lanes")
        print("  ✓ All elements in single draw call")
        print("  ✓ Functional core/imperative shell architecture")
        print(f"\nCheck output: {output_file}")
        print("="*60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
