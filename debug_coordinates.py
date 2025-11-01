#!/usr/bin/env python3
"""
Debug coordinate system to understand note falling direction
"""

from moderngl_shell import render_frame_to_file
from animation_core import build_frame_scene

# Create notes at different time positions
notes = [
    {'time': 0.0, 'lane': 'hihat', 'velocity': 100},  # At strike line
    {'time': 1.0, 'lane': 'snare', 'velocity': 100},  # 1s in future (should be above)
    {'time': -1.0, 'lane': 'kick', 'velocity': 100}, # 1s in past (should be below)
]

lanes = ['hihat', 'snare', 'kick', 'tom']

# Render at time=0.0
scene = build_frame_scene(
    notes=notes,
    current_time=0.0,
    lanes=lanes,
    strike_line_y=0.7,
    fall_speed=1.0
)

# Print positions
print("\nNote positions at current_time=0.0:")
print(f"Strike line Y: 0.7")
for i, note in enumerate(notes):
    print(f"\nNote {i+1}: time={note['time']}s, lane={note['lane']}")
    # Find this note's rectangle in scene
    for element in scene:
        if element.get('color') == (0.0, 1.0, 1.0) and i == 0:  # hihat cyan
            print(f"  Y position: {element['y']:.2f}")
            break
        elif element.get('color') == (1.0, 0.0, 0.0) and i == 1:  # snare red
            print(f"  Y position: {element['y']:.2f}")
            break
        elif element.get('color') == (1.0, 0.5, 0.0) and i == 2:  # kick orange
            print(f"  Y position: {element['y']:.2f}")
            break

print("\nExpected behavior (OpenGL: Y=+1 is TOP, Y=-1 is BOTTOM):")
print("  time=1.0 (future) → Y > 0.7 (above strike line, near top)")
print("  time=0.0 (now)    → Y = 0.7 (at strike line)")
print("  time=-1.0 (past)  → Y < 0.7 (below strike line, near bottom)")

render_frame_to_file(
    rectangles=scene,
    output_path="debug_coordinates.png",
    width=1920,
    height=1080
)

print("\n✓ Rendered debug_coordinates.png")
print("Check image: notes should fall from TOP to BOTTOM")
