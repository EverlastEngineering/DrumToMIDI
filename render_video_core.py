"""
Video Rendering Core - Functional Core

Pure functions for image conversion, canvas operations, and drawing primitives.
No side effects: no file I/O, no OpenGL/GPU context, no logging.

Architecture: Functional core (this file) called by imperative shell (render_midi_video_shell.py)
"""

from typing import Tuple, Optional
import numpy as np  # type: ignore
from PIL import Image, ImageDraw  # type: ignore
import cv2  # type: ignore


# ============================================================================
# Image Format Conversions
# ============================================================================

def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """
    Convert PIL Image to OpenCV array with proper alpha compositing.
    
    Pure function - handles RGBA by compositing onto black background.
    
    Args:
        pil_image: PIL Image in any mode (RGBA, RGB, etc.)
    
    Returns:
        OpenCV numpy array in BGR format (3 channels)
    
    Examples:
        >>> img = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        >>> cv2_img = pil_to_cv2(img)
        >>> cv2_img.shape
        (100, 100, 3)
    """
    # If image has alpha channel, composite it onto black background
    if pil_image.mode == 'RGBA':
        # Create black background with alpha
        background = Image.new('RGBA', pil_image.size, (0, 0, 0, 255))
        # Composite using alpha blending
        composited = Image.alpha_composite(background, pil_image)
        # Convert to RGB for OpenCV
        pil_image = composited.convert('RGB')
    
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
    """
    Convert OpenCV array to PIL Image.
    
    Pure function - simple color space conversion.
    
    Args:
        cv2_image: OpenCV numpy array in BGR format
    
    Returns:
        PIL Image in RGB format
    
    Examples:
        >>> cv2_img = np.zeros((100, 100, 3), dtype=np.uint8)
        >>> pil_img = cv2_to_pil(cv2_img)
        >>> pil_img.mode
        'RGB'
    """
    return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))


# ============================================================================
# PIL Drawing Primitives
# ============================================================================

def draw_rounded_rectangle(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int, int, int],
    radius: int,
    fill: Optional[Tuple[int, int, int, int]] = None,
    outline: Optional[Tuple[int, int, int, int]] = None,
    width: int = 1
) -> None:
    """
    Draw anti-aliased rounded rectangle using PIL.
    
    Pure function (modifies draw object but has no other side effects).
    
    Args:
        draw: PIL ImageDraw object to draw on
        xy: Bounding box (x1, y1, x2, y2)
        radius: Corner radius in pixels (0 for sharp corners)
        fill: Fill color tuple (R, G, B, A) or None
        outline: Outline color tuple (R, G, B, A) or None
        width: Outline width in pixels
    
    Notes:
        - If radius <= 0, draws regular rectangle
        - Uses PIL's built-in rounded_rectangle for anti-aliasing
    """
    if radius <= 0:
        if fill:
            draw.rectangle(xy, fill=fill)
        if outline:
            draw.rectangle(xy, outline=outline, width=width)
        return
    
    # Use PIL's built-in rounded rectangle for better anti-aliasing
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


# ============================================================================
# OpenCV Canvas Operations
# ============================================================================

def create_cv2_canvas(
    width: int,
    height: int,
    channels: int = 4,
    fill_color: Optional[Tuple[int, ...]] = None
) -> np.ndarray:
    """
    Create OpenCV canvas (NumPy array) for drawing.
    
    Pure function - allocates new array.
    
    Args:
        width: Canvas width in pixels
        height: Canvas height in pixels
        channels: 3 for BGR, 4 for BGRA
        fill_color: Initial fill color (B, G, R) or (B, G, R, A). None for transparent/black.
    
    Returns:
        NumPy array ready for cv2 drawing operations
    
    Examples:
        >>> canvas = create_cv2_canvas(100, 100, channels=4, fill_color=(0, 0, 0, 0))
        >>> canvas.shape
        (100, 100, 4)
        >>> canvas.dtype
        dtype('uint8')
    """
    if channels == 4:
        canvas = np.zeros((height, width, 4), dtype=np.uint8)
        if fill_color:
            canvas[:] = fill_color
    else:
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        if fill_color:
            canvas[:] = fill_color
    return canvas


