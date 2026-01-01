from PIL import Image
from case_agent.utils.image_overlay import overlay_matches_on_pil


def test_overlay_draws_boxes(tmp_path):
    img = Image.new('RGB', (400, 300), color=(255, 255, 255))
    matches = [{'probe_bbox': {'top': 50, 'left': 60, 'bottom': 150, 'right': 160}, 'subject': 'Alice'}]
    out = overlay_matches_on_pil(img, matches, size=(200,150))
    assert out.size[0] <= 200 and out.size[1] <= 150
    # ensure the image is not identical (a simple way to check something was drawn)
    # sample a pixel on the top border of the drawn box (scaled coords)
    px = out.getpixel((50,25))
    assert px != (255,255,255), f"Expected border pixel to be non-white, got {px}"
