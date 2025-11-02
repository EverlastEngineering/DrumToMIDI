"""
MIDI Parser - Backwards Compatibility Wrapper

This module re-exports functions from midi_core.py and midi_shell.py
for backwards compatibility. New code should import from those modules directly.

DEPRECATED: Use midi_core.py (pure functions) and midi_shell.py (I/O) instead.
"""

# Re-export shell functions (public API)
from midi_shell import (
    parse_midi_file,
    parse_midi_to_sequence,
    load_midi_file,
    validate_midi_file
)

# Re-export commonly used core functions
from midi_core import (
    tempo_to_bpm,
    build_tempo_map_from_tracks as build_tempo_map,
    extract_midi_notes_from_tracks as extract_midi_notes,
    map_midi_notes_to_drums as map_midi_to_drums
)

# All implementation moved to midi_core.py and midi_shell.py
# This file now only provides backwards compatibility imports

__all__ = [
    # Shell functions (public API)
    'parse_midi_file',
    'parse_midi_to_sequence',
    'load_midi_file',
    'validate_midi_file',
    # Core functions (for advanced usage)
    'tempo_to_bpm',
    'build_tempo_map',
    'extract_midi_notes',
    'map_midi_to_drums',
]
