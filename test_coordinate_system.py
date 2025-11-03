"""
Test coordinate system conversions to sanity check OpenGL vs pixel space.

This script tests all coordinate conversion functions with real values
to verify they produce correct results.
"""

import sys


def test_pixel_to_norm_conversions():
    """Test pixel to normalized coordinate conversions"""
    print("=" * 70)
    print("COORDINATE SYSTEM SANITY CHECK")
    print("=" * 70)
    print()
    
    # Test with common resolutions
    resolutions = [
        (1920, 1080),
        (1280, 720),
        (3840, 2160),
    ]
    
    for width, height in resolutions:
        print(f"\n{'='*70}")
        print(f"Testing Resolution: {width}x{height}")
        print(f"{'='*70}")
        
        # Key positions to test
        test_positions = [
            ("Top of screen", 0),
            ("25% down", height * 0.25),
            ("50% down (center)", height * 0.5),
            ("85% down (strike line)", height * 0.85),
            ("Bottom of screen", height),
        ]
        
        print("\n--- PIXEL TO NORMALIZED Y CONVERSION ---")
        print("OpenGL: Y=+1.0 is TOP, Y=-1.0 is BOTTOM")
        print("Pixels: Y=0 is TOP, Y=height is BOTTOM")
        print()
        
        for desc, pixel_y in test_positions:
            # Current formula from gpu_resident_core.py
            norm_y = 1.0 - (pixel_y / height) * 2.0
            
            print(f"{desc:30s}: pixel_y={pixel_y:6.1f} → norm_y={norm_y:+6.3f}")
            
            # Verify it makes sense
            if pixel_y == 0:
                if abs(norm_y - 1.0) > 0.001:
                    print(f"  ❌ ERROR: Top should be +1.0, got {norm_y}")
                else:
                    print(f"  ✓ Correct: Top is +1.0")
            elif pixel_y == height:
                if abs(norm_y - (-1.0)) > 0.001:
                    print(f"  ❌ ERROR: Bottom should be -1.0, got {norm_y}")
                else:
                    print(f"  ✓ Correct: Bottom is -1.0")
        
        print("\n--- NORMALIZED TO PIXEL Y CONVERSION (from shader) ---")
        
        # Test the reverse conversion from the shader
        norm_test_positions = [
            ("Top (OpenGL)", 1.0),
            ("Center (OpenGL)", 0.0),
            ("Strike line (OpenGL)", -0.7),
            ("Bottom (OpenGL)", -1.0),
        ]
        
        for desc, norm_y in norm_test_positions:
            # Shader formula: float strike_line_y_pixels = ((1.0 - u_strike_line_y_norm) / 2.0) * u_screen_size.y;
            pixel_y = ((1.0 - norm_y) / 2.0) * height
            
            print(f"{desc:30s}: norm_y={norm_y:+6.3f} → pixel_y={pixel_y:6.1f}")
            
            # Verify it makes sense
            if abs(norm_y - 1.0) < 0.001:
                if abs(pixel_y - 0) > 0.1:
                    print(f"  ❌ ERROR: +1.0 should be pixel 0 (top), got {pixel_y}")
                else:
                    print(f"  ✓ Correct: +1.0 is pixel 0 (top)")
            elif abs(norm_y - (-1.0)) < 0.001:
                if abs(pixel_y - height) > 0.1:
                    print(f"  ❌ ERROR: -1.0 should be pixel {height} (bottom), got {pixel_y}")
                else:
                    print(f"  ✓ Correct: -1.0 is pixel {height} (bottom)")
        
        print("\n--- ROUND-TRIP CONVERSION TEST ---")
        print("Test: pixel → norm → pixel (should get same value back)")
        print()
        
        for desc, original_pixel_y in test_positions:
            # Forward: pixel → norm
            norm_y = 1.0 - (original_pixel_y / height) * 2.0
            
            # Reverse: norm → pixel
            recovered_pixel_y = ((1.0 - norm_y) / 2.0) * height
            
            error = abs(original_pixel_y - recovered_pixel_y)
            status = "✓" if error < 0.01 else "❌"
            
            print(f"{status} {desc:30s}: {original_pixel_y:6.1f} → {norm_y:+6.3f} → {recovered_pixel_y:6.1f} (error: {error:.6f})")
        
        print("\n--- STRIKE LINE CALCULATION ---")
        strike_line_y = int(height * 0.85)
        strike_line_y_norm = 1.0 - (strike_line_y / height) * 2.0
        
        print(f"Strike line at 85% down:")
        print(f"  Pixel Y: {strike_line_y}")
        print(f"  Normalized Y: {strike_line_y_norm:+6.3f}")
        print(f"  Expected: approximately -0.7")
        
        if abs(strike_line_y_norm - (-0.7)) < 0.05:
            print(f"  ✓ Correct: Strike line is near -0.7")
        else:
            print(f"  ❌ ERROR: Strike line should be near -0.7, got {strike_line_y_norm}")
        
        print("\n--- NOTE FALLING BEHAVIOR ---")
        print("Testing a note that starts above screen and falls to strike line:")
        print()
        
        # Note starts 2 seconds before it hits strike line
        # With pixels_per_second = height * 0.4
        pixels_per_second = height * 0.4
        lookahead_time = 2.0  # seconds
        
        time_positions = [
            ("2.0 sec before hit (far above screen)", -2.0),
            ("1.0 sec before hit", -1.0),
            ("0.5 sec before hit", -0.5),
            ("At strike line", 0.0),
            ("0.5 sec after hit", 0.5),
            ("1.0 sec after hit", 1.0),
        ]
        
        for desc, time_delta in time_positions:
            # Note position in pixels relative to strike line
            # time_delta < 0 means note hasn't hit yet (should be ABOVE/smaller pixel_y)
            # time_delta > 0 means note has passed (should be BELOW/larger pixel_y)
            pixel_offset = time_delta * pixels_per_second
            y_pixels = strike_line_y + pixel_offset  # ADDITION! negative offset moves UP (smaller y)
            
            # Convert to normalized
            y_norm = 1.0 - (y_pixels / height) * 2.0
            
            on_screen = 0 <= y_pixels <= height
            status = "📺" if on_screen else "  "
            
            print(f"{status} {desc:40s}: time_delta={time_delta:+5.1f}s → pixel_y={y_pixels:7.1f} → norm_y={y_norm:+6.3f}")
            
            # Check if note behavior makes sense
            if time_delta < 0:  # Before hit
                if y_pixels < strike_line_y:
                    print(f"     ✓ Note is ABOVE strike line (y_pixels < {strike_line_y})")
                else:
                    print(f"     ❌ ERROR: Note should be ABOVE strike line before hit")
            elif time_delta > 0:  # After hit
                if y_pixels > strike_line_y:
                    print(f"     ✓ Note is BELOW strike line (y_pixels > {strike_line_y})")
                else:
                    print(f"     ❌ ERROR: Note should be BELOW strike line after hit")
            else:
                if abs(y_pixels - strike_line_y) < 1.0:
                    print(f"     ✓ Note is AT strike line")
                else:
                    print(f"     ❌ ERROR: Note should be at strike line")


