import asyncio
import math

# Grid Configuration
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🤖 SOLVER: Simple Robotic Drag (No Physics)...")
    
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

    # 4. TILE CENTERS
    tile_width = grid_width / COLS
    tile_height = grid_height / ROWS
    
    def get_tile_center(index):
        row = math.floor(index / COLS)
        col = index % COLS
        x = grid_x + (col * tile_width) + (tile_width / 2)
        y = grid_y + (row * tile_height) + (tile_height / 2)
        return x, y

    sx, sy = get_tile_center(0)
    tx, ty = get_tile_center(7)

    # 5. VISUAL DOTS (For Debugging)
    try:
        await page.evaluate(f"""
            var d1 = document.createElement('div');
            d1.style.position = 'absolute'; left='{sx}px'; top='{sy}px';
            d1.style.width='20px'; height='20px'; background='red'; border='2px solid white'; zIndex='999999';
            document.body.appendChild(d1);
            
            var d2 = document.createElement('div');
            d2.style.position = 'absolute'; left='{tx}px'; top='{ty}px';
            d2.style.width='20px'; height='20px'; background='lime'; border='2px solid white'; zIndex='999999';
            document.body.appendChild(d2);
        """)
    except: pass
    
    await asyncio.sleep(0.5)

    # --- 6. SIMPLE ROBOTIC CDP TOUCH ---
    print(f"📱 CDP TOUCH: {int(sx)},{int(sy)} -> {int(tx)},{int(ty)}")
    
    # Create Raw CDP Session
    client = await page.context.new_cdp_session(page)
    
    # A. TOUCH START
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchStart",
        "touchPoints": [{"x": sx, "y": sy}]
    })
    print("👇 Touch Down")
    await asyncio.sleep(0.5) # Wait to grab
    
    # B. TOUCH MOVE (Linear Steps)
    steps = 20
    for i in range(steps + 1):
        t = i / steps
        # Linear Math (Straight Line)
        curr_x = sx + (tx - sx) * t
        curr_y = sy + (ty - sy) * t
        
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchMove",
            "touchPoints": [{"x": curr_x, "y": curr_y}]
        })
        await asyncio.sleep(0.05) # Fast Move
        
    print("🚀 Moved to Target")
    await asyncio.sleep(0.5) # Hold at target
    
    # C. TOUCH END
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchEnd",
        "touchPoints": []
    })
    print("👆 Touch Up")
    
    return True