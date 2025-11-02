"""
Tests for MIDI Types - Data Contract Validation

Tests the shared type definitions used by MIDI parsers and renderers.
"""

import pytest
from midi_types import (
    MidiNote,
    DrumNote,
    DrumMapping,
    MidiSequence,
    midi_note_to_drum_note,
    drum_note_to_dict,
    dict_to_drum_note,
    validate_midi_note,
    validate_drum_note,
    STANDARD_GM_DRUM_MAP
)


# ============================================================================
# MidiNote Tests
# ============================================================================

class TestMidiNote:
    """Test MidiNote dataclass"""
    
    def test_basic_creation(self):
        """Test creating a basic MIDI note"""
        note = MidiNote(
            midi_note=60,
            time=1.5,
            velocity=100,
            channel=9
        )
        
        assert note.midi_note == 60
        assert note.time == 1.5
        assert note.velocity == 100
        assert note.channel == 9
        assert note.duration is None
    
    def test_with_duration(self):
        """Test MIDI note with duration"""
        note = MidiNote(
            midi_note=60,
            time=1.0,
            velocity=80,
            duration=0.5
        )
        
        assert note.duration == 0.5
    
    def test_default_channel(self):
        """Test default drum channel"""
        note = MidiNote(
            midi_note=36,
            time=0.0,
            velocity=127
        )
        
        assert note.channel == 9  # Default drum channel
    
    def test_immutability(self):
        """Test that MidiNote is immutable"""
        note = MidiNote(
            midi_note=60,
            time=1.0,
            velocity=100
        )
        
        with pytest.raises(AttributeError):
            note.time = 2.0


class TestMidiNoteValidation:
    """Test MidiNote validation"""
    
    def test_valid_note(self):
        """Test validation passes for valid note"""
        note = MidiNote(
            midi_note=60,
            time=1.5,
            velocity=100,
            channel=9
        )
        
        assert validate_midi_note(note) is True
    
    def test_midi_note_out_of_range_low(self):
        """Test validation fails for MIDI note < 0"""
        note = MidiNote(
            midi_note=-1,
            time=1.0,
            velocity=100
        )
        
        with pytest.raises(ValueError, match="out of range"):
            validate_midi_note(note)
    
    def test_midi_note_out_of_range_high(self):
        """Test validation fails for MIDI note > 127"""
        note = MidiNote(
            midi_note=128,
            time=1.0,
            velocity=100
        )
        
        with pytest.raises(ValueError, match="out of range"):
            validate_midi_note(note)
    
    def test_negative_time(self):
        """Test validation fails for negative time"""
        note = MidiNote(
            midi_note=60,
            time=-1.0,
            velocity=100
        )
        
        with pytest.raises(ValueError, match="must be non-negative"):
            validate_midi_note(note)
    
    def test_velocity_out_of_range(self):
        """Test validation fails for invalid velocity"""
        note = MidiNote(
            midi_note=60,
            time=1.0,
            velocity=128
        )
        
        with pytest.raises(ValueError, match="out of range"):
            validate_midi_note(note)
    
    def test_channel_out_of_range(self):
        """Test validation fails for invalid channel"""
        note = MidiNote(
            midi_note=60,
            time=1.0,
            velocity=100,
            channel=16
        )
        
        with pytest.raises(ValueError, match="out of range"):
            validate_midi_note(note)
    
    def test_negative_duration(self):
        """Test validation fails for negative duration"""
        note = MidiNote(
            midi_note=60,
            time=1.0,
            velocity=100,
            duration=-0.5
        )
        
        with pytest.raises(ValueError, match="must be non-negative"):
            validate_midi_note(note)


# ============================================================================
# DrumNote Tests
# ============================================================================

