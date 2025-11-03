"""
GPU-Resident MIDI Renderer Shaders

Time-based vertex animation shaders for GPU-resident note rendering.
All notes uploaded once, animation happens entirely on GPU via uniforms.
"""

# Time-animated vertex shader for MIDI notes
# Animates note positions based on current time uniform
TIME_ANIMATED_VERTEX_SHADER = """
#version 330

// Per-vertex attributes (unit quad corners: 0-1)
in vec2 in_position;

// Per-instance attributes (each note - uploaded once at initialization)
in vec4 in_base_rect;     // x, y_at_strike, width, height (normalized coords)
in vec3 in_color;         // r, g, b
in vec2 in_timing;        // start_time, duration
in vec2 in_size_pixels;   // width, height in pixels

// Uniforms (updated per frame - only these change!)
uniform float u_current_time;           // Current playback time in seconds
uniform float u_pixels_per_second;      // Fall speed in pixels/second
uniform float u_strike_line_y_norm;     // Strike line position in normalized coords
uniform vec2 u_screen_size;             // Width, height in pixels
uniform float u_lookahead_time;         // How far ahead to show notes (seconds)
uniform float u_passthrough_time;       // How long after strike to show (seconds)

// Outputs to fragment shader
out vec3 v_color;
out vec2 v_texcoord;
out vec2 v_size;
out float v_alpha;          // Fade based on distance from strike line

void main() {
    float start_time = in_timing.x;
    float time_delta = u_current_time - start_time;
    
    // GPU visibility culling - discard notes outside time window
    if (time_delta < -u_lookahead_time || time_delta > u_passthrough_time) {
        // Move far off-screen (GPU will discard early)
        gl_Position = vec4(10.0, 10.0, 0.0, 1.0);
        v_alpha = 0.0;
        return;
    }
    
    // Calculate vertical position based on time
    // Note falls from top toward strike line
    float strike_line_y_pixels = (u_strike_line_y_norm + 1.0) * 0.5 * u_screen_size.y;
    float pixel_offset = time_delta * u_pixels_per_second;
    float y_pixels = strike_line_y_pixels - pixel_offset;
    
    // Convert to normalized coords (-1 to 1)
    float y_norm = (y_pixels / u_screen_size.y) * 2.0 - 1.0;
    
    // Secondary culling - notes off screen
    if (y_norm < -1.2 || y_norm > 1.2) {
        gl_Position = vec4(10.0, 10.0, 0.0, 1.0);
        v_alpha = 0.0;
        return;
    }
    
    // Build rectangle position
    vec4 rect = in_base_rect;
    rect.y = y_norm;  // Animated y position
    
    // Transform unit quad (0-1) to rectangle
    vec2 pos = rect.xy + in_position * rect.zw;
    gl_Position = vec4(pos, 0.0, 1.0);
    
    // Calculate alpha fade based on distance from strike line
    float distance_from_strike = abs(y_pixels - strike_line_y_pixels);
    float fade_distance = u_screen_size.y * 0.3;  // Fade over 30% of screen height
    v_alpha = 1.0 - smoothstep(0.0, fade_distance, distance_from_strike);
    
    // Pass through to fragment shader
    v_color = in_color;
    v_texcoord = in_position;  // 0-1 coordinates for rounded corners
    v_size = in_size_pixels;
}
"""

# Fragment shader (same as original - handles rounded corners)
TIME_ANIMATED_FRAGMENT_SHADER = """
#version 330

in vec3 v_color;
in vec2 v_texcoord;  // 0-1 texture coordinates within the rectangle
in vec2 v_size;      // Width and height of rectangle in pixels
in float v_alpha;    // Alpha from vertex shader (fade effect)

out vec4 f_color;

uniform float u_corner_radius;  // Corner radius in pixels

void main() {
    // Calculate distance from edges for rounded corners
    vec2 pixel_pos = v_texcoord * v_size;
    vec2 half_size = v_size * 0.5;
    
    // Distance from center to this pixel
    vec2 dist_from_center = abs(pixel_pos - half_size);
    
    // Corner boundaries (where rounding starts)
    vec2 corner_start = half_size - vec2(u_corner_radius);
    
    // If we're in the corner region, calculate distance from corner circle
    float corner_alpha = 1.0;
    if (dist_from_center.x > corner_start.x && dist_from_center.y > corner_start.y) {
        // Distance from corner circle center
        vec2 corner_dist = dist_from_center - corner_start;
        float dist = length(corner_dist);
        
        // Smooth anti-aliased edge (1 pixel transition)
        corner_alpha = 1.0 - smoothstep(u_corner_radius - 1.0, u_corner_radius, dist);
    }
    
    // Combine corner alpha with fade alpha
    float final_alpha = corner_alpha * v_alpha;
    
    f_color = vec4(v_color, final_alpha);
}
"""

# Static elements shader (strike line, lane markers, background)
# These don't animate, rendered from separate static buffer
STATIC_VERTEX_SHADER = """
#version 330

// Per-vertex attributes
in vec2 in_position;
in vec3 in_color;
in vec4 in_rect;          // x, y, width, height (normalized coords)
in vec2 in_size_pixels;

// Outputs
out vec3 v_color;
out vec2 v_texcoord;
out vec2 v_size;

void main() {
    vec2 pos = in_rect.xy + in_position * in_rect.zw;
    gl_Position = vec4(pos, 0.0, 1.0);
    
    v_color = in_color;
    v_texcoord = in_position;
    v_size = in_size_pixels;
}
"""

STATIC_FRAGMENT_SHADER = """
#version 330

in vec3 v_color;
in vec2 v_texcoord;
in vec2 v_size;

out vec4 f_color;

uniform float u_corner_radius;

void main() {
    // Same rounded corner logic as animated shader
    vec2 pixel_pos = v_texcoord * v_size;
    vec2 half_size = v_size * 0.5;
    vec2 dist_from_center = abs(pixel_pos - half_size);
    vec2 corner_start = half_size - vec2(u_corner_radius);
    
    float alpha = 1.0;
    if (dist_from_center.x > corner_start.x && dist_from_center.y > corner_start.y) {
        vec2 corner_dist = dist_from_center - corner_start;
        float dist = length(corner_dist);
        alpha = 1.0 - smoothstep(u_corner_radius - 1.0, u_corner_radius, dist);
    }
    
    f_color = vec4(v_color, alpha);
}
"""
