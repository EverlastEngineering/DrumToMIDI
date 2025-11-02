---
applyTo: '**'
---
When testing, once you're sure the docker container is running and stable, use the following commands to run tests inside the container:

## Quick Test Commands

**Run all tests with coverage (recommended):**
```bash
docker exec -it DrumToMIDI-midi bash -c "cd /app && pytest"
```

Find test files by searching for `import pytest`.

## Test Coverage

Attempt to maintain coverage on functional core code.

## Testing GPU/Imperative Shell Code

For GPU operations and imperative shells (code with side effects), use a 3-tier integration testing approach:

### Level 1: Smoke Tests
Fast sanity checks that run on every commit (~0.3 seconds). Verify:
- Context creation/cleanup doesn't crash
- Rendering produces valid output dimensions
- Basic operations complete without errors
- Empty scenes and single items render

**Purpose**: Catch catastrophic failures immediately.

### Level 2: Property Tests  
Verify behavior invariants, not exact outputs (~0.5 seconds). Test properties like:
- Color channels are correct (red objects have red > green/blue)
- Transparency blending works
- Multi-pass effects increase brightness appropriately
- Different resolutions produce correctly sized output
- Sequential renders are independent

**Purpose**: Robust to implementation changes. Adding new effects or changing blur radius won't break these tests.

**Coverage**: Level 2 tests alone provide ~85-90% coverage of GPU shell code.

### Level 3: Regression Tests
Pixel-perfect baseline comparisons. Mark with `@pytest.mark.slow` and `@pytest.mark.regression`.
Run manually or pre-release only (~2-5 seconds).

**Purpose**: Catch subtle visual changes before release.

**Example structure**:
```python
def test_render_produces_valid_output(gpu_context):
    """Level 1: Smoke test - just verify it works"""
    render_scene(gpu_context, test_data)
    result = read_output(gpu_context)
    assert result.shape == (1080, 1920, 3)
    assert result.dtype == np.uint8

def test_red_objects_have_red_pixels(gpu_context):
    """Level 2: Property test - verify behavior"""
    render_scene(gpu_context, red_rectangle)
    result = read_output(gpu_context)
    avg_color = result.mean(axis=(0, 1))
    assert avg_color[0] > avg_color[1]  # Red > green
    assert avg_color[0] > avg_color[2]  # Red > blue

@pytest.mark.slow
@pytest.mark.regression
def test_matches_baseline(gpu_context):
    """Level 3: Regression test - exact comparison"""
    render_scene(gpu_context, test_data)
    result = read_output(gpu_context)
    baseline = np.load('tests/baselines/scene.npy')
    assert np.allclose(result, baseline, atol=5)
```

**Key principle**: Test the public interface, not implementation details. Tests should survive refactoring.