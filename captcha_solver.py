import asyncio
import random
import time
import math

# Grid Configuration for Huawei Swap Captcha (Usually 4x2)
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Analyzing Tile Swap Captcha...")
    
    # 1. FIND CAPTCHA CONTAINER
    # Huawei swap captcha container class is usually different
    frames = page.frames
    captcha_frame = None
    
    for frame in frames:
        try:
            # Check for the specific swap container or image
            if await frame.locator(".uc-captcha-drag-area").count() > 0 or \
               await frame.locator("img").count() > 3: # Swap captcha has multiple tile imgs
                captcha_frame = frame
                break
        except: continue
        
    # If standard logic fails, use the last frame (usually the popup)
    if not captcha_frame and len(frames) > 1:
        captcha_frame = frames[-1]

    if not captcha_frame:
        print("❌ Captcha Frame not found")
        return False

    print(f"✅ Captcha Frame Detected: {captcha_frame.url}")
    
    # 2. LOCATE THE MAIN CAPTCHA BOX
    # We need the bounding box of the whole image area to divide it
    # Usually class: .uc-captcha-bg-img or similar container
    container = captcha_frame.locator(".uc-captcha-drag-area").first
    if await container.count() == 0:
        # Fallback to a generic container if class changes
        container = captcha_frame.locator("div").first 
        
    box = await container.bounding_box()
    if not box:
        print("❌ Could not get Captcha Box coordinates")
        return False

    print(f"📏 Captcha Size: {box['width']}x{box['height']}")
    
    # 3. CALCULATE GRID COORDINATES (The Matrix 4x2)
    # Huawei Swap is typically 4 columns, 2 rows
    tile_width = box['width'] / COLS
    tile_height = box['height'] / ROWS
    
    print(f"🔲 Calculating Grid: Each tile is {tile_width}x{tile_height}")

    # Function to get center X,Y of a specific tile index (0-7)
    def get_tile_center(index):
        row = math.floor(index / COLS)
        col = index % COLS
        
        x = box['x'] + (col * tile_width) + (tile_width / 2)
        y = box['y'] + (row * tile_height) + (tile_height / 2)
        return x, y

    # --- 📸 DEBUG: DRAW GRID ON SCREENSHOT ---
    # Hum har tile k center par ek DOT lagayenge taake screenshot me confirm ho
    for i in range(ROWS * COLS):
        tx, ty = get_tile_center(i)
        await page.evaluate(f"""
            var dot = document.createElement('div');
            dot.style.position = 'absolute';
            dot.style.left = '{tx}px';
            dot.style.top = '{ty}px';
            dot.style.width = '15px';
            dot.style.height = '15px';
            dot.style.backgroundColor = 'yellow';
            dot.style.color = 'black';
            dot.style.fontSize = '10px';
            dot.style.fontWeight = 'bold';
            dot.innerText = '{i}';
            dot.style.borderRadius = '50%';
            dot.style.zIndex = '999999';
            dot.style.textAlign = 'center';
            document.body.appendChild(dot);
        """)
    
    # Take Screenshot with Grid Numbers
    await asyncio.sleep(1)
    await page.screenshot(path=f"./captures/{session_id}_GRID_ANALYSIS.jpg")
    print(f"📸 Grid Analysis Saved: {session_id}_GRID_ANALYSIS.jpg")

    # --- 4. THE AI LOGIC (PLACEHOLDER) ---
    # Yahan AI (YesCaptcha/2Captcha) humein bataye gi k kin 2 tiles ko swap karna hai.
    # Filhal hum TEST k liye 'Tile 0' (First) aur 'Tile 7' (Last) ko swap karte hain.
    # (Ya jo bhi do tiles alag rang ki hon, unhein AI detect karegi)
    
    source_tile_index = 0  # Example: Top-Left
    target_tile_index = 4  # Example: Bottom-Left (Just testing logic)
    
    # --- 5. PERFORM SWAP ACTION ---
    print(f"🔄 Swapping Tile {source_tile_index} with Tile {target_tile_index}...")
    
    sx, sy = get_tile_center(source_tile_index)
    tx, ty = get_tile_center(target_tile_index)
    
    # MOVE TO SOURCE
    await page.mouse.move(sx, sy, steps=5)
    await asyncio.sleep(0.3)
    
    # MOUSE DOWN (GRAB)
    await page.mouse.down()
    await asyncio.sleep(0.5)
    
    # DRAG TO TARGET
    await page.mouse.move(tx, ty, steps=15) # Smooth drag
    await asyncio.sleep(0.5)
    
    # MOUSE UP (DROP)
    await page.mouse.up()
    
    print("✅ Swap Action Complete!")
    await asyncio.sleep(3)
    
    return True