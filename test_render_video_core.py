"""
Unit tests for render_video_core.py - Functional Core

Tests pure image conversion and drawing functions with no side effects.
Aims for 95%+ coverage with fast, deterministic tests.
"""

import pytest
import numpy as np
from PIL import Image, ImageDraw
import cv2
from render_video_core import (
    pil_to_cv2,
    cv2_to_pil,
    draw_rounded_rectangle,
    create_cv2_canvas,
    cv2_draw_rounded_rectangle,
    cv2_composite_layer,
    cv2_draw_highlight_circle
)


# ============================================================================
# Tests for image format conversions
# ============================================================================

class TestImageConversions:
    """Tests for PIL ↔ OpenCV conversions"""
    
    def test_pil_to_cv2_rgb_image(self):
        """RGB PIL image converts to BGR OpenCV array"""
        pil_img = Image.new('RGB', (100, 100), (255, 0, 0))  # Red
        cv2_img = pil_to_cv2(pil_img)
        
        assert cv2_img.shape == (100, 100, 3)
        assert cv2_img.dtype == np.uint8
        # OpenCV uses BGR, so red becomes [0, 0, 255]
        assert cv2_img[50, 50, 2] == 255  # Red channel
        assert cv2_img[50, 50, 1] == 0    # Green channel
        assert cv2_img[50, 50, 0] == 0    # Blue channel
    
    def test_pil_to_cv2_rgba_with_alpha_compositing(self):
        """RGBA PIL image with transparency composites onto black"""
        pil_img = Image.new('RGBA', (100, 100), (255, 0, 0, 128))  # Semi-transparent red
        cv2_img = pil_to_cv2(pil_img)
        
        assert cv2_img.shape == (100, 100, 3)
        # Should be darker red due to alpha compositing onto black
        assert cv2_img[50, 50, 2] < 255  # Red channel reduced
        assert cv2_img[50, 50, 2] > 0    # But not zero
    
    def test_cv2_to_pil_basic(self):
        """OpenCV array converts to PIL Image"""
        cv2_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2_img[50, 50, :] = [255, 128, 64]  # BGR
        
        pil_img = cv2_to_pil(cv2_img)
        
        assert pil_img.size == (100, 100)
        assert pil_img.mode == 'RGB'
        # BGR in OpenCV becomes RGB in PIL
        r, g, b = pil_img.getpixel((50, 50))
        assert (r, g, b) == (64, 128, 255)  # BGR→RGB
    
    def test_roundtrip_conversion(self):
        """PIL → OpenCV → PIL should preserve image"""
        original = Image.new('RGB', (50, 50), (100, 150, 200))
        
        cv2_img = pil_to_cv2(original)
        restored = cv2_to_pil(cv2_img)
        
        assert restored.size == original.size
        assert restored.mode == original.mode
        # Colors should match
        assert original.getpixel((25, 25)) == restored.getpixel((25, 25))


# ============================================================================
# Tests for PIL drawing primitives
# ============================================================================

class TestPILDrawing:
    """Tests for PIL rounded rectangle drawing"""
    
    def test_draw_rounded_rectangle_with_fill(self):
        """Rounded rectangle should be drawn with fill"""
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        draw_rounded_rectangle(draw, (10, 10, 90, 90), radius=10, fill=(255, 0, 0, 255))
        
        # Center should be red
        assert img.getpixel((50, 50)) == (255, 0, 0, 255)
        # Corners should be transparent (outside rounded corners)
        assert img.getpixel((10, 10))[3] == 0
    
    def test_draw_rounded_rectangle_zero_radius(self):
        """Zero radius should draw regular rectangle"""
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        draw_rounded_rectangle(draw, (10, 10, 90, 90), radius=0, fill=(0, 255, 0, 255))
        
        # All corners should be filled (sharp corners)
        assert img.getpixel((11, 11))[3] > 0
        assert img.getpixel((89, 89))[3] > 0
    
    def test_draw_rounded_rectangle_zero_radius_outline_only(self):
        """Zero radius with outline only should draw rectangle outline"""
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        draw_rounded_rectangle(draw, (10, 10, 90, 90), radius=0, outline=(255, 255, 0, 255), width=2)
        
        # Edge should have outline
        assert img.getpixel((50, 11))[3] > 0
    
    def test_draw_rounded_rectangle_with_outline(self):
        """Rounded rectangle with outline only"""
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        draw_rounded_rectangle(draw, (10, 10, 90, 90), radius=10, outline=(0, 0, 255, 255), width=2)
        
        # Edge should have outline color
        # (exact pixel testing is fragile due to anti-aliasing)
        assert img.getpixel((50, 11))[2] > 200  # Blue outline at top edge


# ============================================================================
# Tests for OpenCV canvas operations
# ============================================================================

