"""
Tests for MIDI Core - Functional Core

Tests pure functions that process MIDI data.
No file I/O in these tests - only data transformations.
"""

import pytest
from midi_core import (
    tempo_to_bpm,
    bpm_to_tempo,
    map_midi_notes_to_drums,
    convert_tempo_map_to_bpm
)
from midi_types import MidiNote, DrumNote


class TestTempoConversion:
    """Test tempo conversion functions"""
    
    def test_tempo_to_bpm(self):
        """Test conversion from microseconds to BPM"""
        # 120 BPM = 500000 microseconds per beat
        assert tempo_to_bpm(500000) == 120.0
        
        # 60 BPM = 1000000 microseconds per beat
        assert tempo_to_bpm(1000000) == 60.0
        
        # 140 BPM ≈ 428571 microseconds per beat
        assert abs(tempo_to_bpm(428571) - 140.0) < 0.1
    
    def test_bpm_to_tempo(self):
        """Test conversion from BPM to microseconds"""
        assert bpm_to_tempo(120.0) == 500000
        assert bpm_to_tempo(60.0) == 1000000
        assert abs(bpm_to_tempo(140.0) - 428571) < 1
    
    def test_round_trip_conversion(self):
        """Test that conversions are reversible"""
        original_bpm = 128.0
        tempo = bpm_to_tempo(original_bpm)
        result_bpm = tempo_to_bpm(tempo)
        assert abs(original_bpm - result_bpm) < 0.01
    
    def test_convert_tempo_map_to_bpm(self):
        """Test converting entire tempo map"""
        tempo_map = [
            (0.0, 500000),   # 120 BPM
            (10.0, 600000),  # 100 BPM
            (20.0, 428571),  # ~140 BPM
        ]
        
        bpm_map = convert_tempo_map_to_bpm(tempo_map)
        
        assert len(bpm_map) == 3
        assert bpm_map[0] == (0.0, 120.0)
        assert bpm_map[1] == (10.0, 100.0)
        assert abs(bpm_map[2][1] - 140.0) < 0.1


class TestMidiNoteMapping:
    """Test mapping MIDI notes to drum notes"""
    
    def test_map_single_note(self):
        """Test mapping a single MIDI note"""
        midi_notes = [
            MidiNote(midi_note=36, time=1.0, velocity=100, channel=9)
        ]
        
        drum_map = {
            36: [{"name": "Kick", "lane": -1, "color": (255, 255, 0)}]
        }
        
        drum_notes = map_midi_notes_to_drums(midi_notes, drum_map)
        
        assert len(drum_notes) == 1
        assert drum_notes[0].midi_note == 36
        assert drum_notes[0].time == 1.0
        assert drum_notes[0].velocity == 100
        assert drum_notes[0].lane == -1
        assert drum_notes[0].color == (255, 255, 0)
        assert drum_notes[0].name == "Kick"
    
    def test_map_multiple_notes(self):
        """Test mapping multiple MIDI notes"""
        midi_notes = [
            MidiNote(midi_note=36, time=1.0, velocity=100, channel=9),
            MidiNote(midi_note=38, time=2.0, velocity=80, channel=9),
            MidiNote(midi_note=42, time=3.0, velocity=90, channel=9),
        ]
        
        drum_map = {
            36: [{"name": "Kick", "lane": -1, "color": (255, 255, 0)}],
            38: [{"name": "Snare", "lane": 2, "color": (255, 0, 0)}],
            42: [{"name": "HiHat Closed", "lane": 0, "color": (0, 255, 255)}],
        }
        
        drum_notes = map_midi_notes_to_drums(midi_notes, drum_map)
        
        assert len(drum_notes) == 3
        assert drum_notes[0].name == "Kick"
        assert drum_notes[1].name == "Snare"
        assert drum_notes[2].name == "HiHat Closed"
    
    def test_map_unmapped_note_ignored(self):
        """Test that unmapped MIDI notes are ignored"""
        midi_notes = [
            MidiNote(midi_note=36, time=1.0, velocity=100, channel=9),
            MidiNote(midi_note=99, time=2.0, velocity=80, channel=9),  # Not in map
        ]
        
        drum_map = {
            36: [{"name": "Kick", "lane": -1, "color": (255, 255, 0)}],
        }
        
        drum_notes = map_midi_notes_to_drums(midi_notes, drum_map)
        
        assert len(drum_notes) == 1
        assert drum_notes[0].midi_note == 36
    
    def test_map_one_to_many(self):
        """Test mapping one MIDI note to multiple drum notes"""
        midi_notes = [
            MidiNote(midi_note=38, time=1.0, velocity=100, channel=9),
        ]
        
        # Snare can produce multiple sounds (head + rim)
        drum_map = {
            38: [
                {"name": "Snare Head", "lane": 2, "color": (255, 0, 0)},
                {"name": "Snare Rim", "lane": 3, "color": (200, 0, 0)},
            ]
        }
        
        drum_notes = map_midi_notes_to_drums(midi_notes, drum_map)
        
        assert len(drum_notes) == 2
        assert drum_notes[0].name == "Snare Head"
        assert drum_notes[0].lane == 2
        assert drum_notes[1].name == "Snare Rim"
        assert drum_notes[1].lane == 3
    
    def test_sorted_by_time(self):
        """Test that output is sorted by time"""
        midi_notes = [
            MidiNote(midi_note=42, time=3.0, velocity=90, channel=9),
            MidiNote(midi_note=36, time=1.0, velocity=100, channel=9),
            MidiNote(midi_note=38, time=2.0, velocity=80, channel=9),
        ]
        
        drum_map = {
            36: [{"name": "Kick", "lane": -1, "color": (255, 255, 0)}],
            38: [{"name": "Snare", "lane": 2, "color": (255, 0, 0)}],
            42: [{"name": "HiHat", "lane": 0, "color": (0, 255, 255)}],
        }
        
        drum_notes = map_midi_notes_to_drums(midi_notes, drum_map)
        
        assert len(drum_notes) == 3
        assert drum_notes[0].time == 1.0
        assert drum_notes[1].time == 2.0
        assert drum_notes[2].time == 3.0
