import asyncio
import math

# Grid Configuration (Huawei usually 4 cols x 2 rows)
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Initializing Visual Drag (0 -> 7)...")
    
    # 1. FIND CAPTCHA FRAME
    # Sometimes it's in a frame, sometimes in the main page
    frames = page.frames
    captcha_frame = None
    
    # Check all frames for the drag area
    for frame in frames:
        try:
            if await frame.locator(".uc-captcha-drag-area").count() > 0:
                captcha_frame = frame
                break
        except: continue
    
    # Fallback to main page if no frame detected
    if not captcha_frame:
        print("⚠️ Frame not found, trying main page...")
        captcha_frame = page

    # 2. LOCATE CONTAINER BOX
    container = captcha_frame.locator(".uc-captcha-drag-area").first
    if await container.count() == 0:
        container = captcha_frame.locator("#captcha-container").first
        
    box = await container.bounding_box()
    if not box:
        print("❌ Captcha Box Coordinates Not Found!")
        return False

    print(f"📏 Captcha Dimensions: {box['width']}x{box['height']}")
    
    # 3. CALCULATE TILE CENTERS
    tile_width = box['width'] / COLS
    tile_height = box['height'] / ROWS
    
    def get_tile_center(index):
        row = math.floor(index / COLS)
        col = index % COLS
        # Center Calculation
        x = box['x'] + (col * tile_width) + (tile_width / 2)
        y = box['y'] + (row * tile_height) + (tile_height / 2)
        return x, y

    # Define Source (0) and Target (7)
    source_idx = 0 
    target_idx = 7
    
    sx, sy = get_tile_center(source_idx)
    tx, ty = get_tile_center(target_idx)

    # --- 4. VISUAL DEBUGGING (RED DOT ON CLICK) ---
    print(f"📍 Marking Click Points...")
    
    # Inject Red Dot at Source (Start)
    await page.evaluate(f"""
        var d1 = document.createElement('div');
        d1.style.position = 'absolute'; 
        d1.style.left = '{sx}px'; 
        d1.style.top = '{sy}px';
        d1.style.width = '25px'; 
        d1.style.height = '25px'; 
        d1.style.backgroundColor = 'red'; 
        d1.style.border = '3px solid white';
        d1.style.borderRadius = '50%'; 
        d1.style.zIndex = '999999';
        d1.id = 'debug-source-dot';
        document.body.appendChild(d1);
    """)

    # Inject Green Dot at Target (End)
    await page.evaluate(f"""
        var d2 = document.createElement('div');
        d2.style.position = 'absolute'; 
        d2.style.left = '{tx}px'; 
        d2.style.top = '{ty}px';
        d2.style.width = '25px'; 
        d2.style.height = '25px'; 
        d2.style.backgroundColor = '#00ff00'; 
        d2.style.border = '3px solid white';
        d2.style.borderRadius = '50%'; 
        d2.style.zIndex = '999999';
        d2.id = 'debug-target-dot';
        document.body.appendChild(d2);
    """)
    
    await asyncio.sleep(0.5) # Let dots render

    # --- 5. EXECUTE DRAG ACTION ---
    print(f"🖱️ Moving Mouse to Source ({sx}, {sy})...")
    await page.mouse.move(sx, sy, steps=5)
    await asyncio.sleep(0.5)
    
    print("✊ MOUSE DOWN (Holding)...")
    await page.mouse.down()
    await asyncio.sleep(1) # Hold for 1 second
    
    print(f"🖱️ Dragging to Target ({tx}, {ty})...")
    # Steps=30 means slow drag
    await page.mouse.move(tx, ty, steps=30) 
    await asyncio.sleep(1) # Wait at target
    
    print("✋ MOUSE UP (Releasing)...")
    await page.mouse.up()
    
    # Remove dots (Optional - I kept them so you can see in screenshot)
    # await page.evaluate("document.getElementById('debug-source-dot').remove()")
    
    return True