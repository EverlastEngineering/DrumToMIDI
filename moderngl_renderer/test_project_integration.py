"""
Tests for ModernGL project integration module

Validates integration between ModernGL renderer and project management system.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from moderngl_renderer.project_integration import render_project_video_moderngl


class TestProjectIntegration:
    """Tests for project_integration module"""
    
    def test_render_project_video_moderngl_with_original_audio(self, tmp_path):
        """Test rendering with original audio source"""
        # Create mock project structure
        project_dir = tmp_path / "1 - test"
        project_dir.mkdir()
        (project_dir / "midi").mkdir()
        (project_dir / "video").mkdir()
        
        # Create dummy MIDI file
        midi_file = project_dir / "midi" / "test.mid"
        midi_file.write_bytes(b"MThd")  # Minimal MIDI header
        
        # Create dummy audio file
        audio_file = project_dir / "test.wav"
        audio_file.write_bytes(b"RIFF")  # Minimal WAV header
        
        # Create project dict
        project = {
            "number": 1,
            "name": "test",
            "path": project_dir,
            "metadata": {"status": {}}
        }
        
        # Mock the dependencies
        with patch('moderngl_renderer.project_integration.parse_midi_file') as mock_parse, \
             patch('moderngl_renderer.project_integration.render_midi_to_frames') as mock_render, \
             patch('moderngl_renderer.project_integration.FFmpegEncoder') as mock_encoder, \
             patch('project_manager.update_project_metadata') as mock_update:
            
            # Setup mocks
            mock_parse.return_value = ([], 10.0)  # Empty notes, 10s duration
            mock_render.return_value = iter([])  # No frames
            mock_encoder.return_value.__enter__ = Mock(return_value=Mock(write_frame=Mock()))
            mock_encoder.return_value.__exit__ = Mock(return_value=False)
            
            # Call function
            render_project_video_moderngl(
                project=project,
                width=1920,
                height=1080,
                fps=60,
                audio_source='original',
                fall_speed_multiplier=1.0
            )
            
            # Verify parse_midi_file was called with correct path
            assert mock_parse.called
            midi_path = str(mock_parse.call_args[0][0])
            assert midi_path.endswith("test.mid")
            
            # Verify render_midi_to_frames was called
            assert mock_render.called
            assert mock_render.call_args[1]['width'] == 1920
            assert mock_render.call_args[1]['height'] == 1080
            assert mock_render.call_args[1]['fps'] == 60
            
            # Verify FFmpegEncoder was called with audio
            assert mock_encoder.called
            audio_path = mock_encoder.call_args[1]['audio_path']
            assert audio_path is not None
            assert "test.wav" in audio_path
            
            # Verify metadata was updated
            assert mock_update.called
    
    def test_render_project_video_moderngl_without_audio(self, tmp_path):
        """Test rendering without audio"""
        # Create mock project structure
        project_dir = tmp_path / "1 - test"
        project_dir.mkdir()
        (project_dir / "midi").mkdir()
        (project_dir / "video").mkdir()
        
        # Create dummy MIDI file
        midi_file = project_dir / "midi" / "test.mid"
        midi_file.write_bytes(b"MThd")
        
        # Create project dict
        project = {
            "number": 1,
            "name": "test",
            "path": project_dir,
            "metadata": {"status": {}}
        }
        
        # Mock the dependencies
        with patch('moderngl_renderer.project_integration.parse_midi_file') as mock_parse, \
             patch('moderngl_renderer.project_integration.render_midi_to_frames') as mock_render, \
             patch('moderngl_renderer.project_integration.FFmpegEncoder') as mock_encoder, \
             patch('project_manager.update_project_metadata'):
            
            # Setup mocks
            mock_parse.return_value = ([], 10.0)
            mock_render.return_value = iter([])
            mock_encoder.return_value.__enter__ = Mock(return_value=Mock(write_frame=Mock()))
            mock_encoder.return_value.__exit__ = Mock(return_value=False)
            
            # Call function without audio
            render_project_video_moderngl(
                project=project,
                width=1920,
                height=1080,
                fps=60,
                audio_source=None,
                fall_speed_multiplier=1.0
            )
            
            # Verify FFmpegEncoder was called without audio
            assert mock_encoder.called
            audio_path = mock_encoder.call_args[1]['audio_path']
            assert audio_path is None
    
    def test_render_project_video_moderngl_missing_midi_directory(self, tmp_path, capsys):
        """Test error handling when MIDI directory is missing"""
        # Create mock project structure without midi directory
        project_dir = tmp_path / "1 - test"
        project_dir.mkdir()
        
        project = {
            "number": 1,
            "name": "test",
            "path": project_dir,
            "metadata": {"status": {}}
        }
        
        # Should exit with error
        with pytest.raises(SystemExit):
            render_project_video_moderngl(
                project=project,
                width=1920,
                height=1080,
                fps=60
            )
        
        # Check error message was printed
        captured = capsys.readouterr()
        assert "No midi/ directory found" in captured.out
    
    def test_render_project_video_moderngl_no_midi_files(self, tmp_path, capsys):
        """Test error handling when no MIDI files exist"""
        # Create mock project structure with empty midi directory
        project_dir = tmp_path / "1 - test"
        project_dir.mkdir()
        (project_dir / "midi").mkdir()
        
        project = {
            "number": 1,
            "name": "test",
            "path": project_dir,
            "metadata": {"status": {}}
        }
        
        # Should exit with error
        with pytest.raises(SystemExit):
            render_project_video_moderngl(
                project=project,
                width=1920,
                height=1080,
                fps=60
            )
        
        # Check error message was printed
        captured = capsys.readouterr()
        assert "No MIDI files found" in captured.out
    
    def test_render_project_video_moderngl_custom_fall_speed(self, tmp_path):
        """Test rendering with custom fall speed multiplier"""
        # Create mock project structure
        project_dir = tmp_path / "1 - test"
        project_dir.mkdir()
        (project_dir / "midi").mkdir()
        (project_dir / "video").mkdir()
        
        midi_file = project_dir / "midi" / "test.mid"
        midi_file.write_bytes(b"MThd")
        
        project = {
            "number": 1,
            "name": "test",
            "path": project_dir,
            "metadata": {"status": {}}
        }
        
        # Mock the dependencies
        with patch('moderngl_renderer.project_integration.parse_midi_file') as mock_parse, \
             patch('moderngl_renderer.project_integration.render_midi_to_frames') as mock_render, \
             patch('moderngl_renderer.project_integration.FFmpegEncoder') as mock_encoder, \
             patch('project_manager.update_project_metadata'):
            
            mock_parse.return_value = ([], 10.0)
            mock_render.return_value = iter([])
            mock_encoder.return_value.__enter__ = Mock(return_value=Mock(write_frame=Mock()))
            mock_encoder.return_value.__exit__ = Mock(return_value=False)
            
            # Call with custom fall speed
            render_project_video_moderngl(
                project=project,
                width=1920,
                height=1080,
                fps=60,
                fall_speed_multiplier=2.0
            )
            
            # Verify render was called with correct fall speed
            assert mock_render.called
            assert mock_render.call_args[1]['fall_speed_multiplier'] == 2.0
