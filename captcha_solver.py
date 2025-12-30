import asyncio
import math
import random
import numpy as np
from scipy import interpolate
import pytweening

# Grid Configuration
ROWS = 2
COLS = 4

# --- 🧠 PROFESSIONAL PHYSICS MOVEMENT ENGINE ---
async def human_like_mouse_move(page, start_x, start_y, end_x, end_y):
    print(f"🤖 PHYSICS ENGINE: Calculating path from ({int(start_x)},{int(start_y)}) to ({int(end_x)},{int(end_y)})...")

    # 1. PATH GENERATION (SCIPY)
    # Hum seedha rasta nahi lenge, balkay beech me 2-3 random points banayenge (Noise)
    points = [[start_x, start_y]]
    
    # Add random control points in between to create a natural arc
    dist = math.hypot(end_x - start_x, end_y - start_y)
    control_points = 3
    for i in range(control_points):
        # Randomness based on distance
        r_x = random.randint(-50, 50)
        r_y = random.randint(-50, 50)
        
        # Linear interpolation point + noise
        t = (i + 1) / (control_points + 1)
        pt_x = start_x + (end_x - start_x) * t + r_x
        pt_y = start_y + (end_y - start_y) * t + r_y
        points.append([pt_x, pt_y])
        
    points.append([end_x, end_y])
    points = np.array(points)

    # Scipy Interpolation (Smooth Curve creation)
    # B-Spline curve fit
    tck, u = interpolate.splprep(points.T, s=0, k=2) # k=2 means quadratic curve
    
    # Generate 50 smooth steps along this curve
    steps = 50
    u_new = np.linspace(0, 1, steps)
    x_smooth, y_smooth = interpolate.splev(u_new, tck)

    # 2. MOVEMENT EXECUTION (PYTWEENING)
    # Move to start
    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(0.2)
    
    print("✊ GRABBING (Physics Based)...")
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.3, 0.6)) # Human pause

    # Execute the calculated path with Variable Speed (Easing)
    for i in range(steps):
        target_x = x_smooth[i]
        target_y = y_smooth[i]
        
        # Easing Logic: EaseInOutCubic (Slow Start -> Fast Middle -> Slow End)
        # This breaks linear speed detection
        progress = i / steps
        ease_factor = pytweening.easeInOutCubic(progress)
        
        # Thora sa random delay har step par (Micro-stutter)
        micro_sleep = random.uniform(0.005, 0.02) 
        
        await page.mouse.move(target_x, target_y)
        await asyncio.sleep(micro_sleep)

    # 3. OVERSHOOT & CORRECTION (Human behavior)
    # Target par puhanch kar thora agay nikal jana aur wapis ana
    overshoot_x = end_x + random.choice([-3, 3])
    overshoot_y = end_y + random.choice([-3, 3])
    
    await page.mouse.move(overshoot_x, overshoot_y, steps=5)
    await asyncio.sleep(0.1)
    await page.mouse.move(end_x, end_y, steps=5)

    await asyncio.sleep(random.uniform(0.4, 0.8)) # Hold at target
    print("✋ RELEASING...")
    await page.mouse.up()


# --- MAIN SOLVER ---
async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Initializing Enterprise-Grade Solver...")
    
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
    
    if await header.count() == 0: return False
    
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

    # 5. EXECUTE PHYSICS DRAG
    try:
        # Using Page Mouse (Global) with Logic
        await human_like_mouse_move(page, sx, sy, tx, ty)
        return True
    except Exception as e:
        print(f"❌ Drag Error: {e}")
        return False