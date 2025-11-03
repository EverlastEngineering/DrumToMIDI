"""
FFmpeg Video Encoder - Imperative Shell

Handles video encoding via FFmpeg subprocess with audio sync.
Pure side-effects module - no business logic, just I/O operations.

This module coordinates:
- Input: Frame generator (numpy arrays)
- Process: FFmpeg subprocess with H.264 encoding
- Output: MP4 video file with optional audio track
"""

import subprocess
import sys
from typing import Iterator, Optional
from pathlib import Path
import numpy as np


class FFmpegEncoder:
    """FFmpeg video encoder with audio sync support
    
    Manages FFmpeg subprocess lifecycle for encoding video frames to MP4.
    Supports optional audio track synchronization.
    
    Side effects:
    - Spawns FFmpeg subprocess
    - Writes video data to pipe
    - Creates output video file
    - Manages process cleanup
    """
    
    def __init__(
        self,
        output_path: str,
        width: int,
        height: int,
        fps: int,
        audio_path: Optional[str] = None,
        preset: str = "medium",
        crf: int = 23,
        audio_bitrate: str = "192k",
        pix_fmt: str = "yuv420p",
        verbose: bool = True
    ):
        """Initialize FFmpeg encoder
        
        Args:
            output_path: Path for output MP4 file
            width: Frame width in pixels
            height: Frame height in pixels
            fps: Frames per second
            audio_path: Optional path to audio file for sync
            preset: FFmpeg preset (ultrafast, fast, medium, slow, veryslow)
            crf: Constant Rate Factor (0-51, lower=better quality, 23=default)
            audio_bitrate: Audio bitrate (e.g., "192k", "256k")
            pix_fmt: Pixel format for output (yuv420p for compatibility)
            verbose: Print encoding progress
        """
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.audio_path = audio_path
        self.preset = preset
        self.crf = crf
        self.audio_bitrate = audio_bitrate
        self.pix_fmt = pix_fmt
        self.verbose = verbose
        
        self.process: Optional[subprocess.Popen] = None
        self.frames_written = 0
    
    def _build_ffmpeg_command(self) -> list:
        """Build FFmpeg command line arguments
        
        Pure function that constructs command based on configuration.
        
        Returns:
            List of command arguments
        """
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',
            '-pix_fmt', 'rgb24',  # Input from numpy is RGB
            '-r', str(self.fps),
            '-i', '-',  # Read video from stdin
        ]
        
        # Add audio input if provided
        if self.audio_path:
            if not Path(self.audio_path).exists():
                raise FileNotFoundError(f"Audio file not found: {self.audio_path}")
            cmd.extend(['-i', self.audio_path])
            # Map video from stdin (0) and audio from file (1)
            cmd.extend(['-map', '0:v:0', '-map', '1:a:0'])
            # Use shortest stream (handles audio/video length mismatch)
            cmd.append('-shortest')
        else:
            cmd.append('-an')  # No audio
        
        # Video encoding settings
        cmd.extend([
            '-vcodec', 'libx264',
            '-preset', self.preset,
            '-crf', str(self.crf),
            '-pix_fmt', self.pix_fmt,
        ])
        
        # Audio encoding settings (if audio is included)
        if self.audio_path:
            cmd.extend(['-c:a', 'aac', '-b:a', self.audio_bitrate])
        
        # Web optimization (move moov atom to start for streaming)
        cmd.extend(['-movflags', '+faststart'])
        
        # Output file
        cmd.append(self.output_path)
        
        return cmd
    
    def start(self):
        """Start FFmpeg subprocess
        
        Side effects:
        - Spawns FFmpeg process
        - Opens pipe for writing frames
        
        Raises:
            RuntimeError: If FFmpeg cannot be started
        """
        if self.process is not None:
            raise RuntimeError("Encoder already started")
        
        cmd = self._build_ffmpeg_command()
        
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"Starting FFmpeg encoder...")
            print(f"  Output: {self.output_path}")
            print(f"  Resolution: {self.width}x{self.height} @ {self.fps}fps")
            print(f"  Codec: H.264 (preset={self.preset}, crf={self.crf})")
            if self.audio_path:
                print(f"  Audio: {Path(self.audio_path).name} ({self.audio_bitrate})")
            else:
                print(f"  Audio: None")
            print(f"{'='*70}\n")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg:\n"
                "  macOS: brew install ffmpeg\n"
                "  Linux: apt-get install ffmpeg\n"
                "  Windows: Download from https://ffmpeg.org/"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start FFmpeg: {e}")
    
    def write_frame(self, frame: np.ndarray):
        """Write a single frame to FFmpeg
        
        Side effects:
        - Writes frame data to FFmpeg stdin pipe
        
        Args:
            frame: RGB numpy array (height, width, 3) with dtype uint8
        
        Raises:
            RuntimeError: If encoder not started or frame is wrong format
        """
        if self.process is None:
            raise RuntimeError("Encoder not started. Call start() first.")
        
        # Validate frame format
        if frame.shape != (self.height, self.width, 3):
            raise ValueError(
                f"Frame shape mismatch: expected ({self.height}, {self.width}, 3), "
                f"got {frame.shape}"
            )
        if frame.dtype != np.uint8:
            raise ValueError(f"Frame dtype must be uint8, got {frame.dtype}")
        
        try:
            self.process.stdin.write(frame.tobytes())
            self.frames_written += 1
            
            if self.verbose and self.frames_written % 60 == 0:
                elapsed = self.frames_written / self.fps
                print(f"  Encoded {self.frames_written} frames ({elapsed:.1f}s)...", 
                      end='\r', flush=True)
        
        except BrokenPipeError:
            # FFmpeg process died
            stderr = self.process.stderr.read().decode('utf-8')
            raise RuntimeError(f"FFmpeg process failed:\n{stderr}")
    
    def finish(self) -> tuple[bool, str]:
        """Close encoder and wait for FFmpeg to finish
        
        Side effects:
        - Closes stdin pipe
        - Waits for FFmpeg process to complete
        - Captures stderr output
        
        Returns:
            (success, stderr_output) tuple
        """
        if self.process is None:
            raise RuntimeError("Encoder not started")
        
        try:
            self.process.stdin.close()
            stderr = self.process.stderr.read().decode('utf-8')
            returncode = self.process.wait()
            
            if self.verbose:
                print()  # New line after progress
                if returncode == 0:
                    print(f"✓ Encoded {self.frames_written} frames successfully")
                    print(f"  Output: {self.output_path}")
                else:
                    print(f"✗ FFmpeg exited with code {returncode}")
            
            return (returncode == 0, stderr)
        
        finally:
            self.process = None
            self.frames_written = 0
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.process is not None:
            try:
                self.finish()
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Error during encoder cleanup: {e}")
        return False  # Don't suppress exceptions


