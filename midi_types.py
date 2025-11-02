"""
MIDI Data Types - Shared Contract

Defines the data contract between MIDI parsing and rendering systems.
This allows MIDI extraction to be decoupled from rendering implementation.

Type Hierarchy:
    MidiNote (base) → can be used by any renderer
    DrumNote (specialized) → includes rendering metadata (lane, color)
"""

from dataclasses import dataclass
from typing import Tuple, List, Dict, Any, Optional


@dataclass(frozen=True)
class MidiNote:
    """Pure MIDI note data - renderer-agnostic
    
    This is the minimal contract that any MIDI parser must provide.
    Contains only data directly from the MIDI file.
    
    Attributes:
        midi_note: MIDI note number (0-127)
        time: Absolute time in seconds when note should be struck
        velocity: MIDI velocity (0-127), indicates intensity
        channel: MIDI channel (0-15), typically 9 for drums
        duration: Note duration in seconds (optional, mainly for sustained notes)
    """
    midi_note: int
    time: float
    velocity: int
    channel: int = 9  # Default to drum channel
    duration: Optional[float] = None


@dataclass(frozen=True)
class DrumNote:
    """Drum note with rendering metadata
    
    Extends MIDI data with rendering-specific information like lane assignment
    and color. Used by video renderers that need spatial layout information.
    
    The lane system supports:
    - Regular lanes (0, 1, 2, ...): Standard falling note columns
    - Special lanes (negative values): Alternative rendering modes
        * lane=-1: Kick drum (screen-wide horizontal bar)
        * Future: lane=-2, -3, etc. for other special visualizations
    
    Attributes:
        midi_note: Original MIDI note number
        time: Absolute time in seconds when note should be struck
        velocity: MIDI velocity (0-127), affects brightness/intensity
        lane: Lane index for spatial positioning (negative for special rendering)
        color: RGB color tuple (0-255 per channel)
        name: Human-readable drum name (e.g., "Snare", "Hi-Hat Closed")
    """
    midi_note: int
    time: float
    velocity: int
    lane: int
    color: Tuple[int, int, int]
    name: str = ""


@dataclass(frozen=True)
class DrumMapping:
    """Defines how a MIDI note maps to a visual lane
    
    Used by drum map configuration to translate MIDI notes to rendering lanes.
    Multiple mappings can exist for the same MIDI note (e.g., different playing
    styles), allowing one MIDI note to trigger multiple visual elements.
    
    Attributes:
        name: Human-readable name (e.g., "Snare", "Hi-Hat Closed")
        lane: Target lane index (negative for special rendering modes)
        color: RGB color for this drum element
    """
    name: str
    lane: int
    color: Tuple[int, int, int]


# Type alias for drum map structure
# Maps MIDI note number → list of drum mappings
# List allows one MIDI note to produce multiple visual elements
DrumMapDict = Dict[int, List[Dict[str, Any]]]


@dataclass(frozen=True)
class MidiSequence:
    """Complete MIDI sequence with metadata
    
    Container for a parsed MIDI file, including all notes and timing information.
    Provides everything needed for rendering or further processing.
    
    Attributes:
        notes: List of notes (MidiNote or DrumNote depending on processing)
        duration: Total duration in seconds
        tempo_map: List of (time, tempo_bpm) tuples for tempo changes
        ticks_per_beat: MIDI ticks per quarter note (resolution)
        time_signature: (numerator, denominator) tuple, e.g., (4, 4)
    """
    notes: List[Any]  # List[MidiNote] or List[DrumNote]
    duration: float
    tempo_map: List[Tuple[float, float]] = None  # (time_seconds, bpm)
    ticks_per_beat: int = 480
    time_signature: Tuple[int, int] = (4, 4)
    
    def __post_init__(self):
        """Ensure tempo_map is initialized"""
        if self.tempo_map is None:
            # Default 120 BPM for entire sequence
            object.__setattr__(self, 'tempo_map', [(0.0, 120.0)])


# ============================================================================
# Conversion Functions
# ============================================================================

def midi_note_to_drum_note(
    midi_note: MidiNote,
    drum_mapping: DrumMapping
) -> DrumNote:
    """Convert MidiNote to DrumNote using drum mapping
    
    Args:
        midi_note: Pure MIDI note data
        drum_mapping: Drum mapping with lane and color info
    
    Returns:
        DrumNote with rendering metadata
    """
    return DrumNote(
        midi_note=midi_note.midi_note,
        time=midi_note.time,
        velocity=midi_note.velocity,
        lane=drum_mapping.lane,
        color=drum_mapping.color,
        name=drum_mapping.name
    )


