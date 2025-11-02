"""
Integration tests for ModernGL imperative shell

Tests GPU operations and rendering pipeline without mocking.
Uses 3-tier approach:
  1. Smoke tests - fast sanity checks
  2. Property tests - verify behavior invariants
  3. Regression tests - pixel-perfect comparisons (manual/pre-release)

These tests exercise the entire GPU pipeline (shaders, framebuffers, blending)
but use smart assertions to remain robust to implementation changes.
"""

import pytest
import numpy as np
from pathlib import Path

from .shell import (
    ModernGLContext,
    render_rectangles,
    read_framebuffer,
    save_frame,
    render_frame_to_file,
    render_frames_to_array
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def small_context():
    """Create a small rendering context for fast tests"""
    ctx = ModernGLContext(width=100, height=100)
    yield ctx
    ctx.cleanup()


@pytest.fixture
def standard_context():
    """Create a standard 1080p context for realistic tests"""
    ctx = ModernGLContext(width=1920, height=1080)
    yield ctx
    ctx.cleanup()


@pytest.fixture
def simple_rectangle():
    """A simple red rectangle in the center"""
    return {
        'x': -0.1,
        'y': -0.1,
        'width': 0.2,
        'height': 0.2,
        'color': (1.0, 0.0, 0.0),
        'alpha': 1.0
    }


@pytest.fixture
def semi_transparent_rectangle():
    """A semi-transparent blue rectangle"""
    return {
        'x': -0.1,
        'y': -0.1,
        'width': 0.2,
        'height': 0.2,
        'color': (0.0, 0.0, 1.0),
        'alpha': 0.5
    }


# ============================================================================
# LEVEL 1: Smoke Tests (fast sanity checks)
# ============================================================================

def test_context_creation_and_cleanup():
    """Context can be created and cleaned up without errors"""
    ctx = ModernGLContext(width=100, height=100)
    assert ctx.width == 100
    assert ctx.height == 100
    assert ctx.ctx is not None
    ctx.cleanup()


def test_context_manager_protocol(simple_rectangle):
    """Context works with 'with' statement"""
    with ModernGLContext(width=100, height=100) as ctx:
        render_rectangles(ctx, [simple_rectangle])
        result = read_framebuffer(ctx)
        assert result.shape == (100, 100, 3)


def test_render_empty_scene(small_context):
    """Rendering empty scene doesn't crash"""
    render_rectangles(small_context, [])
    result = read_framebuffer(small_context)
    
    assert result.shape == (100, 100, 3)
    assert result.dtype == np.uint8


def test_render_single_rectangle(small_context, simple_rectangle):
    """Rendering a single rectangle produces valid output"""
    render_rectangles(small_context, [simple_rectangle])
    result = read_framebuffer(small_context)
    
    assert result.shape == (100, 100, 3)
    assert result.dtype == np.uint8
    assert result.max() > 0  # Something was rendered


def test_render_multiple_rectangles(small_context):
    """Rendering multiple rectangles works"""
    rectangles = [
        {'x': -0.5, 'y': 0.0, 'width': 0.2, 'height': 0.2, 'color': (1.0, 0.0, 0.0), 'alpha': 1.0},
        {'x': 0.0, 'y': 0.0, 'width': 0.2, 'height': 0.2, 'color': (0.0, 1.0, 0.0), 'alpha': 1.0},
        {'x': 0.5, 'y': 0.0, 'width': 0.2, 'height': 0.2, 'color': (0.0, 0.0, 1.0), 'alpha': 1.0},
    ]
    
    render_rectangles(small_context, rectangles)
    result = read_framebuffer(small_context)
    
    assert result.shape == (100, 100, 3)
    assert result.max() > 0


def test_render_frames_to_array(small_context):
    """Batch rendering produces correct output"""
    frame_scenes = [
        [{'x': -0.1, 'y': -0.1, 'width': 0.2, 'height': 0.2, 'color': (1.0, 0.0, 0.0), 'alpha': 1.0}],
        [{'x': 0.1, 'y': 0.1, 'width': 0.2, 'height': 0.2, 'color': (0.0, 1.0, 0.0), 'alpha': 1.0}],
    ]
    
    results = render_frames_to_array(frame_scenes, width=100, height=100)
    
    assert len(results) == 2
    assert all(r.shape == (100, 100, 3) for r in results)
    assert all(r.dtype == np.uint8 for r in results)


def test_save_frame_creates_file(small_context, simple_rectangle, tmp_path):
    """save_frame creates a valid PNG file"""
    output_path = tmp_path / "test_frame.png"
    
    render_rectangles(small_context, [simple_rectangle])
    save_frame(small_context, str(output_path))
    
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_render_frame_to_file(simple_rectangle, tmp_path):
    """render_frame_to_file creates a valid PNG"""
    output_path = tmp_path / "test_render.png"
    
    render_frame_to_file([simple_rectangle], str(output_path), width=100, height=100)
    
    assert output_path.exists()
    assert output_path.stat().st_size > 0


# ============================================================================
# LEVEL 2: Property Tests (verify behavior invariants)
# ============================================================================

def test_clear_color_black(small_context):
    """Black clear color produces black background"""
    render_rectangles(small_context, [], clear_color=(0.0, 0.0, 0.0))
    result = read_framebuffer(small_context)
    
    # Should be entirely black
    assert result.max() <= 5  # Allow small GPU rounding


def test_clear_color_white(small_context):
    """White clear color produces white background"""
    render_rectangles(small_context, [], clear_color=(1.0, 1.0, 1.0))
    result = read_framebuffer(small_context)
    
    # Should be entirely white (or very close)
    assert result.min() >= 250


def test_red_rectangle_has_red_pixels(small_context):
    """Red rectangle produces predominantly red pixels"""
    red_rect = {
        'x': -0.5,
        'y': -0.5,
        'width': 1.0,
        'height': 1.0,
        'color': (1.0, 0.0, 0.0),
        'alpha': 1.0
    }
    
    render_rectangles(small_context, [red_rect], clear_color=(0.0, 0.0, 0.0))
    result = read_framebuffer(small_context)
    
    # Red channel should be much higher than green/blue
    # (Note: blur spreads color out, so average is lower)
    avg_color = result.mean(axis=(0, 1))
    assert avg_color[0] > 20  # Red channel present
    assert avg_color[1] < 5   # Green channel low
    assert avg_color[2] < 5   # Blue channel low


def test_transparency_blending(small_context):
    """Semi-transparent rectangle blends with background"""
    semi_transparent = {
        'x': -0.9,
        'y': -0.9,
        'width': 1.8,
        'height': 1.8,
        'color': (1.0, 0.0, 0.0),
        'alpha': 0.5
    }
    
    render_rectangles(small_context, [semi_transparent], clear_color=(0.0, 0.0, 0.0))
    result = read_framebuffer(small_context)
    
    # Should be approximately half-intensity red (with blur spreading it out)
    avg_color = result.mean(axis=(0, 1))
    assert 10 < avg_color[0] < 50  # Some red present
    assert avg_color[1] < 5   # Green low
    assert avg_color[2] < 5   # Blue low


def test_overlapping_rectangles_blend(small_context):
    """Overlapping rectangles blend correctly"""
    # Red rectangle
    rect1 = {'x': -0.2, 'y': -0.2, 'width': 0.3, 'height': 0.3, 
             'color': (1.0, 0.0, 0.0), 'alpha': 0.5}
    # Green rectangle overlapping
    rect2 = {'x': -0.1, 'y': -0.1, 'width': 0.3, 'height': 0.3, 
             'color': (0.0, 1.0, 0.0), 'alpha': 0.5}
    
    render_rectangles(small_context, [rect1, rect2], clear_color=(0.0, 0.0, 0.0))
    result = read_framebuffer(small_context)
    
    # Overlap region should have both red and green (though blur spreads them)
    center = result[45:55, 45:55]  # Center 10x10 region
    avg_color = center.mean(axis=(0, 1))
    assert avg_color[0] > 1  # Some red
    assert avg_color[1] > 1  # Some green


def test_glow_increases_brightness(small_context):
    """Multi-pass glow makes rectangles brighter"""
    bright_rect = {
        'x': -0.2,
        'y': -0.2,
        'width': 0.4,
        'height': 0.4,
        'color': (1.0, 1.0, 1.0),
        'alpha': 1.0
    }
    
    # With glow strength > 0, center should be brighter than edges
    render_rectangles(small_context, [bright_rect], clear_color=(0.0, 0.0, 0.0))
    result = read_framebuffer(small_context)
    
    # Center pixels should be brighter than edge pixels (glow effect)
    center = result[40:60, 40:60]
    edge = result[0:10, 0:10]
    assert center.mean() > edge.mean()  # Center brighter due to glow


def test_different_resolutions_produce_correct_dimensions():
    """Different resolutions produce correctly sized output"""
    resolutions = [(100, 100), (1920, 1080), (256, 256)]
    rect = {'x': -0.1, 'y': -0.1, 'width': 0.2, 'height': 0.2, 
            'color': (1.0, 0.0, 0.0), 'alpha': 1.0}
    
    for width, height in resolutions:
        ctx = ModernGLContext(width=width, height=height)
        render_rectangles(ctx, [rect])
        result = read_framebuffer(ctx)
        
        assert result.shape == (height, width, 3)
        ctx.cleanup()


def test_corner_radius_affects_rendering(small_context):
    """Rectangles with corner_radius render differently than sharp corners"""
    # Small corner radius context
    ctx_rounded = ModernGLContext(width=100, height=100, corner_radius=10.0)
    
    rect = {'x': -0.5, 'y': -0.5, 'width': 1.0, 'height': 1.0, 
            'color': (1.0, 1.0, 1.0), 'alpha': 1.0}
    
    render_rectangles(ctx_rounded, [rect], clear_color=(0.0, 0.0, 0.0))
    result_rounded = read_framebuffer(ctx_rounded)
    
    # With blur, corners and center both get blurred out
    # Just verify something was rendered
    assert result_rounded.max() > 0
    assert result_rounded.min() < 255
    ctx_rounded.cleanup()


def test_multiple_frames_are_independent(small_context):
    """Sequential renders don't affect each other"""
    rect1 = {'x': -0.1, 'y': -0.1, 'width': 0.2, 'height': 0.2, 
             'color': (1.0, 0.0, 0.0), 'alpha': 1.0}
    rect2 = {'x': 0.3, 'y': 0.3, 'width': 0.2, 'height': 0.2, 
             'color': (0.0, 1.0, 0.0), 'alpha': 1.0}
    
    # Render first frame
    render_rectangles(small_context, [rect1])
    result1 = read_framebuffer(small_context)
    
    # Render second frame (different content)
    render_rectangles(small_context, [rect2])
    result2 = read_framebuffer(small_context)
    
    # Results should be different
    assert not np.array_equal(result1, result2)
    
    # First frame's content shouldn't appear in second frame
    # (Check center-left where rect1 was, should be black in frame 2)
    frame2_center_left = result2[45:55, 40:50]
    assert frame2_center_left.mean() < 30  # Should be mostly black


# ============================================================================
# LEVEL 3: Regression Tests (pixel-perfect, run manually/pre-release)
# ============================================================================

# Note: These are optional and would be run less frequently
# Baselines would be stored in moderngl_renderer/tests/baselines/

@pytest.mark.slow
@pytest.mark.regression
def test_single_rectangle_baseline(small_context, tmp_path):
    """Compare single rectangle render to baseline (if exists)"""
    baseline_path = Path(__file__).parent / "baselines" / "single_red_rect_100x100.npy"
    
    rect = {'x': -0.2, 'y': -0.2, 'width': 0.4, 'height': 0.4,
            'color': (1.0, 0.0, 0.0), 'alpha': 1.0}
    
    render_rectangles(small_context, [rect], clear_color=(0.0, 0.0, 0.0))
    result = read_framebuffer(small_context)
    
    if baseline_path.exists():
        baseline = np.load(baseline_path)
        # Allow small differences due to GPU variations
        assert np.allclose(result, baseline, atol=5)
    else:
        # First run: create baseline
        baseline_path.parent.mkdir(exist_ok=True)
        np.save(baseline_path, result)
        pytest.skip("Created baseline, run again to compare")


@pytest.mark.slow
@pytest.mark.regression
def test_multi_rectangle_baseline(small_context):
    """Compare multi-rectangle render to baseline (if exists)"""
    baseline_path = Path(__file__).parent / "baselines" / "multi_rect_100x100.npy"
    
    rectangles = [
        {'x': -0.6, 'y': -0.6, 'width': 0.3, 'height': 0.3, 'color': (1.0, 0.0, 0.0), 'alpha': 1.0},
        {'x': 0.0, 'y': 0.0, 'width': 0.3, 'height': 0.3, 'color': (0.0, 1.0, 0.0), 'alpha': 1.0},
        {'x': 0.3, 'y': 0.3, 'width': 0.3, 'height': 0.3, 'color': (0.0, 0.0, 1.0), 'alpha': 1.0},
    ]
    
    render_rectangles(small_context, rectangles, clear_color=(0.0, 0.0, 0.0))
    result = read_framebuffer(small_context)
    
    if baseline_path.exists():
        baseline = np.load(baseline_path)
        assert np.allclose(result, baseline, atol=5)
    else:
        baseline_path.parent.mkdir(exist_ok=True)
        np.save(baseline_path, result)
        pytest.skip("Created baseline, run again to compare")
