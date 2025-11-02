"""
MIDI Core - Functional Core

Pure functions for MIDI data transformations.
No side effects, no I/O - only calculations and data processing.

All functions take data as input and return transformed data.
File I/O is handled by midi_shell.py.
"""

import mido  # type: ignore
from typing import List, Tuple, Dict, Any
from midi_types import MidiNote, DrumNote, MidiSequence, DrumMapDict


# ============================================================================
# Tempo Calculations
# ============================================================================

def tempo_to_bpm(tempo_microseconds: int) -> float:
    """Convert MIDI tempo (microseconds per beat) to BPM
    
    Pure function: mathematical conversion only.
    
    Args:
        tempo_microseconds: Tempo in microseconds per quarter note
    
    Returns:
        Tempo in beats per minute
    """
    return 60_000_000 / tempo_microseconds


def bpm_to_tempo(bpm: float) -> int:
    """Convert BPM to MIDI tempo (microseconds per beat)
    
    Pure function: mathematical conversion only.
    
    Args:
        bpm: Beats per minute
    
    Returns:
        Tempo in microseconds per quarter note
    """
    return int(60_000_000 / bpm)


# ============================================================================
# Tempo Map Building
# ============================================================================

def build_tempo_map_from_tracks(
    tracks: List[Any],
    ticks_per_beat: int
) -> List[Tuple[float, int]]:
    """Build global tempo map from MIDI tracks
    
    Pure function: processes track data structure, no file I/O.
    Critical for Type 1 MIDI files where Track 0 contains tempo
    but notes are in other tracks.
    
    Args:
        tracks: List of mido Track objects (already loaded)
        ticks_per_beat: MIDI ticks per quarter note
    
    Returns:
        List of (absolute_time_seconds, tempo_microseconds) tuples, sorted by time
    """
    tempo_map = []
    
    for track in tracks:
        absolute_time = 0.0
        current_tempo = 500000  # Default 120 BPM
        
        for msg in track:
            # Update absolute time BEFORE processing the message
            if msg.time > 0:
                absolute_time += mido.tick2second(
                    msg.time, 
                    ticks_per_beat, 
                    current_tempo
                )
            
            if msg.type == 'set_tempo':
                # Record this tempo change
                tempo_map.append((absolute_time, msg.tempo))
                current_tempo = msg.tempo
    
    # Sort tempo map by time and remove duplicates
    tempo_map.sort()
    if not tempo_map:
        tempo_map = [(0.0, 500000)]  # Default to 120 BPM if no tempo found
    
    # Remove duplicate tempo changes at same time (keep last one)
    unique_tempo_map = []
    for i, (time, tempo) in enumerate(tempo_map):
        if i == 0 or abs(time - tempo_map[i-1][0]) > 0.001:
            unique_tempo_map.append((time, tempo))
        else:
            # Replace previous if at same time
            unique_tempo_map[-1] = (time, tempo)
    
    return unique_tempo_map


def convert_tempo_map_to_bpm(
    tempo_map: List[Tuple[float, int]]
) -> List[Tuple[float, float]]:
    """Convert tempo map from microseconds to BPM
    
    Pure function: data transformation only.
    
    Args:
        tempo_map: List of (time, tempo_microseconds) tuples
    
    Returns:
        List of (time, bpm) tuples
    """
    return [(time, tempo_to_bpm(tempo)) for time, tempo in tempo_map]


# ============================================================================
# Note Extraction
# ============================================================================

def extract_midi_notes_from_tracks(
    tracks: List[Any],
    ticks_per_beat: int,
    tempo_map: List[Tuple[float, int]],
    channel_filter: int = None
) -> Tuple[List[MidiNote], float]:
    """Extract raw MIDI notes from tracks
    
    Pure function: processes track data structure, no file I/O.
    
    Args:
        tracks: List of mido Track objects (already loaded)
        ticks_per_beat: MIDI ticks per quarter note
        tempo_map: Tempo map from build_tempo_map_from_tracks()
        channel_filter: Only extract notes from this channel (None = all channels)
    
    Returns:
        (notes, total_duration) tuple
    """
    notes = []
    total_duration = 0.0
    
    for track in tracks:
        absolute_time = 0.0
        tempo_idx = 0
        current_tempo = tempo_map[0][1]
        
        for msg in track:
            # Check if we need to advance to next tempo change
            while (tempo_idx + 1 < len(tempo_map) and 
                   absolute_time >= tempo_map[tempo_idx + 1][0] - 0.001):
                tempo_idx += 1
                current_tempo = tempo_map[tempo_idx][1]
            
            # Calculate time delta and add to absolute time
            if msg.time > 0:
                absolute_time += mido.tick2second(
                    msg.time,
                    ticks_per_beat,
                    current_tempo
                )
            
            if msg.type == 'note_on' and msg.velocity > 0:
                # Apply channel filter if specified
                if channel_filter is not None and msg.channel != channel_filter:
                    continue
                
                note = MidiNote(
                    midi_note=msg.note,
                    time=absolute_time,
                    velocity=msg.velocity,
                    channel=msg.channel
                )
                notes.append(note)
                total_duration = max(total_duration, absolute_time)
    
    # Sort by time
    notes.sort(key=lambda n: n.time)
    
    return notes, total_duration


