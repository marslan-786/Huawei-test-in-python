import asyncio
import math
import cv2
import numpy as np
import base64
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATION (Same as main.py) ---
MONGO_URI = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"
DB_NAME = "huawei_captcha"
COL_SETTINGS = "bot_settings"
COL_CAPTCHAS = "captchas"

# --- GLOBAL MEMORY ---
SLICE_CONFIG = None
AI_KNOWLEDGE_BASE = []
AI_LOADED = False

async def load_ai_brain():
    """Loads Slice Config & Master Images from DB into RAM"""
    global SLICE_CONFIG, AI_KNOWLEDGE_BASE, AI_LOADED
    
    if AI_LOADED: return # Already loaded
    
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # 1. Load Settings
    doc = await db[COL_SETTINGS].find_one({"_id": "slice_config"})
    if doc:
        SLICE_CONFIG = {k: doc.get(k,0) for k in ["top","bottom","left","right"]}
        print(f"🧠 AI Loaded Config: {SLICE_CONFIG}")
    else:
        print("⚠️ AI Warning: No Slice Config found! Using Defaults.")
        SLICE_CONFIG = {"top":0, "bottom":0, "left":0, "right":0}

    # 2. Build Knowledge Base (Master Images)
    print("🧠 Building AI Knowledge Base...")
    count = 0
    async for doc in db[COL_CAPTCHAS].find({"status": "labeled"}):
        try:
            nparr = np.frombuffer(doc['image'], np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Slice & Swap Back to create Perfect Master
            tiles = slice_image_numpy(img, SLICE_CONFIG)
            if tiles:
                src, trg = doc.get('label_source'), doc.get('label_target')
                tiles[src], tiles[trg] = tiles[trg], tiles[src] # Restore
                AI_KNOWLEDGE_BASE.append(tiles)
                count += 1
        except: pass
    
    print(f"🧠 AI Brain Ready! Knowledge Base: {count} Masters")
    AI_LOADED = True

def slice_image_numpy(img, cfg):
    """Slices image into 8 grayscale tiles based on config"""
    h, w, _ = img.shape
    # Crop
    crop = img[cfg['top']:h-cfg['bottom'], cfg['left']:w-cfg['right']]
    if crop.size == 0: return None
    
    # Grayscale
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    
    # Slice 8
    ch, cw = gray.shape
    th, tw = ch // 2, cw // 4
    return [gray[r*th:(r+1)*th, c*tw:(c+1)*tw] for r in range(2) for c in range(4)]

def get_swap_indices_logic(puzzle_img_path):
    """Compares puzzle against knowledge base to find swaps"""
    if not AI_KNOWLEDGE_BASE: return 0, 7 # Fallback default
    
    # Load Puzzle
    puzzle_img = cv2.imread(puzzle_img_path)
    if puzzle_img is None: return 0, 7
    
    puzzle_tiles = slice_image_numpy(puzzle_img, SLICE_CONFIG)
    if not puzzle_tiles: return 0, 7

    # Find Best Background Match
    best_score = float('inf')
    best_master = None

    for master in AI_KNOWLEDGE_BASE:
        diff = 0
        if master[0].shape != puzzle_tiles[0].shape: continue
        for i in range(8):
            diff += np.sum(cv2.absdiff(puzzle_tiles[i], master[i]))
        
        if diff < best_score:
            best_score = diff
            best_master = master

    if not best_master: return 0, 7 # Should not happen if training is good

    # Identify Swaps
    diffs = []
    for i in range(8):
        d = cv2.absdiff(puzzle_tiles[i], best_master[i])
        _, th = cv2.threshold(d, 30, 255, cv2.THRESH_BINARY)
        diffs.append((np.sum(th), i))
    
    diffs.sort(key=lambda x: x[0], reverse=True)
    return diffs[0][1], diffs[1][1] # Top 2 differences are the answer

# --- MAIN SOLVER FUNCTION CALLED BY BOT ---
async def solve_captcha(page, session_id, logger=print):
    # Ensure AI is loaded
    await load_ai_brain()
    
    logger("\n============== SOLVER STARTED ==============")
    
    # 1. FIND CAPTCHA FRAME
    frames = page.frames
    captcha_frame = None
    for frame in frames:
        try:
            if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                captcha_frame = frame; break
        except: continue
    
    if not captcha_frame: 
        logger("❌ FRAME ERROR: Not Found"); return False

    # 2. LOCATE IMAGE & TAKE SCREENSHOT
    # We use the FULL image container logic you perfected
    # Adjust this selector if needed based on your calibration training
    # Usually it is the image inside the captcha container
    try:
        # Wait for image to load
        img_locator = captcha_frame.locator("img").first 
        # Or specifically: captcha_frame.locator(".uc-captcha-img")
        
        if await img_locator.count() == 0:
            logger("❌ Image Element Not Found"); return False
            
        box = await img_locator.bounding_box()
        if not box: return False
        
        # Save Puzzle Image
        img_path = f"./captures/{session_id}_puzzle.png"
        await page.screenshot(path=img_path, clip=box)
        logger(f"📸 Captcha Image Saved: {img_path}")
        
    except Exception as e:
        logger(f"❌ Screen Error: {e}"); return False

    # 3. ASK AI BRAIN
    logger("🧠 Consulting AI Knowledge Base...")
    src_idx, trg_idx = get_swap_indices_logic(img_path)
    logger(f"🎯 AI DECISION: Swap Tile {src_idx} <-> {trg_idx}")

    # 4. CALCULATE DRAG COORDINATES
    # We use the bounding box of the image we just screenshotted
    # box['x'], box['y'], box['width'], box['height'] are already relative to page
    # IMPORTANT: Need to account for frame offset if inside iframe!
    # Playwright's bounding_box() is usually relative to the main page if called on an element handle properly.
    
    # Calculate grid dimensions based on image size
    grid_w = box['width']
    grid_h = box['height']
    start_x = box['x']
    start_y = box['y']
    
    tile_w = grid_w / 4
    tile_h = grid_h / 2

    def get_center(idx):
        r = idx // 4
        c = idx % 4
        cx = start_x + (c * tile_w) + (tile_w / 2)
        cy = start_y + (r * tile_h) + (tile_h / 2)
        return cx, cy

    sx, sy = get_center(src_idx)
    tx, ty = get_center(trg_idx)

    # 5. EXECUTE DRAG (HUMAN-LIKE)
    logger(f"🖱️ Dragging...")
    
    # Visual Feedback (Red Dot)
    await page.evaluate(f"""
        var d = document.createElement('div');
        d.style.position='absolute'; d.style.left='{sx}px'; d.style.top='{sy}px';
        d.style.width='20px'; d.style.height='20px'; d.style.background='red'; d.style.zIndex='9999';
        document.body.appendChild(d);
    """)

    # Touch/Mouse Actions
    # Using CDP Session for precise touch control (like your previous script)
    client = await page.context.new_cdp_session(page)
    
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchStart", "touchPoints": [{"x": sx, "y": sy}]
    })
    await asyncio.sleep(0.3)
    
    steps = 15
    for i in range(steps + 1):
        t = i / steps
        cx = sx + (tx - sx) * t
        cy = sy + (ty - sy) * t
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchMove", "touchPoints": [{"x": cx, "y": cy}]
        })
        await asyncio.sleep(0.01)

    await asyncio.sleep(0.3)
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchEnd", "touchPoints": []
    })
    
    logger("✅ Swap Executed.")
    return True