def test_x_axis_conversion():
    """Test X-axis conversions (these should be simpler)"""
    print("\n" + "=" * 70)
    print("X-AXIS CONVERSION TEST")
    print("=" * 70)
    print()
    
    width = 1920
    
    print("OpenGL: X=-1.0 is LEFT, X=+1.0 is RIGHT")
    print("Pixels: X=0 is LEFT, X=width is RIGHT")
    print()
    
    test_x_positions = [
        ("Left edge", 0),
        ("25% from left", width * 0.25),
        ("Center", width * 0.5),
        ("75% from left", width * 0.75),
        ("Right edge", width),
    ]
    
    for desc, pixel_x in test_x_positions:
        norm_x = (pixel_x / width) * 2.0 - 1.0
        print(f"{desc:20s}: pixel_x={pixel_x:6.1f} → norm_x={norm_x:+6.3f}")
        
        if pixel_x == 0 and abs(norm_x - (-1.0)) > 0.001:
            print(f"  ❌ ERROR: Left should be -1.0, got {norm_x}")
        elif pixel_x == width and abs(norm_x - 1.0) > 0.001:
            print(f"  ❌ ERROR: Right should be +1.0, got {norm_x}")


if __name__ == "__main__":
    test_pixel_to_norm_conversions()
    test_x_axis_conversion()
    
    print("\n" + "=" * 70)
    print("SANITY CHECK COMPLETE")
    print("=" * 70)
    print()
    print("If all tests show ✓, coordinate system is correct.")
    print("If any show ❌, there are bugs in the conversion formulas.")
