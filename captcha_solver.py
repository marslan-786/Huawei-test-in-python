import asyncio
import math
import os
from ai_solver import get_swap_indices

# Grid 4x2
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("\n============== SOLVER STARTED ==============")
    
    # 1. FIND FRAME (Text Sandwich)
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
        print("❌ FRAME ERROR: Not Found")
        return False

    # 2. BOUNDARIES
    header = captcha_frame.get_by_text("Please complete verification", exact=False).first
    footer = captcha_frame.get_by_text("swap 2 tiles", exact=False).first
    
    if await header.count() == 0: 
        print("❌ TEXT ERROR: Header not found")
        return False
        
    head_box = await header.bounding_box()
    foot_box = await footer.bounding_box()
    
    if not head_box or not foot_box: return False

    # 3. GRID CALC
    top_pad = 10; bot_pad = 10
    grid_y = head_box['y'] + head_box['height'] + top_pad
    grid_height = foot_box['y'] - grid_y - bot_pad
    grid_width = foot_box['width']
    grid_x = foot_box['x']
    
    if grid_height < 50: grid_height = 150
    
    print(f"📏 Grid Detected: W={int(grid_width)}, H={int(grid_height)}")

    # 4. CAPTURE IMAGE
    img_path = f"./captures/{session_id}_puzzle.png"
    # Take screenshot of the AREA only (Best effort)
    try:
        # We try to clip the screenshot to the calculated grid area
        # This requires global page coordinates
        await page.screenshot(path=img_path, clip={
            "x": grid_x,
            "y": grid_y,
            "width": grid_width,
            "height": grid_height
        })
        print(f"📸 Screenshot Saved: {img_path}")
    except Exception as e:
        print(f"❌ Screenshot Error: {e}")
        return False

    # 5. CALL AI (The Moment of Truth)
    print("🤖 Calling AI Brain...")
    source_idx, target_idx = get_swap_indices(img_path)
    
    print(f"🎯 ACTION: Moving Tile {source_idx} -> {target_idx}")

    # 6. CALCULATE CENTERS
    tile_width = grid_width / COLS
    tile_height = grid_height / ROWS
    
    def get_tile_center(index):
        row = math.floor(index / COLS)
        col = index % COLS
        x = grid_x + (col * tile_width) + (tile_width / 2)
        y = grid_y + (row * tile_height) + (tile_height / 2)
        return x, y

    sx, sy = get_tile_center(source_idx)
    tx, ty = get_tile_center(target_idx)

    # 7. VISUALIZE & MOVE
    # Draw Dots
    try:
        await page.evaluate(f"""
            var d1 = document.createElement('div');
            d1.style.position = 'absolute'; left='{sx}px'; top='{sy}px';
            d1.style.width='20px'; height='20px'; background='blue'; border='2px solid white'; zIndex='9999999';
            document.body.appendChild(d1);
            var d2 = document.createElement('div');
            d2.style.position = 'absolute'; left='{tx}px'; top='{ty}px';
            d2.style.width='20px'; height='20px'; background='lime'; border='2px solid white'; zIndex='9999999';
            document.body.appendChild(d2);
        """)
    except: pass
    
    await asyncio.sleep(0.5)

    # ROBOTIC DRAG (CDP)
    client = await page.context.new_cdp_session(page)
    
    print("👇 Touch Start")
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchStart",
        "touchPoints": [{"x": sx, "y": sy}]
    })
    await asyncio.sleep(0.5)
    
    print("🚀 Dragging...")
    steps = 20
    for i in range(steps + 1):
        t = i / steps
        cx = sx + (tx - sx) * t
        cy = sy + (ty - sy) * t
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchMove",
            "touchPoints": [{"x": cx, "y": cy}]
        })
        await asyncio.sleep(0.02)

    await asyncio.sleep(0.5) # Hold
    
    print("👆 Touch End")
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchEnd",
        "touchPoints": []
    })
    
    print("============== SOLVER FINISHED ==============\n")
    return True