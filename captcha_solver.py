import asyncio
import math
import random

# Grid Configuration (4x2)
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Calculating Human-Like Drag (0 -> 7)...")
    
    # 1. FIND FRAME (Text Sandwich Logic)
    frames = page.frames
    captcha_frame = None
    for frame in frames:
        try:
            if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                captcha_frame = frame
                break
        except: continue
    
    if not captcha_frame and len(frames) > 1: captcha_frame = frames[-1]
    if not captcha_frame:
        print("❌ Captcha Frame Not Found")
        return False

    # 2. FIND BOUNDARIES
    header = captcha_frame.get_by_text("Please complete verification", exact=False).first
    footer = captcha_frame.get_by_text("swap 2 tiles", exact=False).first
    
    if await header.count() == 0:
        print("❌ Header text missing")
        return False

    head_box = await header.bounding_box()
    foot_box = await footer.bounding_box()
    
    if not head_box or not foot_box:
        print("❌ Bounds missing")
        return False

    # 3. CALCULATE GRID
    top_pad = 10
    bot_pad = 10
    
    grid_y = head_box['y'] + head_box['height'] + top_pad
    grid_height = foot_box['y'] - grid_y - bot_pad
    
    # Use Footer Width as reference for Grid Width (More accurate)
    grid_width = foot_box['width'] 
    # Center X based on footer X
    grid_x = foot_box['x']
    
    # Safety Check
    if grid_height < 50: grid_height = 150

    print(f"📏 Grid: X={int(grid_x)}, Y={int(grid_y)}, W={int(grid_width)}, H={int(grid_height)}")

    # 4. TILE CENTERS
    tile_width = grid_width / COLS
    tile_height = grid_height / ROWS
    
    def get_tile_center(index):
        row = math.floor(index / COLS)
        col = index % COLS
        x = grid_x + (col * tile_width) + (tile_width / 2)
        y = grid_y + (row * tile_height) + (tile_height / 2)
        return x, y

    # Swap 0 -> 7
    sx, sy = get_tile_center(0)
    tx, ty = get_tile_center(7)

    # --- 5. VISUAL DOTS (DEBUG) ---
    try:
        await captcha_frame.evaluate(f"""
            var d1 = document.createElement('div');
            d1.style.position = 'absolute'; left='{sx}px'; top='{sy}px';
            d1.style.width='20px'; height='20px'; background='blue'; 
            d1.style.borderRadius='50%'; d1.style.border='2px solid white'; d1.style.zIndex='999999';
            document.body.appendChild(d1);
            
            var d2 = document.createElement('div');
            d2.style.position = 'absolute'; left='{tx}px'; top='{ty}px';
            d2.style.width='20px'; height='20px'; background='lime'; 
            d2.style.borderRadius='50%'; d2.style.border='2px solid white'; d2.style.zIndex='999999';
            document.body.appendChild(d2);
        """)
    except: pass

    await asyncio.sleep(0.5)

    # --- 6. HUMAN DRAG EXECUTION ---
    print(f"🖱️ Moving to Source...")
    # Thora sa random offset add kar rahe hain taake robotic na lagay
    await page.mouse.move(sx + random.randint(-2, 2), sy + random.randint(-2, 2), steps=10)
    await asyncio.sleep(0.3)
    
    print("✊ GRABBING (With Wiggle)...")
    await page.mouse.down()
    await asyncio.sleep(0.5) # Wait to grab
    
    # WIGGLE (Hila jula k confirm karna k tile pakri gayi)
    await page.mouse.move(sx + 5, sy, steps=5)
    await page.mouse.move(sx - 5, sy, steps=5)
    await page.mouse.move(sx, sy, steps=5)
    await asyncio.sleep(0.2)
    
    print("🚀 DRAGGING SLOWLY...")
    # Steps=100 means very smooth, slow movement
    await page.mouse.move(tx, ty, steps=100) 
    
    # OVERSHOOT (Thora agay ja k wapis ana)
    await page.mouse.move(tx + 5, ty + 5, steps=10)
    await asyncio.sleep(0.2)
    await page.mouse.move(tx, ty, steps=10)
    
    await asyncio.sleep(0.5) # Hold at target
    
    print("✋ RELEASING...")
    await page.mouse.up()
    
    return True