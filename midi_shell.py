"""
MIDI Shell - Imperative Shell

Handles file I/O and side effects for MIDI parsing.
Loads MIDI files and delegates to pure functions in midi_core.py.

This is the "shell" that wraps the functional "core".
"""

import mido  # type: ignore
from typing import List, Tuple
from pathlib import Path

from midi_types import DrumNote, MidiSequence, DrumMapDict
from midi_core import (
    process_midi_data_to_drum_notes,
    process_midi_data_to_sequence
)


# ============================================================================
# File Loading (Imperative Shell)
# ============================================================================

def load_midi_file(midi_path: str) -> mido.MidiFile:
    """Load MIDI file from disk
    
    Imperative shell: performs file I/O.
    
    Args:
        midi_path: Path to MIDI file
    
    Returns:
        Loaded mido.MidiFile object
    
    Raises:
        FileNotFoundError: If MIDI file doesn't exist
        IOError: If file can't be read
    """
    path = Path(midi_path)
    if not path.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")
    
    try:
        return mido.MidiFile(midi_path)
    except Exception as e:
        raise IOError(f"Failed to load MIDI file: {e}")


# ============================================================================
# High-Level Parsing (Shell wrapping Core)
# ============================================================================

def parse_midi_file(
    midi_path: str,
    drum_map: DrumMapDict = None,
    tail_duration: float = 3.0,
    channel_filter: int = None
) -> Tuple[List[DrumNote], float]:
    """Parse MIDI file into drum notes
    
    Imperative shell: loads file, then delegates to pure functions.
    
    Args:
        midi_path: Path to MIDI file
        drum_map: Drum mapping dictionary (required for drum notes)
        tail_duration: Extra seconds to add at end for notes to fall off screen
        channel_filter: Optional channel filter
    
    Returns:
        (drum_notes, total_duration) tuple
    
    Raises:
        FileNotFoundError: If MIDI file doesn't exist
        ValueError: If drum_map is not provided
    """
    if drum_map is None:
        raise ValueError("drum_map is required for parsing to DrumNotes")
    
    # IMPERATIVE: Load file from disk
    midi_file = load_midi_file(midi_path)
    
    # FUNCTIONAL: Process the loaded data
    return process_midi_data_to_drum_notes(
        tracks=midi_file.tracks,
        ticks_per_beat=midi_file.ticks_per_beat,
        drum_map=drum_map,
        tail_duration=tail_duration,
        channel_filter=channel_filter
    )


def parse_midi_to_sequence(
    midi_path: str,
    drum_map: DrumMapDict = None
) -> MidiSequence:
    """Parse MIDI file into a complete MidiSequence object
    
    Imperative shell: loads file, then delegates to pure functions.
    
    Args:
        midi_path: Path to MIDI file
        drum_map: Optional drum mapping for creating DrumNotes
    
    Returns:
        MidiSequence with all metadata
    
    Raises:
        FileNotFoundError: If MIDI file doesn't exist
    """
    # IMPERATIVE: Load file from disk
    midi_file = load_midi_file(midi_path)
    
    # FUNCTIONAL: Process the loaded data
    return process_midi_data_to_sequence(
        tracks=midi_file.tracks,
        ticks_per_beat=midi_file.ticks_per_beat,
        drum_map=drum_map
    )


# ============================================================================
# Convenience Functions
# ============================================================================

def validate_midi_file(midi_path: str) -> bool:
    """Check if a file is a valid MIDI file
    
    Imperative shell: performs file I/O.
    
    Args:
        midi_path: Path to check
    
    Returns:
        True if valid MIDI file, False otherwise
    """
    try:
        load_midi_file(midi_path)
        return True
    except (FileNotFoundError, IOError):
        return False