class TestOpenCVCanvas:
    """Tests for canvas creation and drawing"""
    
    def test_create_cv2_canvas_4channel(self):
        """Create BGRA canvas with correct dimensions"""
        canvas = create_cv2_canvas(100, 200, channels=4)
        
        assert canvas.shape == (200, 100, 4)
        assert canvas.dtype == np.uint8
        # Should be all zeros (transparent)
        assert np.all(canvas == 0)
    
    def test_create_cv2_canvas_3channel(self):
        """Create BGR canvas with correct dimensions"""
        canvas = create_cv2_canvas(150, 100, channels=3)
        
        assert canvas.shape == (100, 150, 3)
        assert canvas.dtype == np.uint8
        assert np.all(canvas == 0)
    
    def test_create_cv2_canvas_with_fill_color(self):
        """Canvas with fill color should be initialized"""
        canvas = create_cv2_canvas(50, 50, channels=3, fill_color=(255, 128, 64))
        
        assert np.all(canvas[:, :, 0] == 255)  # B
        assert np.all(canvas[:, :, 1] == 128)  # G
        assert np.all(canvas[:, :, 2] == 64)   # R
    
    def test_create_cv2_canvas_with_alpha_fill(self):
        """4-channel canvas with alpha fill"""
        canvas = create_cv2_canvas(50, 50, channels=4, fill_color=(255, 128, 64, 200))
        
        assert canvas.shape == (50, 50, 4)
        assert canvas[0, 0, 3] == 200  # Alpha channel


# ============================================================================
# Tests for OpenCV drawing primitives
# ============================================================================

class TestOpenCVDrawing:
    """Tests for OpenCV drawing functions"""
    
    def test_cv2_draw_rounded_rectangle_with_fill(self):
        """Draw filled rounded rectangle on OpenCV canvas"""
        canvas = create_cv2_canvas(100, 100, channels=3)
        
        cv2_draw_rounded_rectangle(canvas, (10, 10, 90, 90), radius=10, fill=(0, 0, 255))
        
        # Center should be red (BGR)
        assert canvas[50, 50, 2] == 255
        assert canvas[50, 50, 1] == 0
        assert canvas[50, 50, 0] == 0
    
    def test_cv2_draw_rounded_rectangle_zero_radius(self):
        """Zero radius draws sharp corners"""
        canvas = create_cv2_canvas(100, 100, channels=3)
        
        cv2_draw_rounded_rectangle(canvas, (20, 20, 80, 80), radius=0, fill=(255, 0, 0))
        
        # Corners should be filled (sharp rectangle)
        assert canvas[21, 21, 0] == 255  # Top-left
        assert canvas[79, 79, 0] == 255  # Bottom-right
    
    def test_cv2_draw_rounded_rectangle_zero_radius_outline_only(self):
        """Zero radius with outline only should draw rectangle outline"""
        canvas = create_cv2_canvas(100, 100, channels=3)
        
        cv2_draw_rounded_rectangle(canvas, (20, 20, 80, 80), radius=0, outline=(255, 255, 0), width=2)
        
        # Edge should have outline color
        assert canvas[50, 21, 1] > 200  # Green channel at edge
    
    def test_cv2_draw_rounded_rectangle_with_outline(self):
        """Outline drawing works"""
        canvas = create_cv2_canvas(100, 100, channels=3)
        
        cv2_draw_rounded_rectangle(canvas, (10, 10, 90, 90), radius=5, outline=(0, 255, 0), width=2)
        
        # Edge should have outline color (green in BGR)
        # Note: exact pixels vary due to anti-aliasing
        assert canvas[50, 11, 1] > 200  # Green channel at edge
    
    def test_cv2_composite_layer_no_alpha(self):
        """Composite 3-channel overlay onto 3-channel base"""
        base = create_cv2_canvas(100, 100, channels=3, fill_color=(100, 100, 100))
        overlay = create_cv2_canvas(100, 100, channels=3, fill_color=(200, 200, 200))
        
        cv2_composite_layer(base, overlay, alpha=0.5)
        
        # Should be 50% blend: (100 * 0.5) + (200 * 0.5) = 150
        assert np.allclose(base[50, 50, :], 150, atol=1)
    
    def test_cv2_composite_layer_with_alpha_channel(self):
        """Composite 4-channel overlay with alpha onto 3-channel base"""
        base = create_cv2_canvas(100, 100, channels=3, fill_color=(0, 0, 0))
        overlay = create_cv2_canvas(100, 100, channels=4, fill_color=(255, 255, 255, 128))  # 50% alpha
        
        cv2_composite_layer(base, overlay, alpha=1.0)
        
        # Should be ~50% white due to alpha blending
        assert np.allclose(base[50, 50, :], 127, atol=5)
    
    def test_cv2_composite_layer_full_alpha(self):
        """Full alpha overlay replaces base"""
        base = create_cv2_canvas(100, 100, channels=3, fill_color=(100, 100, 100))
        overlay = create_cv2_canvas(100, 100, channels=3, fill_color=(200, 200, 200))
        
        cv2_composite_layer(base, overlay, alpha=1.0)
        
        # Base should be completely replaced
        assert np.all(base == 200)
    
    def test_cv2_draw_highlight_circle_basic(self):
        """Draw highlight circle on canvas"""
        canvas = create_cv2_canvas(200, 200, channels=4)
        
        cv2_draw_highlight_circle(
            canvas, center_x=100, center_y=100,
            max_size=30.0, color=(255, 0, 0),  # Red
            circle_alpha=255, pulse=0.5, glow_layers=0
        )
        
        # Center should have red color (converted to BGR)
        assert canvas[100, 100, 2] > 200  # Red channel (BGR index 2)
        assert canvas[100, 100, 3] > 200  # Alpha channel
    
    def test_cv2_draw_highlight_circle_pulse_affects_outline(self):
        """Pulse value affects outline thickness"""
        canvas1 = create_cv2_canvas(200, 200, channels=4)
        canvas2 = create_cv2_canvas(200, 200, channels=4)
        
        cv2_draw_highlight_circle(
            canvas1, 100, 100, 30.0, (255, 0, 0),
            circle_alpha=255, pulse=0.0, glow_layers=0
        )
        cv2_draw_highlight_circle(
            canvas2, 100, 100, 30.0, (255, 0, 0),
            circle_alpha=255, pulse=1.0, glow_layers=0
        )
        
        # Higher pulse should create different outline
        # (exact comparison difficult due to anti-aliasing)
        assert not np.array_equal(canvas1, canvas2)


