import asyncio
import math

# Grid 4x2
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Searching for Captcha Element...")
    
    # 1. FIND THE RIGHT FRAME
    # Huawei ka captcha hamesha iframe me hota hai.
    frames = page.frames
    captcha_frame = None
    
    # Check all frames
    for frame in frames:
        try:
            # Frame k andar 'canvas' ya 'captcha' class dhoondo
            if await frame.locator("canvas").count() > 0 or \
               await frame.locator("[class*='captcha']").count() > 0:
                captcha_frame = frame
                print(f"✅ Found Captcha Frame: {frame.url}")
                break
        except: continue
    
    # Agar specific nahi mila, to last frame try karo (popup)
    if not captcha_frame and len(frames) > 1: 
        captcha_frame = frames[-1]
        print("⚠️ Using Last Frame as Fallback")

    if not captcha_frame:
        print("❌ No Captcha Frame Detected")
        return False

    # 2. FIND THE PUZZLE BOX (MULTI-STRATEGY)
    # Hum 3-4 alag alag selectors try karenge
    target_element = None
    
    selectors_to_try = [
        "canvas",                          # Priority 1: HTML5 Canvas
        ".uc-captcha-drag-area",           # Priority 2: Standard Drag Area
        ".uc-captcha-img",                 # Priority 3: Image Class
        "#captcha-container",              # Priority 4: ID
        "img[src*='captcha']"              # Priority 5: Image with src
    ]

    for selector in selectors_to_try:
        if await captcha_frame.locator(selector).count() > 0:
            target_element = captcha_frame.locator(selector).first
            # Check visibility
            if await target_element.is_visible():
                print(f"🎯 Locked on Element: {selector}")
                break
    
    # Agar koi specific element na mile, to BODY ko hi box maan lo
    if not target_element:
        print("⚠️ No specific element found, using Frame Body")
        target_element = captcha_frame.locator("body")

    # 3. GET COORDINATES
    try:
        box = await target_element.bounding_box()
    except:
        box = None

    if not box:
        print("❌ Failed to get Bounding Box")
        return False

    print(f"📏 Captcha Size: {box['width']}x{box['height']} at ({box['x']},{box['y']})")
    
    # Agar box height 0 hai (hidden element), to return kar jao
    if box['height'] < 50 or box['width'] < 100:
        print("❌ Box too small (Hidden?), Aborting Solver")
        return False

    # 4. CALCULATE TILE CENTERS (0 -> 7)
    tile_width = box['width'] / COLS
    tile_height = box['height'] / ROWS
    
    def get_tile_center(index):
        row = math.floor(index / COLS)
        col = index % COLS
        x = box['x'] + (col * tile_width) + (tile_width / 2)
        y = box['y'] + (row * tile_height) + (tile_height / 2)
        return x, y

    # Define Swap: 0 (Top-Left) <-> 7 (Bottom-Right)
    source_idx = 0
    target_idx = 7
    
    sx, sy = get_tile_center(source_idx)
    tx, ty = get_tile_center(target_idx)

    # --- 5. VISUAL MARKERS (RED/GREEN DOTS) ---
    print("📍 Injecting Visual Dots...")
    try:
        await page.evaluate(f"""
            var d1 = document.createElement('div');
            d1.style.position = 'absolute'; left='{sx}px'; top='{sy}px';
            d1.style.width='25px'; height='25px'; background='red'; 
            d1.style.borderRadius='50%'; d1.style.border='3px solid white'; d1.style.zIndex='999999';
            document.body.appendChild(d1);
            
            var d2 = document.createElement('div');
            d2.style.position = 'absolute'; left='{tx}px'; top='{ty}px';
            d2.style.width='25px'; height='25px'; background='lime'; 
            d2.style.borderRadius='50%'; d2.style.border='3px solid white'; d2.style.zIndex='999999';
            document.body.appendChild(d2);
        """)
    except Exception as e:
        print(f"⚠️ Could not draw dots: {e}")

    await asyncio.sleep(1) # Wait for dots to appear in video

    # --- 6. EXECUTE DRAG ---
    print(f"🖱️ Moving to Tile {source_idx}...")
    await page.mouse.move(sx, sy, steps=10)
    await asyncio.sleep(0.5)
    
    print("✊ HOLDING (Mouse Down)...")
    await page.mouse.down()
    await asyncio.sleep(1.5) # LONG HOLD needed for swap logic
    
    print(f"🖱️ Dragging to Tile {target_idx}...")
    await page.mouse.move(tx, ty, steps=30) # Slow drag
    await asyncio.sleep(1.0) # Wait at target
    
    print("✋ RELEASING...")
    await page.mouse.up()
    
    return True