"""
Tests for MIDI Parser

Tests the pure parsing functions without any rendering logic.
"""

import pytest
from pathlib import Path
from midi_parser import (
    tempo_to_bpm,
    map_midi_to_drums,
    parse_midi_file,
    parse_midi_to_sequence
)
from midi_types import MidiNote


class TestTempoMap:
    """Test tempo map building"""
    
    def test_tempo_to_bpm(self):
        """Test conversion from microseconds to BPM"""
        # 120 BPM = 500000 microseconds per beat
        assert tempo_to_bpm(500000) == 120.0
        
        # 60 BPM = 1000000 microseconds per beat
        assert tempo_to_bpm(1000000) == 60.0
        
        # 140 BPM ≈ 428571 microseconds per beat
        assert abs(tempo_to_bpm(428571) - 140.0) < 0.1


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
        
        drum_notes = map_midi_to_drums(midi_notes, drum_map)
        
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
        
        drum_notes = map_midi_to_drums(midi_notes, drum_map)
        
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
        
        drum_notes = map_midi_to_drums(midi_notes, drum_map)
        
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
        
        drum_notes = map_midi_to_drums(midi_notes, drum_map)
        
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
        
        drum_notes = map_midi_to_drums(midi_notes, drum_map)
        
        assert len(drum_notes) == 3
        assert drum_notes[0].time == 1.0
        assert drum_notes[1].time == 2.0
        assert drum_notes[2].time == 3.0


class TestIntegration:
    """Integration tests using real MIDI files"""
    
    @pytest.fixture
    def sample_drum_map(self):
        """Sample drum map for testing"""
        return {
            36: [{"name": "Kick", "lane": -1, "color": (255, 255, 0)}],
            38: [{"name": "Snare", "lane": 2, "color": (255, 0, 0)}],
            42: [{"name": "HiHat Closed", "lane": 0, "color": (0, 255, 255)}],
            46: [{"name": "HiHat Open", "lane": 1, "color": (30, 255, 80)}],
        }
    
    def test_parse_real_midi_file(self, sample_drum_map):
        """Test parsing a real MIDI file from the test projects"""
        # Use project 2's MIDI file if it exists
        midi_path = Path("user_files/2 - sdrums/midi/sdrums.mid")
        
        if not midi_path.exists():
            pytest.skip("Test MIDI file not found")
        
        drum_notes, duration = parse_midi_file(
            str(midi_path),
            drum_map=sample_drum_map,
            tail_duration=3.0
        )
        
        # Basic sanity checks
        assert len(drum_notes) > 0, "Should parse some notes"
        assert duration > 0, "Should have positive duration"
        
        # Check notes are sorted by time
        for i in range(len(drum_notes) - 1):
            assert drum_notes[i].time <= drum_notes[i + 1].time
        
        # Check all notes have valid properties
        for note in drum_notes:
            assert 0 <= note.velocity <= 127
            assert note.time >= 0
            assert len(note.color) == 3
            assert all(0 <= c <= 255 for c in note.color)
    
    def test_parse_to_sequence(self, sample_drum_map):
        """Test parsing to MidiSequence object"""
        midi_path = Path("user_files/2 - sdrums/midi/sdrums.mid")
        
        if not midi_path.exists():
            pytest.skip("Test MIDI file not found")
        
        sequence = parse_midi_to_sequence(
            str(midi_path),
            drum_map=sample_drum_map
        )
        
        assert len(sequence.notes) > 0
        assert sequence.duration > 0
        assert sequence.ticks_per_beat > 0
        assert len(sequence.tempo_map) > 0
        assert sequence.time_signature == (4, 4) or sequence.time_signature[0] > 0
        
        # Check tempo map has valid BPM values
        for time, bpm in sequence.tempo_map:
            assert time >= 0
            assert 20 <= bpm <= 300  # Reasonable BPM range
