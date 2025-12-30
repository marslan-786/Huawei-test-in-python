import asyncio
import math
import os
from ai_solver import get_swap_indices # Import our new Brain

# Grid Configuration
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Analyzing Captcha with OpenCV AI...")
    
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
    if not captcha_frame: return False

    # 2. BOUNDARIES
    header = captcha_frame.get_by_text("Please complete verification", exact=False).first
    footer = captcha_frame.get_by_text("swap 2 tiles", exact=False).first
    
    if await header.count() == 0 or await footer.count() == 0: return False
    
    head_box = await header.bounding_box()
    foot_box = await footer.bounding_box()
    if not head_box or not foot_box: return False

    # 3. GRID CALCULATION
    top_pad = 10; bot_pad = 10
    grid_y = head_box['y'] + head_box['height'] + top_pad
    grid_height = foot_box['y'] - grid_y - bot_pad
    grid_width = foot_box['width']
    grid_x = foot_box['x']
    
    if grid_height < 50: grid_height = 150
    
    # 4. CAPTURE IMAGE FOR AI
    # Hum sirf Captcha Area ka screenshot lenge
    captcha_image_path = f"./captures/{session_id}_puzzle.png"
    
    # Use global page clip to take accurate screenshot of just the grid area
    # Note: Using 'page' because 'captcha_frame' screenshot coordinates can be tricky
    try:
        # Calculate GLOBAL coordinates for screenshot clip
        # Since we used frame relative bounding boxes, we might need to be careful.
        # Safest way: Screenshot the whole frame's container
        container = captcha_frame.locator(".uc-captcha-drag-area").first
        if await container.count() > 0:
             await container.screenshot(path=captcha_image_path)
        else:
            # Fallback: Approximate clip based on text logic
            # Note: This is risky if frame offset exists. 
            # Better to find a container element.
            print("⚠️ Container not found, using generic selector...")
            await captcha_frame.locator("img").first.screenshot(path=captcha_image_path)
            
        print("📸 Puzzle Image Saved for AI Analysis")
    except Exception as e:
        print(f"❌ Screenshot Error: {e}")
        return False

    # 5. ASK AI FOR SOLUTION
    if os.path.exists(captcha_image_path):
        source_idx, target_idx = get_swap_indices(captcha_image_path)
    else:
        print("❌ Image file missing, using random fallback")
        source_idx, target_idx = 0, 7 # Fallback

    print(f"🤖 EXECUTING AI SWAP: {source_idx} -> {target_idx}")

    # 6. TILE CENTERS
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

    # 7. EXECUTE ROBOTIC DRAG (Proven to work)
    # CDP Touch Logic
    client = await page.context.new_cdp_session(page)
    
    print("👇 Touch Start")
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchStart",
        "touchPoints": [{"x": sx, "y": sy}]
    })
    await asyncio.sleep(0.5)
    
    # Linear Drag
    steps = 25
    for i in range(steps + 1):
        t = i / steps
        curr_x = sx + (tx - sx) * t
        curr_y = sy + (ty - sy) * t
        
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchMove",
            "touchPoints": [{"x": curr_x, "y": curr_y}]
        })
        await asyncio.sleep(0.04)
        
    await asyncio.sleep(0.5)
    
    print("👆 Touch End")
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchEnd",
        "touchPoints": []
    })
    
    return True