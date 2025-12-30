import asyncio
import math

# Grid Configuration (4x2)
ROWS = 2
COLS = 4

async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Using 'Text Sandwich' Logic...")
    
    # 1. FIND THE CAPTCHA FRAME
    # Huawei captcha is inside an iframe. Let's find it.
    frames = page.frames
    captcha_frame = None
    
    # Check all frames for the text "swap 2 tiles"
    for frame in frames:
        try:
            if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                captcha_frame = frame
                print(f"✅ Found Frame with Text: {frame.url}")
                break
        except: continue
    
    # Fallback
    if not captcha_frame and len(frames) > 1: 
        captcha_frame = frames[-1]

    if not captcha_frame:
        print("❌ Captcha Frame Not Detected")
        return False

    # 2. DEFINE BOUNDARIES (The Sandwich)
    # Roof: "Please complete verification"
    # Floor: "swap 2 tiles..."
    
    header = captcha_frame.get_by_text("Please complete verification", exact=False).first
    footer = captcha_frame.get_by_text("swap 2 tiles", exact=False).first
    
    if await header.count() == 0 or await footer.count() == 0:
        print("❌ Could not find Header/Footer Text markers")
        # Retry with a generic center guess if text fails
        return False

    # Get Coordinates of Text
    head_box = await header.bounding_box()
    foot_box = await footer.bounding_box()
    
    if not head_box or not foot_box:
        print("❌ Failed to measure text boundaries")
        return False

    # 3. CALCULATE GRID AREA
    # The Grid is BETWEEN the Header and Footer
    # Padding estimates (thoda sa gap hota hai text aur image k beech)
    top_padding = 10 
    bottom_padding = 10
    
    grid_y = head_box['y'] + head_box['height'] + top_padding
    grid_height = foot_box['y'] - grid_y - bottom_padding
    
    # Width is usually aligned with the footer text width or slightly wider
    # Let's assume width is approx 300px (standard mobile captcha) or use footer width
    grid_width = 300 # Hardcoded safe estimate for mobile view
    grid_x = foot_box['x'] + (foot_box['width'] / 2) - (grid_width / 2) # Center it based on footer
    
    # Safety Check: If calculated height is weird, force standard size
    if grid_height < 50: 
        print("⚠️ Calculated height too small, using default")
        grid_height = 150 # Standard height
        grid_y = foot_box['y'] - 160

    print(f"📏 Calculated Grid: X={grid_x}, Y={grid_y}, W={grid_width}, H={grid_height}")

    # 4. CALCULATE TILE CENTERS (0 -> 7)
    tile_width = grid_width / COLS
    tile_height = grid_height / ROWS
    
    def get_tile_center(index):
        row = math.floor(index / COLS)
        col = index % COLS
        x = grid_x + (col * tile_width) + (tile_width / 2)
        y = grid_y + (row * tile_height) + (tile_height / 2)
        return x, y

    # Define Swap: 0 (Top-Left) <-> 7 (Bottom-Right)
    source_idx = 0
    target_idx = 7
    
    sx, sy = get_tile_center(source_idx)
    tx, ty = get_tile_center(target_idx)

    # --- 5. VISUAL MARKERS (RED/GREEN DOTS) ---
    print("📍 Drawing Dots on Calculated Coordinates...")
    try:
        # Drawing inside the frame context
        await captcha_frame.evaluate(f"""
            var d1 = document.createElement('div');
            d1.style.position = 'absolute'; left='{sx}px'; top='{sy}px';
            d1.style.width='20px'; height='20px'; background='red'; 
            d1.style.borderRadius='50%'; d1.style.border='3px solid white'; d1.style.zIndex='999999';
            document.body.appendChild(d1);
            
            var d2 = document.createElement('div');
            d2.style.position = 'absolute'; left='{tx}px'; top='{ty}px';
            d2.style.width='20px'; height='20px'; background='lime'; 
            d2.style.borderRadius='50%'; d2.style.border='3px solid white'; d2.style.zIndex='999999';
            document.body.appendChild(d2);
        """)
    except Exception as e:
        print(f"⚠️ Dot Error: {e}")

    await asyncio.sleep(1) # Wait for dots to appear in video

    # --- 6. EXECUTE DRAG ---
    print(f"🖱️ Moving to Source ({sx:.1f}, {sy:.1f})...")
    await captcha_frame.mouse.move(sx, sy, steps=10)
    await asyncio.sleep(0.5)
    
    print("✊ HOLDING...")
    await captcha_frame.mouse.down()
    await asyncio.sleep(1.0)
    
    print(f"🖱️ Dragging to Target ({tx:.1f}, {ty:.1f})...")
    await captcha_frame.mouse.move(tx, ty, steps=30) # Slow drag
    await asyncio.sleep(1.0)
    
    print("✋ RELEASING...")
    await captcha_frame.mouse.up()
    
    return True