class TestDrumNote:
    """Test DrumNote dataclass"""
    
    def test_basic_creation(self):
        """Test creating a basic drum note"""
        note = DrumNote(
            midi_note=36,
            time=1.0,
            velocity=120,
            lane=-1,
            color=(255, 140, 90),
            name="Kick"
        )
        
        assert note.midi_note == 36
        assert note.time == 1.0
        assert note.velocity == 120
        assert note.lane == -1
        assert note.color == (255, 140, 90)
        assert note.name == "Kick"
    
    def test_default_name(self):
        """Test default empty name"""
        note = DrumNote(
            midi_note=38,
            time=2.0,
            velocity=100,
            lane=2,
            color=(255, 0, 0)
        )
        
        assert note.name == ""
    
    def test_regular_lane(self):
        """Test regular lane (positive number)"""
        note = DrumNote(
            midi_note=42,
            time=0.5,
            velocity=80,
            lane=0,
            color=(0, 255, 255)
        )
        
        assert note.lane == 0
    
    def test_special_lane(self):
        """Test special lane (negative number)"""
        note = DrumNote(
            midi_note=36,
            time=1.0,
            velocity=127,
            lane=-1,
            color=(255, 255, 0)
        )
        
        assert note.lane == -1
    
    def test_immutability(self):
        """Test that DrumNote is immutable"""
        note = DrumNote(
            midi_note=38,
            time=1.0,
            velocity=100,
            lane=2,
            color=(255, 0, 0)
        )
        
        with pytest.raises(AttributeError):
            note.velocity = 50


class TestDrumNoteValidation:
    """Test DrumNote validation"""
    
    def test_valid_drum_note(self):
        """Test validation passes for valid drum note"""
        note = DrumNote(
            midi_note=36,
            time=1.0,
            velocity=100,
            lane=-1,
            color=(255, 140, 90)
        )
        
        assert validate_drum_note(note) is True
    
    def test_invalid_color_length(self):
        """Test validation fails for non-RGB color"""
        note = DrumNote(
            midi_note=36,
            time=1.0,
            velocity=100,
            lane=-1,
            color=(255, 140)  # Only 2 components
        )
        
        with pytest.raises(ValueError, match="RGB tuple"):
            validate_drum_note(note)
    
    def test_color_out_of_range(self):
        """Test validation fails for color > 255"""
        note = DrumNote(
            midi_note=36,
            time=1.0,
            velocity=100,
            lane=-1,
            color=(255, 300, 90)  # 300 > 255
        )
        
        with pytest.raises(ValueError, match="0, 255"):
            validate_drum_note(note)
    
    def test_negative_color(self):
        """Test validation fails for negative color"""
        note = DrumNote(
            midi_note=36,
            time=1.0,
            velocity=100,
            lane=-1,
            color=(-10, 140, 90)
        )
        
        with pytest.raises(ValueError, match="0, 255"):
            validate_drum_note(note)


# ============================================================================
# DrumMapping Tests
# ============================================================================

class TestDrumMapping:
    """Test DrumMapping dataclass"""
    
    def test_basic_creation(self):
        """Test creating drum mapping"""
        mapping = DrumMapping(
            name="Snare",
            lane=2,
            color=(255, 0, 0)
        )
        
        assert mapping.name == "Snare"
        assert mapping.lane == 2
        assert mapping.color == (255, 0, 0)
    
    def test_immutability(self):
        """Test that DrumMapping is immutable"""
        mapping = DrumMapping(
            name="Kick",
            lane=-1,
            color=(255, 255, 0)
        )
        
        with pytest.raises(AttributeError):
            mapping.lane = 0


# ============================================================================
# MidiSequence Tests
# ============================================================================