# ============================================================================
# Drum Mapping
# ============================================================================

def map_midi_notes_to_drums(
    midi_notes: List[MidiNote],
    drum_map: DrumMapDict
) -> List[DrumNote]:
    """Map MIDI notes to drum notes with rendering metadata
    
    Pure function: data transformation only.
    
    Args:
        midi_notes: Raw MIDI notes from extract_midi_notes_from_tracks()
        drum_map: Dictionary mapping MIDI note numbers to drum info
    
    Returns:
        List of DrumNote objects with lane and color assignments
    """
    drum_notes = []
    
    for midi_note in midi_notes:
        if midi_note.midi_note in drum_map:
            # Create a note for each lane definition (most have 1, some have multiple)
            for drum_info in drum_map[midi_note.midi_note]:
                drum_note = DrumNote(
                    midi_note=midi_note.midi_note,
                    time=midi_note.time,
                    velocity=midi_note.velocity,
                    lane=drum_info["lane"],
                    color=drum_info["color"],
                    name=drum_info["name"]
                )
                drum_notes.append(drum_note)
    
    # Sort by time
    drum_notes.sort(key=lambda n: n.time)
    
    return drum_notes


# ============================================================================
# Time Signature Extraction
# ============================================================================

def extract_time_signature_from_tracks(
    tracks: List[Any]
) -> Tuple[int, int]:
    """Extract time signature from tracks
    
    Pure function: searches track data structure.
    
    Args:
        tracks: List of mido Track objects
    
    Returns:
        (numerator, denominator) tuple, defaults to (4, 4)
    """
    for track in tracks:
        for msg in track:
            if msg.type == 'time_signature':
                return (msg.numerator, msg.denominator)
    
    return (4, 4)  # Default


# ============================================================================
# High-Level Orchestration (Pure)
# ============================================================================

def process_midi_data_to_drum_notes(
    tracks: List[Any],
    ticks_per_beat: int,
    drum_map: DrumMapDict,
    tail_duration: float = 3.0,
    channel_filter: int = None
) -> Tuple[List[DrumNote], float]:
    """Process MIDI track data into drum notes
    
    Pure function: orchestrates other pure functions.
    Takes already-loaded MIDI data, returns processed notes.
    
    Args:
        tracks: List of mido Track objects (already loaded)
        ticks_per_beat: MIDI ticks per quarter note
        drum_map: Drum mapping dictionary
        tail_duration: Extra seconds to add at end
        channel_filter: Optional channel filter
    
    Returns:
        (drum_notes, total_duration) tuple
    """
    # Build tempo map
    tempo_map = build_tempo_map_from_tracks(tracks, ticks_per_beat)
    
    # Extract raw MIDI notes
    midi_notes, duration = extract_midi_notes_from_tracks(
        tracks, 
        ticks_per_beat, 
        tempo_map, 
        channel_filter
    )
    
    # Map to drum notes
    drum_notes = map_midi_notes_to_drums(midi_notes, drum_map)
    
    # Add tail duration
    total_duration = duration + tail_duration
    
    return drum_notes, total_duration


def process_midi_data_to_sequence(
    tracks: List[Any],
    ticks_per_beat: int,
    drum_map: DrumMapDict = None
) -> MidiSequence:
    """Process MIDI track data into a MidiSequence
    
    Pure function: orchestrates other pure functions.
    Takes already-loaded MIDI data, returns structured sequence.
    
    Args:
        tracks: List of mido Track objects (already loaded)
        ticks_per_beat: MIDI ticks per quarter note
        drum_map: Optional drum mapping for creating DrumNotes
    
    Returns:
        MidiSequence with all metadata
    """
    # Build tempo map
    tempo_map = build_tempo_map_from_tracks(tracks, ticks_per_beat)
    tempo_map_bpm = convert_tempo_map_to_bpm(tempo_map)
    
    # Extract notes
    if drum_map:
        midi_notes, duration = extract_midi_notes_from_tracks(
            tracks, 
            ticks_per_beat, 
            tempo_map
        )
        notes = map_midi_notes_to_drums(midi_notes, drum_map)
    else:
        notes, duration = extract_midi_notes_from_tracks(
            tracks, 
            ticks_per_beat, 
            tempo_map
        )
    
    # Get time signature
    time_signature = extract_time_signature_from_tracks(tracks)
    
    return MidiSequence(
        notes=notes,
        duration=duration,
        tempo_map=tempo_map_bpm,
        ticks_per_beat=ticks_per_beat,
        time_signature=time_signature
    )
