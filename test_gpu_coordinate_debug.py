#!/usr/bin/env python3
"""
Debug script to trace through GPU coordinate calculations
"""

def test_coordinate_flow():
    """Test the complete flow of coordinates"""
    
    # Screen setup
    width = 1920
    height = 1080
    pixels_per_second = height * 0.4  # 432
    strike_line_y_pixels = int(height * 0.85)  # 918
    
    print("=" * 60)
    print("SCREEN SETUP")
    print("=" * 60)
    print(f"Resolution: {width}x{height}")
    print(f"Strike line: {strike_line_y_pixels} pixels (85% down)")
    print(f"Fall speed: {pixels_per_second} pixels/sec")
    print()
    
    # CPU: Convert strike line to normalized
    strike_line_y_norm = 1.0 - (strike_line_y_pixels / height) * 2.0
    print("=" * 60)
    print("CPU: STRIKE LINE CONVERSION")
    print("=" * 60)
    print(f"Pixels: {strike_line_y_pixels}")
    print(f"Formula: 1.0 - ({strike_line_y_pixels}/{height}) * 2.0")
    print(f"Normalized: {strike_line_y_norm:.4f}")
    print()
    
    # GPU: Convert back to pixels
    strike_back_to_pixels = ((1.0 - strike_line_y_norm) / 2.0) * height
    print("=" * 60)
    print("GPU: STRIKE LINE BACK TO PIXELS")
    print("=" * 60)
    print(f"Normalized: {strike_line_y_norm:.4f}")
    print(f"Formula: ((1.0 - {strike_line_y_norm:.4f}) / 2.0) * {height}")
    print(f"Pixels: {strike_back_to_pixels:.1f}")
    print(f"Match original? {abs(strike_back_to_pixels - strike_line_y_pixels) < 1}")
    print()
    
    # Test note positions at different times
    test_times = [
        ("At top (start)", -strike_line_y_pixels / pixels_per_second, 0),
        ("Halfway down", -(strike_line_y_pixels / 2) / pixels_per_second, strike_line_y_pixels / 2),
        ("At strike line", 0, strike_line_y_pixels),
        ("After strike", 0.5, strike_line_y_pixels + 0.5 * pixels_per_second),
    ]
    
    print("=" * 60)
    print("NOTE POSITION TESTS")
    print("=" * 60)
    
    for desc, time_delta, expected_y_pixels in test_times:
        pixel_offset = time_delta * pixels_per_second
        y_pixels = strike_line_y_pixels + pixel_offset
        y_norm = 1.0 - (y_pixels / height) * 2.0
        
        print(f"\n{desc}:")
        print(f"  time_delta: {time_delta:.3f} sec")
        print(f"  pixel_offset: {pixel_offset:.1f}")
        print(f"  y_pixels: {strike_line_y_pixels} + {pixel_offset:.1f} = {y_pixels:.1f}")
        print(f"  Expected: {expected_y_pixels:.1f}")
        print(f"  Match? {abs(y_pixels - expected_y_pixels) < 1}")
        print(f"  y_norm: {y_norm:.4f}")
        
        # Describe position
        if y_pixels < 0:
            print("  Position: ABOVE screen (off top)")
        elif y_pixels > height:
            print("  Position: BELOW screen (off bottom)")
        else:
            pct = (y_pixels / height) * 100
            print(f"  Position: {pct:.1f}% down from top")

if __name__ == "__main__":
    test_coordinate_flow()
