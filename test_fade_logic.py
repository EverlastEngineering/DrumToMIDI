#!/usr/bin/env python3
"""Test fade logic to debug"""

from moderngl_core import calculate_note_alpha_fade

# Screen setup
strike_line_y = -0.6
screen_bottom = -1.0

# Test different note positions
test_positions = [
    (0.5, "above strike line"),
    (-0.6, "at strike line"),
    (-0.7, "slightly below"),
    (-0.8, "halfway to bottom"),
    (-1.0, "at bottom"),
]

print(f"Strike line Y: {strike_line_y}")
print(f"Screen bottom Y: {screen_bottom}")
print(f"\nNote Y -> Alpha (should fade from 1.0 to 0.2 as it goes below strike line):\n")

for y, desc in test_positions:
    alpha = calculate_note_alpha_fade(y, strike_line_y, screen_bottom)
    print(f"  Y={y:5.1f} ({desc:20s}): alpha={alpha:.2f}")
