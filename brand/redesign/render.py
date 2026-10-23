import sys, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).parent
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(device_scale_factor=2)
    for name in sys.argv[1:]:
        page.goto(f'file://{HERE / name}.html', wait_until='load'); page.wait_for_timeout(500)
        el = page.query_selector('.board'); box = el.bounding_box()
        page.set_viewport_size({'width': int(box['width']), 'height': int(box['height'])})
        page.wait_for_timeout(200)
        el.screenshot(path=str(HERE / f'{name}.png'))
        print(name, int(box['width']), 'x', int(box['height']))
    b.close()
