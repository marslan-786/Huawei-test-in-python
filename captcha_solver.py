import asyncio
import math
import os
from ai_solver import get_swap_indices

# Grid 4x2
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id, logger=print):
    logger("\n============== SOLVER STARTED ==============")
    
    # 1. FIND FRAME
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
        logger("❌ FRAME ERROR: Not Found")
        return False

    # 2. BOUNDARIES
    header = captcha_frame.get_by_text("Please complete verification", exact=False).first
    footer = captcha_frame.get_by_text("swap 2 tiles", exact=False).first
    
    if await header.count() == 0: 
        logger("❌ TEXT ERROR: Header not found")
        return False
        
    head_box = await header.bounding_box()
    foot_box = await footer.bounding_box()
    
    if not head_box or not foot_box: return False

    # 3. GRID CALC (FIXED WIDTH LOGIC)
    top_pad = 10; bot_pad = 10
    grid_y = head_box['y'] + head_box['height'] + top_pad
    grid_height = foot_box['y'] - grid_y - bot_pad
    
    # --- 🔥 FIX: DON'T USE TEXT WIDTH ---
    # Footer text is narrow. We need FULL grid width.
    # Center point is footer center.
    center_x = foot_box['x'] + (foot_box['width'] / 2)
    
    # Standard Mobile Grid Width is ~330px to 350px.
    grid_width = 340 
    
    # Calculate X based on Center
    grid_x = center_x - (grid_width / 2)
    
    if grid_height < 50: grid_height = 150
    
    logger(f"📏 Grid Calculated: W={int(grid_width)}, H={int(grid_height)} (Centered at {int(center_x)})")

    # 4. CAPTURE IMAGE
    img_path = f"./captures/{session_id}_puzzle.png"
    try:
        # Take screenshot with WIDER clip
        await page.screenshot(path=img_path, clip={
            "x": grid_x,
            "y": grid_y,
            "width": grid_width,
            "height": grid_height
        })
        logger(f"📸 Screenshot Saved: {img_path}")
    except Exception as e:
        logger(f"❌ Screenshot Error: {e}")
        return False

    # 5. CALL AI
    logger("🤖 Calling AI Brain...")
    # Pass logger to AI too
    source_idx, target_idx = get_swap_indices(img_path, logger=logger)
    
    logger(f"🎯 ACTION: Moving Tile {source_idx} -> {target_idx}")

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
    # (Robotic Drag Logic - Keep same)
    client = await page.context.new_cdp_session(page)
    
    logger("👇 Touch Start")
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchStart",
        "touchPoints": [{"x": sx, "y": sy}]
    })
    await asyncio.sleep(0.5)
    
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

    await asyncio.sleep(0.5)
    
    logger("👆 Touch End")
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchEnd",
        "touchPoints": []
    })
    
    logger("============== SOLVER FINISHED ==============")
    return True