def drum_note_to_dict(note: DrumNote) -> Dict[str, Any]:
    """Convert DrumNote to dictionary format
    
    Useful for compatibility with code expecting dict-based notes.
    Used by moderngl_renderer which currently uses dicts.
    
    Args:
        note: DrumNote instance
    
    Returns:
        Dictionary with note data
    """
    return {
        'midi_note': note.midi_note,
        'time': note.time,
        'velocity': note.velocity,
        'lane': note.lane,
        'color': note.color,
        'name': note.name
    }


def dict_to_drum_note(data: Dict[str, Any]) -> DrumNote:
    """Convert dictionary to DrumNote
    
    Args:
        data: Dictionary with note fields
    
    Returns:
        DrumNote instance
    """
    return DrumNote(
        midi_note=data.get('midi_note', 0),
        time=data['time'],
        velocity=data['velocity'],
        lane=data.get('lane', 0),
        color=data.get('color', (255, 255, 255)),
        name=data.get('name', '')
    )


# ============================================================================
# Validation Functions
# ============================================================================

def validate_midi_note(note: MidiNote) -> bool:
    """Validate MidiNote fields are within spec
    
    Args:
        note: MidiNote to validate
    
    Returns:
        True if valid, raises ValueError if invalid
    """
    if not (0 <= note.midi_note <= 127):
        raise ValueError(f"MIDI note {note.midi_note} out of range [0, 127]")
    
    if note.time < 0:
        raise ValueError(f"Note time {note.time} must be non-negative")
    
    if not (0 <= note.velocity <= 127):
        raise ValueError(f"Velocity {note.velocity} out of range [0, 127]")
    
    if not (0 <= note.channel <= 15):
        raise ValueError(f"Channel {note.channel} out of range [0, 15]")
    
    if note.duration is not None and note.duration < 0:
        raise ValueError(f"Duration {note.duration} must be non-negative")
    
    return True


def validate_drum_note(note: DrumNote) -> bool:
    """Validate DrumNote fields
    
    Args:
        note: DrumNote to validate
    
    Returns:
        True if valid, raises ValueError if invalid
    """
    if not (0 <= note.midi_note <= 127):
        raise ValueError(f"MIDI note {note.midi_note} out of range [0, 127]")
    
    if note.time < 0:
        raise ValueError(f"Note time {note.time} must be non-negative")
    
    if not (0 <= note.velocity <= 127):
        raise ValueError(f"Velocity {note.velocity} out of range [0, 127]")
    
    if len(note.color) != 3:
        raise ValueError(f"Color must be RGB tuple, got {note.color}")
    
    if not all(0 <= c <= 255 for c in note.color):
        raise ValueError(f"Color values must be in range [0, 255], got {note.color}")
    
    return True


# ============================================================================
# Standard GM Drum Map
# ============================================================================

# Standard General MIDI drum map
# This can be overridden by loading from config files
STANDARD_GM_DRUM_MAP: DrumMapDict = {
    # Hi-hats
    42: [{"name": "Hi-Hat Closed", "lane": 0, "color": (0, 255, 255)}],  # Cyan
    44: [{"name": "Hi-Hat Foot Close", "lane": 0, "color": (15, 128, 40)}],  # Dark cyan
    46: [{"name": "Hi-Hat Open", "lane": 1, "color": (30, 255, 80)}],  # Light blue
    
    # Snares
    38: [{"name": "Snare", "lane": 2, "color": (255, 0, 0)}],  # Red
    40: [{"name": "Snare Rim", "lane": 2, "color": (255, 0, 255)}],  # Magenta
    
    # Other percussion
    39: [{"name": "Clap", "lane": 3, "color": (255, 128, 128)}],  # Light red
    
    # Cymbals
    49: [{"name": "Left Cymbal", "lane": 4, "color": (0, 80, 255)}],  # Dark orange
    57: [{"name": "Right Cymbal", "lane": 8, "color": (0, 100, 255)}],  # Orange
    51: [{"name": "Ride", "lane": 9, "color": (100, 150, 250)}],  # Light orange
    
    # Toms
    47: [{"name": "Tom 1", "lane": 5, "color": (0, 255, 0)}],  # Green
    48: [{"name": "Tom 2", "lane": 6, "color": (0, 150, 0)}],  # Dark green
    50: [{"name": "Tom 3", "lane": 7, "color": (140, 0, 140)}],  # Magenta
    
    # Kick drum - special rendering (screen-wide bar)
    36: [{"name": "Kick", "lane": -1, "color": (255, 140, 90)}],  # Yellow/orange
}
