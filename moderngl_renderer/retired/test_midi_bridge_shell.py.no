"""
Tests for MIDI Bridge Shell

Tests the imperative shell that connects MIDI data to GPU rendering.
Uses Level 1 (smoke tests) and Level 2 (property tests) from testing guidelines.
"""

import pytest
import numpy as np
from midi_types import DrumNote
from .midi_bridge_core import RenderConfig
from .midi_bridge_shell import render_midi_frame, render_midi_to_frames
from .shell import ModernGLContext


# ============================================================================
# Level 1: Smoke Tests
# ============================================================================

class TestRenderMidiFrameSmoke:
    """Level 1: Verify basic operations don't crash"""
    
    @pytest.fixture
    def gpu_context(self):
        """Create GPU context for testing"""
        ctx = ModernGLContext(width=1920, height=1080)
        yield ctx
        ctx.cleanup()
    
    @pytest.fixture
    def config(self):
        """Create render config"""
        return RenderConfig(width=1920, height=1080, fps=60)
    
    def test_render_empty_notes(self, gpu_context, config):
        """Should handle empty note list without crashing"""
        notes = []
        current_time = 0.0
        
        # Should not crash
        render_midi_frame(gpu_context, notes, current_time, config)
    
    def test_render_single_note(self, gpu_context, config):
        """Should render a single note"""
        notes = [
            DrumNote(
                midi_note=36,
                time=1.0,
                velocity=100,
                lane=0,
                color=(255, 0, 0),
                name="Kick"
            )
        ]
        current_time = 0.5
        
        # Should not crash
        render_midi_frame(gpu_context, notes, current_time, config)
    
    def test_render_kick_drum(self, gpu_context, config):
        """Should render kick drum (lane=-1) as full-width bar"""
        notes = [
            DrumNote(
                midi_note=36,
                time=1.0,
                velocity=100,
                lane=-1,  # Kick drum special lane
                color=(255, 0, 0),
                name="Kick"
            )
        ]
        current_time = 0.5
        
        # Should not crash
        render_midi_frame(gpu_context, notes, current_time, config)
    
    def test_render_multiple_lanes(self, gpu_context, config):
        """Should handle notes in different lanes"""
        notes = [
            DrumNote(36, 1.0, 100, 0, (255, 0, 0), "Kick"),
            DrumNote(38, 1.5, 80, 1, (0, 255, 0), "Snare"),
            DrumNote(42, 2.0, 60, 2, (0, 0, 255), "HiHat"),
        ]
        current_time = 1.0
        
        # Should not crash
        render_midi_frame(gpu_context, notes, current_time, config)


# ============================================================================
# Level 2: Property Tests
# ============================================================================

class TestRenderMidiFrameProperties:
    """Level 2: Verify behavior properties"""
    
    @pytest.fixture
    def gpu_context(self):
        """Create GPU context for testing"""
        ctx = ModernGLContext(width=1920, height=1080)
        yield ctx
        ctx.cleanup()
    
    @pytest.fixture
    def config(self):
        """Create render config"""
        return RenderConfig(width=1920, height=1080, fps=60)
    
    def test_sequential_renders_independent(self, gpu_context, config):
        """Sequential renders should not interfere with each other"""
        from .shell import read_framebuffer
        
        notes1 = [DrumNote(36, 1.0, 100, 0, (255, 0, 0), "Kick")]
        notes2 = [DrumNote(38, 1.0, 100, 1, (0, 255, 0), "Snare")]
        
        # Render first scene
        render_midi_frame(gpu_context, notes1, 0.5, config)
        frame1 = read_framebuffer(gpu_context)
        
        # Render second scene (should not contain frame1 data)
        render_midi_frame(gpu_context, notes2, 0.5, config)
        frame2 = read_framebuffer(gpu_context)
        
        # Frames should be different (different colored notes)
        assert not np.array_equal(frame1, frame2)
    
    def test_produces_valid_output_dimensions(self, gpu_context, config):
        """Output should match configured dimensions"""
        from .shell import read_framebuffer
        
        notes = [DrumNote(36, 1.0, 100, 0, (255, 0, 0), "Kick")]
        render_midi_frame(gpu_context, notes, 0.5, config)
        
        frame = read_framebuffer(gpu_context)
        
        assert frame.shape == (1080, 1920, 3)
        assert frame.dtype == np.uint8
    
    def test_clear_color_affects_background(self, gpu_context, config):
        """Different clear colors should produce different backgrounds"""
        from .shell import read_framebuffer
        
        notes = []  # Empty scene
        
        # Render with black background
        render_midi_frame(gpu_context, notes, 0.0, config, clear_color=(0.0, 0.0, 0.0))
        frame_black = read_framebuffer(gpu_context)
        
        # Render with white background
        render_midi_frame(gpu_context, notes, 0.0, config, clear_color=(1.0, 1.0, 1.0))
        frame_white = read_framebuffer(gpu_context)
        
        # Backgrounds should be different
        assert not np.array_equal(frame_black, frame_white)
        
        # Black background should be dark
        assert frame_black.mean() < 10
        
        # White background should be bright
        assert frame_white.mean() > 245


# ============================================================================
# Generator Tests
# ============================================================================

class TestRenderMidiToFrames:
    """Test frame generation for video output"""
    
    def test_generator_yields_frames(self):
        """Should yield numpy arrays for each frame"""
        notes = [DrumNote(36, 1.0, 100, 0, (255, 0, 0), "Kick")]
        
        # Generate 1 second at 30 fps = 30 frames
        frames = list(render_midi_to_frames(
            notes, 
            width=640, 
            height=480, 
            fps=30,
            duration=1.0
        ))
        
        assert len(frames) == 30
        
        # Each frame should be correct shape
        for frame in frames:
            assert frame.shape == (480, 640, 3)
            assert frame.dtype == np.uint8
    
    def test_auto_calculates_duration(self):
        """Should auto-calculate duration from latest note time"""
        notes = [
            DrumNote(36, 1.0, 100, 0, (255, 0, 0), "Kick"),
            DrumNote(38, 5.0, 100, 1, (0, 255, 0), "Snare"),
        ]
        
        # Duration should be auto-calculated to at least 5.0 + buffer
        frames = list(render_midi_to_frames(
            notes,
            width=320,
            height=240,
            fps=10,
            duration=None  # Auto-calculate
        ))
        
        # Should render past last note (5.0s) + buffer (2.0s) = 7.0s minimum
        # At 10 fps, that's 70+ frames
        assert len(frames) >= 70
    
    def test_empty_notes_returns_immediately(self):
        """Empty notes should not generate frames"""
        notes = []
        
        frames = list(render_midi_to_frames(
            notes,
            duration=None  # Auto-calculate from empty list
        ))
        
        assert len(frames) == 0
    
    def test_custom_resolution(self):
        """Should respect custom resolution"""
        notes = [DrumNote(36, 1.0, 100, 0, (255, 0, 0), "Kick")]
        
        frames = list(render_midi_to_frames(
            notes,
            width=800,
            height=600,
            fps=10,
            duration=0.5
        ))
        
        # 0.5s at 10fps = 5 frames
        assert len(frames) == 5
        
        # Check resolution
        for frame in frames:
            assert frame.shape == (600, 800, 3)
