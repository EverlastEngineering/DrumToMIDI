"""
Text Overlay Generation - Functional Core

Pure functions for generating text overlays (lane labels).
Renders text using PIL, returns PIL Image with alpha channel.

The imperative shell (midi_video_shell.py) handles uploading to GPU texture.
"""

from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict


def create_lane_labels_overlay(
    width: int,
    height: int,
    drum_map: Dict[int, List[Dict]],
    num_lanes: int,
    drum_notes: List = None,
    font_size: int = 18,
    y_start: float = 0.08
) -> Image.Image:
    """Create text overlay showing drum names for each lane
    
    Pure function that generates a PIL Image with lane labels.
    Each lane shows all drum types that can appear in it, stacked vertically.
    Text is colored to match the drum color.
    Only shows drums that actually appear in the MIDI.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        drum_map: Drum mapping dictionary (STANDARD_GM_DRUM_MAP format)
        num_lanes: Number of lanes to label
        drum_notes: List of drum notes from MIDI (to filter unused drums)
        font_size: Font size in pixels
        y_start: Y position to start labels (normalized 0-1, 0=bottom, 1=top)
    
    Returns:
        PIL Image (RGBA) with transparent background and colored text labels
    
    Examples:
        >>> overlay = create_lane_labels_overlay(1920, 1080, STANDARD_GM_DRUM_MAP, 3, notes)
        >>> overlay.size
        (1920, 1080)
        >>> overlay.mode
        'RGBA'
    """
    # Create transparent image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Load font
    font = _load_font(font_size)
    
    # Get set of MIDI notes that actually appear in the song
    midi_notes_in_use = set()
    if drum_notes:
        midi_notes_in_use = {note.midi_note for note in drum_notes}
    
    # Group drums by lane, filtering by notes in use
    lane_drums = _group_drums_by_lane(drum_map, num_lanes, midi_notes_in_use)
    
    # Calculate lane positions
    lane_width = width / num_lanes
    
    # Draw labels for each lane
    for lane_idx in range(num_lanes):
        if lane_idx not in lane_drums:
            continue
        
        drums = lane_drums[lane_idx]
        
        # Start Y position (from top, accounting for progress bar)
        y_pos = int(height * y_start)
        
        # Draw each drum label in this lane
        for drum_name, drum_color in drums:
            # Convert to uppercase
            drum_name = drum_name.upper()
            
            # Calculate text size
            bbox = draw.textbbox((0, 0), drum_name, font=font)
            text_height = bbox[3] - bbox[1]
            
            # Left-align text in lane (with small padding from left edge)
            lane_left = lane_idx * lane_width
            x_pos = int(lane_left + 15)  # 15px padding from left edge
            
            # Draw text shadow for readability
            draw.text(
                (x_pos + 1, y_pos + 1),
                drum_name,
                font=font,
                fill=(0, 0, 0, 180)  # Semi-transparent black shadow
            )
            
            # Draw colored text
            draw.text(
                (x_pos, y_pos),
                drum_name,
                font=font,
                fill=(*drum_color, 255)  # Full opacity colored text
            )
            
            # Move down for next label
            y_pos += text_height + 12  # 12px spacing between labels
    
    return img


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load Space Grotesk font or fall back to system fonts
    
    Args:
        size: Font size in pixels
    
    Returns:
        PIL FreeTypeFont object
    """
    from pathlib import Path
    
    # Try Space Grotesk first (bundled with project)
    script_dir = Path(__file__).parent
    space_grotesk_path = script_dir / 'SpaceGrotesk-Bold.ttf'
    
    font_paths = [
        str(space_grotesk_path),  # Bundled Space Grotesk
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',  # macOS
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux
        'C:\\Windows\\Fonts\\arialbd.ttf',  # Windows
    ]
    
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue
    
    # Fall back to default font
    return ImageFont.load_default()


def _group_drums_by_lane(
    drum_map: Dict[int, List[Dict]],
    num_lanes: int,
    midi_notes_in_use: set = None
) -> Dict[int, List[Tuple[str, Tuple[int, int, int]]]]:
    """Group drum mappings by lane number
    
    Args:
        drum_map: Drum mapping dictionary
        num_lanes: Number of lanes to include
        midi_notes_in_use: Set of MIDI note numbers that appear in the song (for filtering)
    
    Returns:
        Dictionary mapping lane_idx -> list of (drum_name, rgb_color) tuples
    
    Examples:
        >>> drums = _group_drums_by_lane(STANDARD_GM_DRUM_MAP, 3, {42, 38})
        >>> 0 in drums  # Lane 0 has hi-hats
        True
        >>> drums[0][0][0]  # First drum name in lane 0
        'Hi-Hat Closed'
    """
    lane_drums = defaultdict(list)
    
    for midi_note, mappings in drum_map.items():
        # Skip drums that don't appear in the MIDI
        if midi_notes_in_use is not None and midi_note not in midi_notes_in_use:
            continue
            
        for mapping in mappings:
            lane = mapping['lane']
            
            # Only include regular lanes (non-negative)
            if 0 <= lane < num_lanes:
                name = mapping['name']
                color = mapping['color']
                lane_drums[lane].append((name, color))
    
    return dict(lane_drums)
