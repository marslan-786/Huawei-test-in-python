import asyncio
import math
import random

# Grid Configuration (4x2)
ROWS = 2
COLS = 4

# --- 🧠 BEZIER CURVE MATH (HUMAN MOVEMENT) ---
def get_bezier_point(t, p0, p1, p2, p3):
    """Calculates position at time t (0 to 1) on a cubic bezier curve"""
    cX = 3 * (p1['x'] - p0['x'])
    bX = 3 * (p2['x'] - p1['x']) - cX
    aX = p3['x'] - p0['x'] - cX - bX

    cY = 3 * (p1['y'] - p0['y'])
    bY = 3 * (p2['y'] - p1['y']) - cY
    aY = p3['y'] - p0['y'] - cY - bY

    x = (aX * t**3) + (bX * t**2) + (cX * t) + p0['x']
    y = (aY * t**3) + (bY * t**2) + (cY * t) + p0['y']
    return {'x': x, 'y': y}

async def human_drag(page, start_x, start_y, end_x, end_y):
    """Moves mouse from A to B using a random Bezier curve path"""
    print(f"🎨 Generating Human Path: ({int(start_x)},{int(start_y)}) -> ({int(end_x)},{int(end_y)})")
    
    # 1. Create Control Points for the Curve (Randomness)
    # P0 = Start, P3 = End
    # P1 & P2 are random points in between to create a curve
    p0 = {'x': start_x, 'y': start_y}
    p3 = {'x': end_x, 'y': end_y}
    
    # Random deviation
    offset = random.randint(50, 150)
    p1 = {'x': start_x + random.randint(-offset, offset), 'y': start_y + random.randint(-offset, offset)}
    p2 = {'x': end_x + random.randint(-offset, offset), 'y': end_y + random.randint(-offset, offset)}

    # 2. Move Mouse along the curve
    steps = 25 # Total steps for drag
    
    await page.mouse.move(start_x, start_y)
    await page.mouse.down()
    print("✊ Grabbing...")
    await asyncio.sleep(0.2)

    for i in range(steps + 1):
        t = i / steps
        point = get_bezier_point(t, p0, p1, p2, p3)
        await page.mouse.move(point['x'], point['y'])
        # Variable speed (slow start, fast middle, slow end)
        sleep_time = random.uniform(0.01, 0.03)
        await asyncio.sleep(sleep_time)

    # 3. Overshoot (Go slightly past target and come back)
    await page.mouse.move(end_x + 5, end_y + 5, steps=5)
    await asyncio.sleep(0.1)
    await page.mouse.move(end_x, end_y, steps=5)
    
    print("✋ Releasing...")
    await page.mouse.up()


# --- MAIN SOLVER ---
async def solve_captcha(page, session_id):
    print("🧠 SOLVER: Using Bezier Curve Logic...")
    
    # 1. FIND FRAME (Using your text sandwich logic)
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

    # 5. EXECUTE HUMAN DRAG (USING PAGE MOUSE)
    # We use 'page.mouse' because frames can be tricky with coordinates.
    # But first we need to ensure we are clicking in the right place relative to viewport.
    # Usually playwright handles frame offset automatically if we use frame.mouse.
    
    # Let's try `captcha_frame.mouse` FIRST with the new algorithm
    try:
        await human_drag(captcha_frame, sx, sy, tx, ty)
        return True
    except Exception as e:
        print(f"⚠️ Frame drag failed ({e}), trying Page drag...")
        # If frame mouse fails, try global page mouse (might need offset calculation)
        await human_drag(page, sx, sy, tx, ty)
        return True