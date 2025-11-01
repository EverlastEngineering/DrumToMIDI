# Shader Architecture for ModernGL Renderer

## Current Architecture (Phase 3)

### Single-Pass System
```
Input (rectangles) → Vertex Shader → Fragment Shader → Framebuffer → Output
```

**Components:**
- `ModernGLContext`: Creates GPU context, framebuffer, shaders
- `render_rectangles()`: Batch uploads, single draw call
- One shader program: vertex + fragment for rounded rectangles

**Strengths:**
- Fast (single pass)
- Simple pipeline
- Easy to test

**Limitations:**
- No post-processing
- No texture-based effects
- Effects must be baked into fragment shader

---

## Adding Effects: Three Approaches

### Approach 1: Multi-Pass with Post-Processing ⭐ RECOMMENDED

**Architecture:**
```
Pass 1: Scene → Texture
Pass 2: Glow extraction → Texture  
Pass 3: Gaussian blur (H) → Texture
Pass 4: Gaussian blur (V) → Texture
Pass 5: Composite (scene + blur) → Final
```

**Implementation:**
```python
class MultiPassRenderer:
    def __init__(self, ctx, width, height):
        # Create multiple framebuffers
        self.fbo_scene = ctx.framebuffer(ctx.texture((w, h), 4))
        self.fbo_glow = ctx.framebuffer(ctx.texture((w, h), 4))
        self.fbo_blur_h = ctx.framebuffer(ctx.texture((w, h), 4))
        self.fbo_blur_v = ctx.framebuffer(ctx.texture((w, h), 4))
        
        # Create fullscreen quad for post-processing
        self.quad = create_fullscreen_quad(ctx)
        
        # Load effect shaders
        self.blur_h_shader = load_shader('blur_horizontal.glsl')
        self.blur_v_shader = load_shader('blur_vertical.glsl')
        self.composite_shader = load_shader('composite.glsl')
    
    def render_frame(self, rectangles):
        # Pass 1: Render scene normally
        self.fbo_scene.use()
        render_rectangles(rectangles)
        
        # Pass 2: Extract bright elements for glow
        self.fbo_glow.use()
        self.glow_extract_shader['scene'].value = self.fbo_scene.color_attachments[0]
        self.quad.render()
        
        # Pass 3-4: Two-pass Gaussian blur
        self.fbo_blur_h.use()
        self.blur_h_shader['input'].value = self.fbo_glow.color_attachments[0]
        self.quad.render()
        
        self.fbo_blur_v.use()
        self.blur_v_shader['input'].value = self.fbo_blur_h.color_attachments[0]
        self.quad.render()
        
        # Pass 5: Composite
        self.ctx.screen.use()  # Or final framebuffer
        self.composite_shader['scene'].value = self.fbo_scene.color_attachments[0]
        self.composite_shader['glow'].value = self.fbo_blur_v.color_attachments[0]
        self.quad.render()
```

**Pros:**
- Industry standard (used in AAA games)
- Highest quality results
- Flexible (can add more passes)
- Clean separation of concerns

**Cons:**
- Multiple render passes = slower
- More VRAM usage
- More complex code

**Performance:**
- 5 passes @ 1080p ≈ 5-10ms total
- Still 100+ FPS for full pipeline

---

### Approach 2: Fragment Shader Effects

**Add effect directly to fragment shader:**
```glsl
// In fragment shader
void main() {
    // Distance from strike line (passed as uniform)
    float dist_to_strike = abs(v_world_y - u_strike_line_y);
    
    // Calculate glow intensity
    float glow = smoothstep(0.2, 0.0, dist_to_strike);
    
    // Base color
    vec4 color = vec4(v_color, alpha);
    
    // Add glow
    color.rgb += v_color * glow * 0.5;
    
    f_color = color;
}
```

**Pros:**
- Single pass (fast)
- No pipeline changes needed
- Easy to implement

**Cons:**
- Limited effect quality (no blur)
- Glow is per-rectangle, not screen-space
- Can't do complex effects

**Use For:**
- Simple effects (brightness, pulsing)
- Per-note highlights
- Color shifts

---

### Approach 3: Geometry-Based (What We Tried)

**Render multiple rectangles for blur approximation:**
```python
# Create glow layers
for size in [3.0, 2.0, 1.5]:
    glow_rect = {
        'x': rect['x'] - extra_width,
        'y': rect['y'] - extra_height,
        'width': rect['width'] * size,
        'height': rect['height'] * size,
        'color': rect['color'],
        'brightness': 0.1 / size
    }
```

**Pros:**
- No shader changes
- Simple implementation

**Cons:**
- Looks bad (harsh edges)
- No smooth falloff
- Expensive (many rectangles)
- Not a real glow

**Verdict:** ❌ Don't use this

---

## Recommendation for Phase 4

### Hybrid Approach

**For immediate integration:**
1. Keep single-pass renderer as-is
2. Add simple fragment shader effects:
   - Brightness pulsing at strike line
   - Color intensity based on velocity
   - Simple highlight on hit

**For Phase 4.5 (Polish):**
1. Implement multi-pass post-processing
2. Add Gaussian blur for quality glow
3. Add motion blur
4. Add screen-space effects

### Implementation Strategy

**Step 1: Refactor ModernGLContext**
```python
class ModernGLContext:
    def __init__(self, width, height, enable_post_fx=False):
        self.enable_post_fx = enable_post_fx
        
        if enable_post_fx:
            # Create multiple framebuffers
            self.fbo_scene = ...
            self.fbo_effects = ...
            # Load post-processing shaders
            self.post_fx_shaders = ...
        else:
            # Single framebuffer (current behavior)
            self.fbo = ...
```

**Step 2: Add Post-Processing Pipeline**
```python
def render_with_effects(ctx, rectangles, effects_config):
    if not ctx.enable_post_fx:
        # Fast path: render directly
        render_rectangles(ctx, rectangles)
    else:
        # Multi-pass with effects
        render_scene_pass(ctx, rectangles)
        apply_glow_pass(ctx, effects_config.glow)
        apply_blur_passes(ctx)
        composite_pass(ctx)
```

**Step 3: Backward Compatibility**
```python
# Old code still works
render_frame_to_file(rectangles, 'output.png')

# New code opts into effects
render_frame_to_file(
    rectangles, 
    'output.png',
    effects={'glow': True, 'blur_radius': 5.0}
)
```

---

## Conclusion

**We didn't build it wrong!** The current architecture is:
- ✅ Correct for single-pass rendering
- ✅ Fast and efficient
- ✅ Easy to test and maintain

**To add effects properly:**
1. Add multi-pass support to `ModernGLContext` (optional flag)
2. Create fullscreen quad renderer for post-processing
3. Implement blur shaders (horizontal + vertical)
4. Add composite shader
5. Keep single-pass as default for speed

**Current code remains valid** - we just add a parallel path for when effects are needed.

The architecture is actually well-designed for extension!