class TestMidiSequence:
    """Test MidiSequence dataclass"""
    
    def test_basic_creation(self):
        """Test creating MIDI sequence"""
        notes = [
            MidiNote(36, 0.0, 120),
            MidiNote(38, 0.5, 100),
        ]
        
        sequence = MidiSequence(
            notes=notes,
            duration=3.0
        )
        
        assert len(sequence.notes) == 2
        assert sequence.duration == 3.0
        assert sequence.tempo_map == [(0.0, 120.0)]  # Default
        assert sequence.ticks_per_beat == 480
        assert sequence.time_signature == (4, 4)
    
    def test_with_tempo_map(self):
        """Test sequence with custom tempo map"""
        notes = [MidiNote(36, 0.0, 120)]
        tempo_map = [(0.0, 120.0), (2.0, 140.0)]
        
        sequence = MidiSequence(
            notes=notes,
            duration=5.0,
            tempo_map=tempo_map
        )
        
        assert sequence.tempo_map == tempo_map
    
    def test_custom_time_signature(self):
        """Test sequence with non-4/4 time"""
        notes = [MidiNote(36, 0.0, 120)]
        
        sequence = MidiSequence(
            notes=notes,
            duration=3.0,
            time_signature=(3, 4)  # 3/4 time
        )
        
        assert sequence.time_signature == (3, 4)


# ============================================================================
# Conversion Functions Tests
# ============================================================================

class TestConversions:
    """Test conversion functions"""
    
    def test_midi_note_to_drum_note(self):
        """Test converting MidiNote to DrumNote"""
        midi_note = MidiNote(
            midi_note=38,
            time=1.5,
            velocity=100,
            channel=9
        )
        
        mapping = DrumMapping(
            name="Snare",
            lane=2,
            color=(255, 0, 0)
        )
        
        drum_note = midi_note_to_drum_note(midi_note, mapping)
        
        assert drum_note.midi_note == 38
        assert drum_note.time == 1.5
        assert drum_note.velocity == 100
        assert drum_note.lane == 2
        assert drum_note.color == (255, 0, 0)
        assert drum_note.name == "Snare"
    
    def test_drum_note_to_dict(self):
        """Test converting DrumNote to dictionary"""
        note = DrumNote(
            midi_note=36,
            time=1.0,
            velocity=120,
            lane=-1,
            color=(255, 140, 90),
            name="Kick"
        )
        
        data = drum_note_to_dict(note)
        
        assert data['midi_note'] == 36
        assert data['time'] == 1.0
        assert data['velocity'] == 120
        assert data['lane'] == -1
        assert data['color'] == (255, 140, 90)
        assert data['name'] == "Kick"
    
    def test_dict_to_drum_note(self):
        """Test converting dictionary to DrumNote"""
        data = {
            'midi_note': 42,
            'time': 0.5,
            'velocity': 80,
            'lane': 0,
            'color': (0, 255, 255),
            'name': 'Hi-Hat Closed'
        }
        
        note = dict_to_drum_note(data)
        
        assert note.midi_note == 42
        assert note.time == 0.5
        assert note.velocity == 80
        assert note.lane == 0
        assert note.color == (0, 255, 255)
        assert note.name == 'Hi-Hat Closed'
    
    def test_dict_to_drum_note_with_defaults(self):
        """Test dict conversion with missing optional fields"""
        data = {
            'time': 1.0,
            'velocity': 100
        }
        
        note = dict_to_drum_note(data)
        
        assert note.midi_note == 0  # Default
        assert note.time == 1.0
        assert note.velocity == 100
        assert note.lane == 0  # Default
        assert note.color == (255, 255, 255)  # Default white
        assert note.name == ''  # Default empty
    
    def test_round_trip_conversion(self):
        """Test converting drum note to dict and back"""
        original = DrumNote(
            midi_note=38,
            time=2.0,
            velocity=110,
            lane=2,
            color=(255, 0, 0),
            name="Snare"
        )
        
        data = drum_note_to_dict(original)
        restored = dict_to_drum_note(data)
        
        assert restored == original


# ============================================================================
# Standard Drum Map Tests
# ============================================================================