# ============================================================================
# Integration tests
# ============================================================================

class TestRenderingIntegration:
    """Integration tests combining multiple functions"""
    
    def test_full_rendering_pipeline(self):
        """Test complete pipeline: canvas → draw → convert"""
        # Create canvas
        canvas = create_cv2_canvas(200, 200, channels=3, fill_color=(50, 50, 50))
        
        # Draw shapes
        cv2_draw_rounded_rectangle(canvas, (50, 50, 150, 150), radius=20, fill=(255, 0, 0))
        cv2_draw_rounded_rectangle(canvas, (75, 75, 125, 125), radius=10, fill=(0, 255, 0))
        
        # Convert to PIL
        pil_img = cv2_to_pil(canvas)
        
        # Verify result
        assert pil_img.size == (200, 200)
        assert pil_img.mode == 'RGB'
        
        # Center should be green (last drawn)
        r, g, b = pil_img.getpixel((100, 100))
        assert g > 200
    
    def test_alpha_compositing_workflow(self):
        """Test layered compositing workflow"""
        # Base layer
        base = create_cv2_canvas(150, 150, channels=3, fill_color=(0, 0, 0))
        
        # Overlay layer with alpha
        overlay = create_cv2_canvas(150, 150, channels=4, fill_color=(255, 255, 255, 0))
        cv2_draw_highlight_circle(
            overlay, 75, 75, 40.0, (255, 0, 0),
            circle_alpha=200, pulse=0.5, glow_layers=0
        )
        
        # Composite
        cv2_composite_layer(base, overlay, alpha=1.0)
        
        # Center should have red color blended with black
        assert base[75, 75, 2] > 100  # Some red present
        assert base[75, 75, 2] < 255  # But not full intensity due to alpha


# ============================================================================
# Edge case and property tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_size_canvas(self):
        """Zero-size canvas should be handled gracefully"""
        canvas = create_cv2_canvas(0, 0, channels=3)
        assert canvas.shape == (0, 0, 3)
    
    def test_single_pixel_canvas(self):
        """1x1 canvas should work"""
        canvas = create_cv2_canvas(1, 1, channels=3, fill_color=(255, 0, 0))
        assert canvas.shape == (1, 1, 3)
        assert canvas[0, 0, 0] == 255
    
    def test_large_canvas_allocation(self):
        """Large canvas should allocate correctly"""
        canvas = create_cv2_canvas(1000, 1000, channels=4)
        assert canvas.shape == (1000, 1000, 4)
        assert canvas.nbytes == 1000 * 1000 * 4  # 4MB
    
    def test_pil_to_cv2_maintains_dimensions(self):
        """Conversion preserves dimensions exactly"""
        for width, height in [(50, 100), (100, 50), (100, 100), (1, 200)]:
            pil_img = Image.new('RGB', (width, height))
            cv2_img = pil_to_cv2(pil_img)
            assert cv2_img.shape == (height, width, 3)  # Note: cv2 is (H, W, C)
    
    def test_compositing_edge_alpha_values(self):
        """Test alpha edge values 0 and 1"""
        base = create_cv2_canvas(100, 100, channels=3, fill_color=(100, 100, 100))
        overlay = create_cv2_canvas(100, 100, channels=3, fill_color=(200, 200, 200))
        
        # Alpha = 0 should not change base
        cv2_composite_layer(base, overlay, alpha=0.0)
        assert np.all(base == 100)
        
        # Alpha = 1 should fully replace
        cv2_composite_layer(base, overlay, alpha=1.0)
        assert np.all(base == 200)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