def cv2_draw_rounded_rectangle(
    canvas: np.ndarray,
    xy: Tuple[int, int, int, int],
    radius: int,
    fill: Optional[Tuple[int, ...]] = None,
    outline: Optional[Tuple[int, ...]] = None,
    width: int = 1
) -> None:
    """
    Draw rounded rectangle on OpenCV canvas.
    
    Modifies canvas in-place (functional core with mutable optimization).
    
    Args:
        canvas: NumPy array to draw on (modified in-place)
        xy: Bounding box (x1, y1, x2, y2)
        radius: Corner radius in pixels (0 for sharp corners)
        fill: Fill color (B, G, R) or (B, G, R, A)
        outline: Outline color (B, G, R) or (B, G, R, A)
        width: Outline width in pixels
    
    Notes:
        - Uses circles at corners for rounded effect
        - Anti-aliased drawing (cv2.LINE_AA)
    """
    x1, y1, x2, y2 = xy
    
    if radius <= 0:
        # Simple rectangle
        if fill:
            cv2.rectangle(canvas, (x1, y1), (x2, y2), fill, -1, cv2.LINE_AA)
        if outline:
            cv2.rectangle(canvas, (x1, y1), (x2, y2), outline, width, cv2.LINE_AA)
        return
    
    # Draw filled rounded rectangle using multiple primitives
    if fill:
        # Main body rectangles
        cv2.rectangle(canvas, (x1 + radius, y1), (x2 - radius, y2), fill, -1, cv2.LINE_AA)
        cv2.rectangle(canvas, (x1, y1 + radius), (x2, y2 - radius), fill, -1, cv2.LINE_AA)
        
        # Corner circles
        cv2.circle(canvas, (x1 + radius, y1 + radius), radius, fill, -1, cv2.LINE_AA)
        cv2.circle(canvas, (x2 - radius, y1 + radius), radius, fill, -1, cv2.LINE_AA)
        cv2.circle(canvas, (x1 + radius, y2 - radius), radius, fill, -1, cv2.LINE_AA)
        cv2.circle(canvas, (x2 - radius, y2 - radius), radius, fill, -1, cv2.LINE_AA)
    
    # Draw outline (simplified - just draws regular rounded rect outline)
    if outline:
        # For outline, use rectangles at edges
        cv2.rectangle(canvas, (x1 + radius, y1), (x2 - radius, y2), outline, width, cv2.LINE_AA)
        cv2.rectangle(canvas, (x1, y1 + radius), (x2, y2 - radius), outline, width, cv2.LINE_AA)


def cv2_composite_layer(
    base: np.ndarray,
    overlay: np.ndarray,
    alpha: float = 1.0
) -> None:
    """
    Composite overlay onto base using alpha blending.
    
    Modifies base in-place (functional core with mutable optimization).
    
    Args:
        base: Base canvas (BGR, 3-channel) - modified in-place
        overlay: Overlay canvas (BGRA, 4-channel with alpha) or (BGR, 3-channel)
        alpha: Additional alpha multiplier (0.0 to 1.0)
    
    Notes:
        - If overlay has no alpha channel, performs simple weighted blend
        - Alpha formula: base * (1 - alpha) + overlay * alpha
    
    Examples:
        >>> base = np.zeros((100, 100, 3), dtype=np.uint8)
        >>> overlay = np.ones((100, 100, 4), dtype=np.uint8) * 255
        >>> cv2_composite_layer(base, overlay, alpha=0.5)
        >>> base[0, 0, 0]  # Should be ~127 (50% blend)
        127
    """
    if overlay.shape[2] != 4:
        # No alpha channel, simple copy or weighted blend
        if alpha >= 1.0:
            base[:] = overlay
        else:
            cv2.addWeighted(base, 1.0 - alpha, overlay, alpha, 0, base)
        return
    
    # Extract alpha channel and apply multiplier
    overlay_alpha = (overlay[:, :, 3] / 255.0 * alpha).astype(np.float32)
    
    # Expand alpha to match BGR channels
    overlay_alpha_3ch = np.stack([overlay_alpha] * 3, axis=2)
    
    # Alpha blending: base * (1 - alpha) + overlay * alpha
    base[:, :, :] = (base[:, :, :] * (1 - overlay_alpha_3ch) + 
                     overlay[:, :, :3] * overlay_alpha_3ch).astype(np.uint8)


def cv2_draw_highlight_circle(
    canvas: np.ndarray,
    center_x: int,
    center_y: int,
    max_size: float,
    color: Tuple[int, int, int],
    circle_alpha: int,
    pulse: float,
    glow_layers: int = 0
) -> None:
    """
    Draw pulsing highlight circle using OpenCV.
    
    Modifies canvas in-place (functional core with mutable optimization).
    
    Args:
        canvas: BGRA canvas to draw on (modified in-place)
        center_x: X coordinate of circle center
        center_y: Y coordinate of circle center
        max_size: Radius of main circle
        color: RGB color tuple (will be converted to BGR)
        circle_alpha: Alpha value for main circle (0-255)
        pulse: Pulse factor (0.0 to 1.0) for animation
        glow_layers: Number of glow layers (0 = disabled for performance)
    
    Notes:
        - Color is converted from RGB to BGR internally
        - Pre-multiplies alpha for performance
        - Glow layers parameter ignored (set to 0 for performance)
    """
    # Convert RGB to BGR for OpenCV
    bgr_color = (color[2], color[1], color[0])
    
    # Main circle - pre-multiply alpha for speed
    main_color = tuple(int(c * circle_alpha / 255.0) for c in bgr_color)
    cv2.circle(canvas, (center_x, center_y), int(max_size),
               (*main_color, circle_alpha), -1, cv2.LINE_AA)
    
    # Bright outline (pulse affects thickness)
    outline_width = int(2 + 2 * pulse)
    bright_color = tuple(min(255, int(c + (255 - c) * 0.8)) for c in bgr_color)
    cv2.circle(canvas, (center_x, center_y), int(max_size),
               (*bright_color, 255), outline_width, cv2.LINE_AA)
