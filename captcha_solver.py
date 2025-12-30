import asyncio
import math

# Grid 4x2
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Hold & Drag (0 -> 7)...")
    
    # 1. FIND FRAME
    frames = page.frames
    captcha_frame = None
    for frame in frames:
        try:
            if await frame.locator(".uc-captcha-drag-area").count() > 0:
                captcha_frame = frame
                break
        except: continue
    
    if not captcha_frame and len(frames) > 1: captcha_frame = frames[-1]
    if not captcha_frame: return False

    # 2. BOX
    container = captcha_frame.locator(".uc-captcha-drag-area").first
    if await container.count() == 0: container = captcha_frame.locator("#captcha-container").first
    box = await container.bounding_box()
    if not box: return False

    # 3. COORDINATES
    tile_width = box['width'] / COLS
    tile_height = box['height'] / ROWS
    
    def get_tile_center(index):
        row = math.floor(index / COLS)
        col = index % COLS
        x = box['x'] + (col * tile_width) + (tile_width / 2)
        y = box['y'] + (row * tile_height) + (tile_height / 2)
        return x, y

    # --- SWAP 0 -> 7 ---
    source_idx = 0  # First Tile (Top Left)
    target_idx = 7  # Last Tile (Bottom Right)
    
    sx, sy = get_tile_center(source_idx)
    tx, ty = get_tile_center(target_idx)

    # VISUAL MARKERS
    await page.evaluate(f"""
        var d1 = document.createElement('div');
        d1.style.position = 'absolute'; left='{sx}px'; top='{sy}px';
        d1.style.width='20px'; height='20px'; background='blue'; borderRadius='50%'; zIndex='999999';
        document.body.appendChild(d1);
        
        var d2 = document.createElement('div');
        d2.style.position = 'absolute'; left='{tx}px'; top='{ty}px';
        d2.style.width='20px'; height='20px'; background='lime'; borderRadius='50%'; zIndex='999999';
        document.body.appendChild(d2);
    """)
    await asyncio.sleep(0.5)

    # --- EXECUTE FORCE DRAG ---
    print(f"🖱️ Moving to Source {source_idx}...")
    await page.mouse.move(sx, sy, steps=5)
    await asyncio.sleep(0.5)
    
    print("✊ HOLDING (Mouse Down)...")
    await page.mouse.down()
    await asyncio.sleep(1) # FORCE HOLD (1 Second)
    
    print(f"🖱️ Dragging to Target {target_idx}...")
    await page.mouse.move(tx, ty, steps=25) # Slow Drag
    await asyncio.sleep(1) # HOLD AT TARGET
    
    print("✋ RELEASING (Mouse Up)...")
    await page.mouse.up()
    
    return True