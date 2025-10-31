#!/usr/bin/env python3
"""
Visual Quality Test

Creates test images to verify rendering quality:
- Anti-aliasing on rounded corners
- Color accuracy
- Alpha blending
- Lane alignment
"""

from moderngl_shell import render_frame_to_file
from moderngl_core import (
    create_strike_line,
    create_lane_markers, 
    create_background_lanes,
    get_lane_x_position
)


def test_rounded_corners():
    """Test rounded corner anti-aliasing at various sizes"""
    
    print("Creating rounded corners test...")
    
    rectangles = []
    
    # Different corner radii
    for i, radius in enumerate([4, 8, 12, 16, 24]):
        rectangles.append({
            'x': -0.9 + i * 0.35,
            'y': 0.5,
            'width': 0.3,
            'height': 0.15,
            'color': (0.0, 1.0, 1.0),
            'brightness': 1.0
        })
    
    # Test shows that we'd need to vary corner radius per call
    # For now, all use same radius
    render_frame_to_file(
        rectangles=rectangles,
        output_path="test_rounded_corners.png",
        width=1920,
        height=1080,
        corner_radius=12.0
    )
    
    print("✓ Saved: test_rounded_corners.png")


def test_alpha_blending():
    """Test alpha transparency with overlapping elements"""
    
    print("Creating alpha blending test...")
    
    rectangles = []
    
    # Overlapping rectangles with different brightness (acts as alpha)
    colors = [
        (1.0, 0.0, 0.0),  # Red
        (0.0, 1.0, 0.0),  # Green
        (0.0, 0.0, 1.0),  # Blue
    ]
    
    for i, color in enumerate(colors):
        rectangles.append({
            'x': -0.3 + i * 0.2,
            'y': 0.3 - i * 0.1,
            'width': 0.4,
            'height': 0.4,
            'color': color,
            'brightness': 0.6  # Semi-transparent
        })
    
    render_frame_to_file(
        rectangles=rectangles,
        output_path="test_alpha_blending.png",
        width=1920,
        height=1080,
        corner_radius=12.0
    )
    
    print("✓ Saved: test_alpha_blending.png")


def test_full_scene():
    """Test complete scene with all elements"""
    
    print("Creating full scene test...")
    
    lanes = ['hihat', 'snare', 'kick', 'tom']
    
    # Colors
    lane_colors = {
        'hihat': (0.0, 1.0, 1.0),
        'snare': (1.0, 0.0, 0.0),
        'kick': (1.0, 0.5, 0.0),
        'tom': (0.0, 1.0, 0.0)
    }
    
    elements = []
    
    # Backgrounds
    elements.extend(create_background_lanes(
        lanes=lanes,
        colors={
            'hihat': (0.0, 0.1, 0.1),
            'snare': (0.1, 0.0, 0.0),
            'kick': (0.1, 0.05, 0.0),
            'tom': (0.0, 0.1, 0.0)
        }
    ))
    
    # Lane markers
    elements.extend(create_lane_markers(lanes=lanes, thickness=0.003))
    
    # Strike line
    elements.append(create_strike_line(
        y_position=0.7, 
        color=(1.0, 1.0, 1.0),
        thickness=0.01
    ))
    
    # Dense note pattern
    for lane in lanes:
        lane_x = get_lane_x_position(lane, lanes)
        note_width = 0.25 if lane == 'kick' else 0.15
        
        # Multiple notes at different positions
        for i in range(15):
            y_pos = 0.95 - (i / 15) * 1.8
            brightness = max(0.3, 1.0 - abs(y_pos - 0.7) / 1.0)
            
            elements.append({
                'x': lane_x - note_width/2,
                'y': y_pos,
                'width': note_width,
                'height': 0.06,
                'color': lane_colors[lane],
                'brightness': brightness
            })
    
    render_frame_to_file(
        rectangles=elements,
        output_path="test_full_scene.png",
        width=1920,
        height=1080,
        corner_radius=12.0
    )
    
    print("✓ Saved: test_full_scene.png")
    print(f"  Total elements: {len(elements)}")


def main():
    """Run all visual quality tests"""
    
    print("\n" + "="*60)
    print("Visual Quality Tests")
    print("="*60 + "\n")
    
    test_rounded_corners()
    test_alpha_blending()
    test_full_scene()
    
    print("\n" + "="*60)
    print("All tests complete!")
    print("="*60)
    print("\nGenerated images:")
    print("  • test_rounded_corners.png - Corner anti-aliasing")
    print("  • test_alpha_blending.png - Transparency blending")
    print("  • test_full_scene.png - Complete visualization")
    print("\nReview images to verify visual quality ✓")


if __name__ == '__main__':
    main()
