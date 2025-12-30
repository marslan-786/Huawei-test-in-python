import asyncio
import math
import random

# Grid Configuration (4x2)
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Calculating GLOBAL Coordinates for Drag...")
    
    # 1. FIND THE CAPTCHA FRAME
    frames = page.frames
    captcha_frame = None
    
    for frame in frames:
        try:
            if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                captcha_frame = frame
                break
        except: continue
    
    # Fallback
    if not captcha_frame and len(frames) > 1: captcha_frame = frames[-1]
    
    if not captcha_frame:
        print("❌ Captcha Frame Not Found")
        return False

    # 2. FIND BOUNDARIES INSIDE FRAME
    header = captcha_frame.get_by_text("Please complete verification", exact=False).first
    footer = captcha_frame.get_by_text("swap 2 tiles", exact=False).first
    
    if await header.count() == 0:
        print("❌ Header text missing")
        return False

    # Get Bounding Boxes inside the frame
    head_box = await header.bounding_box()
    foot_box = await footer.bounding_box()
    
    if not head_box or not foot_box:
        print("❌ Bounds missing")
        return False

    # 3. GET FRAME OFFSET (CRITICAL STEP)
    # We need to know where the FRAME is on the PAGE
    # Usually, we can't get frame element directly easily, so we use a trick:
    # We use page.mouse logic directly on known elements if frame has no offset issue.
    # However, Playwright handles frame coordinates automatically if we use frame.mouse
    # BUT we want to draw dots on the MAIN PAGE to be sure.
    
    # Let's rely on Playwright's auto-conversion for mouse, 
    # but for DOTS we need to be careful.
    
    # CALCULATE GRID (Inside Frame Logic)
    top_pad = 10
    bot_pad = 10
    
    grid_y = head_box['y'] + head_box['height'] + top_pad
    grid_height = foot_box['y'] - grid_y - bot_pad
    
    # Use Footer Width as reference
    grid_width = foot_box['width'] 
    grid_x = foot_box['x']
    
    # Safety Check
    if grid_height < 50: grid_height = 150

    print(f"📏 Grid (Frame Relative): X={int(grid_x)}, Y={int(grid_y)}, W={int(grid_width)}, H={int(grid_height)}")

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

    # --- 5. VISUAL DOTS (ON MAIN PAGE via Frame Evaluation) ---
    # We will try to draw dots inside the frame again, but with high Z-index and border
    try:
        await captcha_frame.evaluate(f"""
            var d1 = document.createElement('div');
            d1.style.position = 'absolute'; left='{sx}px'; top='{sy}px';
            d1.style.width='30px'; height='30px'; background='rgba(255,0,0,0.8)'; 
            d1.style.borderRadius='50%'; d1.style.border='3px solid yellow'; d1.style.zIndex='2147483647';
            d1.style.pointerEvents='none';
            document.body.appendChild(d1);
            
            var d2 = document.createElement('div');
            d2.style.position = 'absolute'; left='{tx}px'; top='{ty}px';
            d2.style.width='30px'; height='30px'; background='rgba(0,255,0,0.8)'; 
            d2.style.borderRadius='50%'; d2.style.border='3px solid yellow'; d2.style.zIndex='2147483647';
            d2.style.pointerEvents='none';
            document.body.appendChild(d2);
        """)
    except Exception as e:
        print(f"Dot Error: {e}")

    await asyncio.sleep(0.5)

    # --- 6. EXECUTE DRAG (USING PAGE MOUSE WITH FRAME OFFSET) ---
    # Important: page.mouse expects global coordinates. 
    # captcha_frame.mouse expects relative. Let's stick to captcha_frame.mouse
    # BUT Playwright 1.40+ sometimes has issues with frame.mouse.
    # Let's try controlling the PAGE mouse but by calculating global position if possible.
    # For now, sticking to frame.mouse which *should* work if element is found.
    
    print(f"🖱️ Moving to Source ({int(sx)}, {int(sy)})...")
    await captcha_frame.mouse.move(sx, sy, steps=10)
    await asyncio.sleep(0.5)
    
    print("✊ GRABBING...")
    await captcha_frame.mouse.down()
    await asyncio.sleep(0.5)
    
    # WIGGLE TO ACTIVATE
    await captcha_frame.mouse.move(sx + 10, sy, steps=5)
    await captcha_frame.mouse.move(sx - 10, sy, steps=5)
    await captcha_frame.mouse.move(sx, sy, steps=5)
    await asyncio.sleep(0.5) # Wait to ensure grab
    
    print("🚀 DRAGGING...")
    await captcha_frame.mouse.move(tx, ty, steps=50) # Slow steps
    
    # OVERSHOOT (Human Touch)
    await captcha_frame.mouse.move(tx + 5, ty + 5, steps=10)
    await asyncio.sleep(0.2)
    await captcha_frame.mouse.move(tx, ty, steps=10)
    
    await asyncio.sleep(1.0) # Hold at target
    
    print("✋ RELEASING...")
    await captcha_frame.mouse.up()
    
    return True