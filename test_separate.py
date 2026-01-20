"""
Tests for separate.py with project-based workflow.

Tests the integration between separate.py and project_manager.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from project_manager import create_project
from separation_shell import process_stems_for_project


class TestSeparateIntegration:
    """Test separate.py integration with project manager."""
    
    @pytest.fixture
    def temp_env(self, tmp_path):
        """Create a complete test environment."""
        user_files = tmp_path / "user_files"
        user_files.mkdir()
        
        # Create root configs
        (tmp_path / "midiconfig.yaml").write_text("# Mock MIDI config for testing")
        
        return {
            "root": tmp_path,
            "user_files": user_files
        }
    
    def test_project_creation_from_audio_file(self, temp_env):
        """Test that a new audio file triggers project creation."""
        # Create an audio file in user_files root
        audio_file = temp_env["user_files"] / "test_song.wav"
        audio_file.write_text("fake audio data")
        
        # Create project
        project = create_project(audio_file, temp_env["user_files"], temp_env["root"])
        
        # Verify project structure
        assert project["number"] == 1
        assert project["name"] == "test_song"
        assert (project["path"] / "test_song.wav").exists()
        assert (project["path"] / "midiconfig.yaml").exists()
        assert (project["path"] / "stems").is_dir()
        
    def test_separation_workflow_preparation(self, temp_env):
        """Test that separation workflow properly prepares project structure."""
        # Create project
        audio_file = temp_env["user_files"] / "drums.wav"
        audio_file.write_text("fake audio data")
        
        project = create_project(audio_file, temp_env["user_files"], temp_env["root"])
        
        # Verify stems directory exists
        stems_dir = project["path"] / "stems"
        assert stems_dir.exists()
        assert stems_dir.is_dir()
        
        # Verify config is accessible
        config = project["path"] / "midiconfig.yaml"
        assert config.exists()
        assert "Mock MIDI config for testing" in config.read_text()
    
    def test_process_stems_signature(self, temp_env):
        """Smoke test: verify process_stems_for_project can be called with correct signature."""
        # Create a minimal project structure
        project_dir = temp_env["user_files"] / "test_project"
        project_dir.mkdir()
        stems_dir = project_dir / "stems"
        stems_dir.mkdir()
        
        # Create a fake audio file
        (project_dir / "test.wav").write_text("fake audio")
        
        # Disable the optimized processor to force fallback path
        # This avoids needing to mock torch/audio loading
        with patch('separation_shell.MDX_OPTIMIZED_AVAILABLE', False), \
             patch('separation_shell.load_mdx23c_checkpoint') as mock_load, \
             patch('separation_shell.get_checkpoint_hyperparameters') as mock_params:
            
            # Setup mocks to avoid actual model loading
            mock_model = Mock()
            mock_load.return_value = mock_model
            mock_params.return_value = {
                'audio': {'chunk_size': 1000, 'sample_rate': 44100},
                'training': {'instruments': ['kick', 'snare']}
            }
            
            # This should NOT raise TypeError about missing config_path
            try:
                process_stems_for_project(
                    project_dir=project_dir,
                    stems_dir=stems_dir,
                    model='mdx23c',
                    overlap=2,
                    device='cpu',
                    verbose=False
                )
            except (RuntimeError, FileNotFoundError, AttributeError, ValueError) as e:
                # These errors are OK - we're just testing the signature works
                # RuntimeError: checkpoint not found
                # FileNotFoundError: audio processing issues
                # AttributeError: mock object issues
                # ValueError: audio loading issues
                pass
            except TypeError as e:
                # This is what we're testing against - signature mismatch
                if 'config_path' in str(e):
                    pytest.fail(f"Function signature still expects config_path: {e}")
                else:
                    raise