def encode_frames_to_video(
    frames: Iterator[np.ndarray],
    output_path: str,
    width: int,
    height: int,
    fps: int,
    audio_path: Optional[str] = None,
    preset: str = "medium",
    crf: int = 23,
    verbose: bool = True
) -> bool:
    """Encode frame generator to video file
    
    Convenience function for simple encoding workflows.
    
    Args:
        frames: Iterator yielding RGB numpy arrays (height, width, 3)
        output_path: Path for output MP4 file
        width: Frame width in pixels
        height: Frame height in pixels
        fps: Frames per second
        audio_path: Optional path to audio file for sync
        preset: FFmpeg preset (ultrafast, fast, medium, slow, veryslow)
        crf: Constant Rate Factor (0-51, lower=better quality)
        verbose: Print encoding progress
    
    Returns:
        True if encoding succeeded, False otherwise
    """
    try:
        with FFmpegEncoder(
            output_path=output_path,
            width=width,
            height=height,
            fps=fps,
            audio_path=audio_path,
            preset=preset,
            crf=crf,
            verbose=verbose
        ) as encoder:
            for frame in frames:
                encoder.write_frame(frame)
        
        return True
    
    except Exception as e:
        if verbose:
            print(f"✗ Encoding failed: {e}")
            import traceback
            traceback.print_exc()
        return False
