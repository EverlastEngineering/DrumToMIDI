#!/usr/bin/env python3
"""
Compare PIL vs GPU rendering for the same note
"""
import sys
sys.path.insert(0, '/Users/jasoncopp/Source/GitHub/larsnet')

from midi_render_core import calculate_note_y_position

# Test parameters
width = 1920
height = 1080
pixels_per_second = height * 0.4  # 432
strike_line_y = int(height * 0.85)  # 918

# Test note
note_time = 2.0  # Note hits at 2 seconds
current_time = 0.0  # Start of video

print("=" * 60)
print("PIL RENDERER CALCULATION")
print("=" * 60)
y_pos_pil = calculate_note_y_position(note_time, current_time, strike_line_y, pixels_per_second)
print(f"Note time: {note_time}s")
print(f"Current time: {current_time}s")
print(f"Strike line: {strike_line_y} pixels")
print(f"Pixels per second: {pixels_per_second}")
print(f"Y position (PIL): {y_pos_pil:.1f} pixels")
print(f"As percentage: {y_pos_pil/height*100:.1f}% down from top")
print()

print("=" * 60)
print("GPU SHADER CALCULATION")
print("=" * 60)
# GPU shader logic
strike_line_y_norm = 1.0 - (strike_line_y / height) * 2.0
print(f"strike_line_y_norm: {strike_line_y_norm:.4f}")

# Shader converts back
strike_line_y_pixels_gpu = ((1.0 - strike_line_y_norm) / 2.0) * height
print(f"Strike line converted back: {strike_line_y_pixels_gpu:.1f} pixels")

# Calculate time_delta (opposite sign from PIL)
time_delta = current_time - note_time
print(f"time_delta: {time_delta:.1f}")

# Calculate position
pixel_offset = time_delta * pixels_per_second
print(f"pixel_offset: {pixel_offset:.1f}")

y_pixels_gpu = strike_line_y_pixels_gpu + pixel_offset
print(f"y_pixels (GPU): {y_pixels_gpu:.1f}")

# Convert to norm
y_norm = 1.0 - (y_pixels_gpu / height) * 2.0
print(f"y_norm: {y_norm:.4f}")

# This would be sent to vertex shader which renders at y_norm
# After rendering, framebuffer is flipped
# Final pixel position in output video
final_y_after_flip = height - y_pixels_gpu
print(f"After framebuffer flip: {final_y_after_flip:.1f} pixels from top")
print(f"As percentage: {final_y_after_flip/height*100:.1f}% down from top")
print()

print("=" * 60)
print("COMPARISON")
print("=" * 60)
print(f"PIL y_pos: {y_pos_pil:.1f} pixels from top")
print(f"GPU y_pos (after flip): {final_y_after_flip:.1f} pixels from top")
print(f"Match? {abs(y_pos_pil - final_y_after_flip) < 1}")