class TestStandardDrumMap:
    """Test standard GM drum map"""
    
    def test_drum_map_exists(self):
        """Test that standard drum map is defined"""
        assert STANDARD_GM_DRUM_MAP is not None
        assert isinstance(STANDARD_GM_DRUM_MAP, dict)
    
    def test_kick_drum_mapping(self):
        """Test kick drum (36) is in map"""
        assert 36 in STANDARD_GM_DRUM_MAP
        kick = STANDARD_GM_DRUM_MAP[36][0]
        
        assert kick['name'] == 'Kick'
        assert kick['lane'] == -1  # Special lane
        assert len(kick['color']) == 3
    
    def test_snare_mapping(self):
        """Test snare (38) is in map"""
        assert 38 in STANDARD_GM_DRUM_MAP
        snare = STANDARD_GM_DRUM_MAP[38][0]
        
        assert snare['name'] == 'Snare'
        assert snare['lane'] >= 0  # Regular lane
    
    def test_hihat_closed_mapping(self):
        """Test hi-hat closed (42) is in map"""
        assert 42 in STANDARD_GM_DRUM_MAP
        hihat = STANDARD_GM_DRUM_MAP[42][0]
        
        assert hihat['name'] == 'Hi-Hat Closed'
        assert hihat['lane'] >= 0
    
    def test_all_mappings_valid_structure(self):
        """Test all drum map entries have correct structure"""
        for midi_note, mappings in STANDARD_GM_DRUM_MAP.items():
            # Must be a MIDI note number
            assert 0 <= midi_note <= 127
            
            # Must be a list
            assert isinstance(mappings, list)
            assert len(mappings) > 0
            
            # Each mapping must have required fields
            for mapping in mappings:
                assert 'name' in mapping
                assert 'lane' in mapping
                assert 'color' in mapping
                
                assert isinstance(mapping['name'], str)
                assert isinstance(mapping['lane'], int)
                assert isinstance(mapping['color'], tuple)
                assert len(mapping['color']) == 3
                
                # Validate color range
                for c in mapping['color']:
                    assert 0 <= c <= 255
    
    def test_unique_lanes(self):
        """Test that regular lanes are unique (no duplicates except special lanes)"""
        regular_lanes = []
        
        for mappings in STANDARD_GM_DRUM_MAP.values():
            for mapping in mappings:
                if mapping['lane'] >= 0:
                    regular_lanes.append(mapping['lane'])
        
        # Check for reasonable lane assignments (should be consecutive-ish)
        unique_lanes = set(regular_lanes)
        assert len(unique_lanes) > 0
        assert max(unique_lanes) < 20  # Shouldn't have huge gaps


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Test typical usage patterns"""
    
    def test_typical_workflow(self):
        """Test typical MIDI parsing to rendering workflow"""
        # 1. Parser creates MidiNotes
        midi_notes = [
            MidiNote(36, 0.0, 120),  # Kick
            MidiNote(38, 0.5, 100),  # Snare
            MidiNote(42, 1.0, 80),   # Hi-hat
        ]
        
        # 2. Mapper converts to DrumNotes using drum map
        drum_notes = []
        for midi_note in midi_notes:
            if midi_note.midi_note in STANDARD_GM_DRUM_MAP:
                for mapping_dict in STANDARD_GM_DRUM_MAP[midi_note.midi_note]:
                    mapping = DrumMapping(**mapping_dict)
                    drum_note = midi_note_to_drum_note(midi_note, mapping)
                    drum_notes.append(drum_note)
        
        # 3. Verify we got drum notes
        assert len(drum_notes) == 3
        
        # 4. Renderer can validate and use them
        for note in drum_notes:
            assert validate_drum_note(note)
        
        # 5. Can convert to dict format for moderngl_renderer
        dict_notes = [drum_note_to_dict(n) for n in drum_notes]
        assert len(dict_notes) == 3
        assert all('time' in n for n in dict_notes)
    
    def test_sequence_creation(self):
        """Test creating complete MIDI sequence"""
        notes = [
            MidiNote(36, t * 0.5, 120)
            for t in range(8)
        ]
        
        sequence = MidiSequence(
            notes=notes,
            duration=4.0,
            tempo_map=[(0.0, 120.0)],
            ticks_per_beat=480
        )
        
        assert len(sequence.notes) == 8
        assert sequence.notes[0].time == 0.0
        assert sequence.notes[-1].time == 3.5
        assert sequence.duration == 4.0
