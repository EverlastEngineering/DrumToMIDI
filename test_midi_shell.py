"""
Tests for MIDI Shell - Imperative Shell

Tests file I/O and integration with the functional core.
"""

import pytest
from pathlib import Path
from midi_shell import (
    load_midi_file,
    parse_midi_file,
    parse_midi_to_sequence,
    validate_midi_file
)


class TestFileLoading:
    """Test MIDI file loading (I/O operations)"""
    
    def test_load_existing_file(self):
        """Test loading a real MIDI file"""
        midi_path = Path("user_files/2 - sdrums/midi/sdrums.mid")
        
        if not midi_path.exists():
            pytest.skip("Test MIDI file not found")
        
        midi_file = load_midi_file(str(midi_path))
        
        assert midi_file is not None
        assert hasattr(midi_file, 'tracks')
        assert hasattr(midi_file, 'ticks_per_beat')
        assert len(midi_file.tracks) > 0
    
    def test_load_nonexistent_file(self):
        """Test that loading nonexistent file raises error"""
        with pytest.raises(FileNotFoundError):
            load_midi_file("nonexistent.mid")
    
    def test_validate_existing_file(self):
        """Test validating a real MIDI file"""
        midi_path = Path("user_files/2 - sdrums/midi/sdrums.mid")
        
        if not midi_path.exists():
            pytest.skip("Test MIDI file not found")
        
        assert validate_midi_file(str(midi_path)) is True
    
    def test_validate_nonexistent_file(self):
        """Test validating nonexistent file returns False"""
        assert validate_midi_file("nonexistent.mid") is False


class TestParsing:
    """Test high-level parsing functions"""
    
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
        """Test parsing a real MIDI file"""
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
    
    def test_parse_without_drum_map_raises_error(self):
        """Test that parsing without drum_map raises ValueError"""
        midi_path = Path("user_files/2 - sdrums/midi/sdrums.mid")
        
        if not midi_path.exists():
            pytest.skip("Test MIDI file not found")
        
        with pytest.raises(ValueError, match="drum_map is required"):
            parse_midi_file(str(midi_path), drum_map=None)
    
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
