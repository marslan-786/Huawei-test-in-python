import asyncio
import random
import time
import math

# Huawei Tile Swap is usually 4 Columns x 2 Rows
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Initializing Grid System...")
    
    # 1. FIND THE CAPTCHA FRAME
    frames = page.frames
    captcha_frame = None
    
    # Frame dhoondo jisme image ho
    for frame in frames:
        try:
            if await frame.locator(".uc-captcha-drag-area").count() > 0 or \
               await frame.locator("canvas").count() > 0:
                captcha_frame = frame
                break
        except: continue
    
    # Fallback to main page if no frame found (Sometimes popup is on main page)
    if not captcha_frame:
        print("⚠️ Frame not found, trying main page context...")
        captcha_frame = page

    # 2. LOCATE CAPTCHA CONTAINER
    # Try multiple selectors used by Huawei
    container = captcha_frame.locator(".uc-captcha-drag-area").first
    if await container.count() == 0:
        container = captcha_frame.locator("#captcha-container").first
    
    if await container.count() == 0:
        print("❌ Captcha Container Not Found!")
        return False

    # Get Coordinates
    box = await container.bounding_box()
    if not box:
        print("❌ Box coordinates missing")
        return False

    print(f"📏 Captcha Found: {box['width']}x{box['height']}")

    # 3. DRAW GRID (Visual Debugging)
    tile_width = box['width'] / COLS
    tile_height = box['height'] / ROWS
    
    def get_tile_center(index):
        row = math.floor(index / COLS)
        col = index % COLS
        x = box['x'] + (col * tile_width) + (tile_width / 2)
        y = box['y'] + (row * tile_height) + (tile_height / 2)
        return x, y

    # Draw Yellow Dots on Screen
    for i in range(ROWS * COLS):
        tx, ty = get_tile_center(i)
        await page.evaluate(f"""
            var dot = document.createElement('div');
            dot.style.position = 'absolute';
            dot.style.left = '{tx}px';
            dot.style.top = '{ty}px';
            dot.style.width = '20px';
            dot.style.height = '20px';
            dot.style.backgroundColor = 'yellow';
            dot.style.color = 'black';
            dot.style.fontWeight = 'bold';
            dot.style.textAlign = 'center';
            dot.style.borderRadius = '50%';
            dot.style.zIndex = '999999';
            dot.innerText = '{i}';
            document.body.appendChild(dot);
        """)

    # Screenshot with Grid
    await asyncio.sleep(1)
    await page.screenshot(path=f"./captures/{session_id}_06_GRID_READY.jpg")
    print("📸 Grid Screenshot Saved!")

    # 4. EXECUTE TEST SWAP (Tile 0 <-> Tile 4)
    # Ye hum check karne k liye kar rahay hain k drag kaam kar raha hai ya nahi
    source_idx = 0 # Top-Left
    target_idx = 4 # Bottom-Left
    
    sx, sy = get_tile_center(source_idx)
    tx, ty = get_tile_center(target_idx)
    
    print(f"🔄 SWAPPING Tile {source_idx} -> Tile {target_idx}")
    
    # MOUSE ACTION
    # 1. Move to Source
    await page.mouse.move(sx, sy, steps=5)
    await asyncio.sleep(0.5)
    
    # 2. Grab (Down)
    await page.mouse.down()
    await asyncio.sleep(0.5)
    
    # 3. Drag to Target (Slowly)
    await page.mouse.move(tx, ty, steps=20) 
    await asyncio.sleep(0.5)
    
    # 4. Drop (Up)
    await page.mouse.up()
    
    print("✅ Swap Done! Waiting for result...")
    await asyncio.sleep(3)
    
    return True