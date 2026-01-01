import asyncio
import cv2
import numpy as np
import base64
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATION ---
MONGO_URI = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"
DB_NAME = "huawei_captcha"
COL_SETTINGS = "bot_settings"
COL_CAPTCHAS = "captchas"

# --- GLOBAL MEMORY ---
SLICE_CONFIG = None
AI_KNOWLEDGE_BASE = []
AI_LOADED = False

async def load_ai_brain(logger):
    """Loads Slice Config & Master Images from DB into RAM"""
    global SLICE_CONFIG, AI_KNOWLEDGE_BASE, AI_LOADED
    
    if AI_LOADED: 
        logger("🧠 AI Brain already loaded in RAM.")
        return 
    
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        
        # 1. Load Settings
        doc = await db[COL_SETTINGS].find_one({"_id": "slice_config"})
        if doc:
            SLICE_CONFIG = {k: doc.get(k,0) for k in ["top","bottom","left","right"]}
            logger(f"⚙️ Loaded Config: {SLICE_CONFIG}")
        else:
            SLICE_CONFIG = {"top":0, "bottom":0, "left":0, "right":0}
            logger("⚠️ No Config Found! Using defaults.")

        # 2. Build Knowledge Base
        logger("🏗️ Building Knowledge Base from DB...")
        AI_KNOWLEDGE_BASE = []
        count = 0
        async for doc in db[COL_CAPTCHAS].find({"status": "labeled"}):
            try:
                # Convert Binary to Numpy Image
                nparr = np.frombuffer(doc['image'], np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Slice it to create a "Master Key"
                tiles = slice_image_numpy(img, SLICE_CONFIG)
                if tiles:
                    # Swap tiles back to original positions to make it a perfect background
                    src, trg = doc.get('label_source'), doc.get('label_target')
                    tiles[src], tiles[trg] = tiles[trg], tiles[src] 
                    AI_KNOWLEDGE_BASE.append(tiles)
                    count += 1
            except: pass
        
        AI_LOADED = True
        logger(f"🧠 AI Ready! Loaded {count} Master Patterns.")
    except Exception as e:
        logger(f"❌ AI Load Error: {e}")

def slice_image_numpy(img, cfg):
    """Cuts the image into 8 pieces"""
    h, w, _ = img.shape
    # Crop based on calibration
    crop = img[cfg['top']:h-cfg['bottom'], cfg['left']:w-cfg['right']]
    if crop.size == 0: return None
    
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ch, cw = gray.shape
    th, tw = ch // 2, cw // 4
    
    tiles = []
    for r in range(2):
        for c in range(4):
            # Extract tile
            tile = gray[r*th:(r+1)*th, c*tw:(c+1)*tw]
            tiles.append(tile)
    return tiles

def get_swap_indices_logic(puzzle_img_path):
    """The Brain: Compares puzzle with masters"""
    if not AI_KNOWLEDGE_BASE: return None, None
    
    puzzle_img = cv2.imread(puzzle_img_path)
    if puzzle_img is None: return None, None
    
    # Slice the fresh puzzle
    puzzle_tiles = slice_image_numpy(puzzle_img, SLICE_CONFIG)
    if not puzzle_tiles: return None, None

    # 1. Match Background
    best_score = float('inf')
    best_master = None

    for master in AI_KNOWLEDGE_BASE:
        # Check size compatibility
        if master[0].shape != puzzle_tiles[0].shape: continue
        
        # Calculate total difference
        diff = sum(np.sum(cv2.absdiff(puzzle_tiles[i], master[i])) for i in range(8))
        if diff < best_score:
            best_score = diff
            best_master = master

    if not best_master: return None, None

    # 2. Find differences (The Swap)
    diffs = []
    for i in range(8):
        d = cv2.absdiff(puzzle_tiles[i], best_master[i])
        # Use threshold to ignore noise (color jitter)
        _, th = cv2.threshold(d, 30, 255, cv2.THRESH_BINARY)
        score = np.sum(th)
        diffs.append((score, i))
    
    # Sort by difference (Highest diff = Moved tile)
    diffs.sort(key=lambda x: x[0], reverse=True)
    return diffs[0][1], diffs[1][1]

# --- MAIN EXPORTED FUNCTION ---
async def solve_captcha(page, session_id, logger=print):
    # 1. Load Brain
    await load_ai_brain(logger)
    
    logger("🕵️ SOLVER: Looking for Captcha Element...")

    # 2. Find the Frame & Element
    # Note: We look for the image inside the captcha container
    frames = page.frames
    captcha_frame = None
    for frame in frames:
        try:
            if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                captcha_frame = frame; break
        except: continue
    
    if not captcha_frame:
        logger("❌ Solver Error: Frame not found")
        return False

    # 3. CRITICAL WAIT (Image Loading)
    logger("⏳ Solver: Waiting 5s for image render...")
    await asyncio.sleep(5) 

    # 4. Take Screenshot
    try:
        # This selector targets the main image. 
        # Make sure this matches what you calibrated!
        # If it fails, try: captcha_frame.locator("canvas").first
        img_element = captcha_frame.locator("img").first 
        
        if await img_element.count() == 0:
            logger("❌ Solver Error: Image tag not found")
            return False
            
        box = await img_element.bounding_box()
        if not box:
            logger("❌ Solver Error: Bounding box is null")
            return False
            
        img_path = f"./captures/{session_id}_puzzle.png"
        await page.screenshot(path=img_path, clip=box)
        logger(f"📸 Snapshot taken: {img_path}")
        
    except Exception as e:
        logger(f"❌ Screenshot Failed: {e}")
        return False

    # 5. AI Thinking
    logger("🧠 AI is thinking...")
    src, trg = get_swap_indices_logic(img_path)
    
    if src is None:
        logger("⚠️ AI could not find a match in DB.")
        return False
        
    logger(f"🎯 RESULT: Swap Tile {src} with Tile {trg}")

    # 6. Calculate Geometry
    grid_w, grid_h = box['width'], box['height']
    start_x, start_y = box['x'], box['y']
    tile_w, tile_h = grid_w / 4, grid_h / 2

    def get_center(idx):
        r, c = idx // 4, idx % 4
        cx = start_x + (c * tile_w) + (tile_w / 2)
        cy = start_y + (r * tile_h) + (tile_h / 2)
        return cx, cy

    sx, sy = get_center(src)
    tx, ty = get_center(trg)

    # 7. Execute Move
    logger(f"🖱️ Action: Moving {src} to {trg}...")
    
    # Visual Marker (Red Dot)
    await page.evaluate(f"""
        var d = document.createElement('div');
        d.style.position='absolute'; d.style.left='{sx}px'; d.style.top='{sy}px';
        d.style.width='20px'; d.style.height='20px'; d.style.background='red'; d.style.zIndex='99999'; d.style.border='2px solid white';
        document.body.appendChild(d);
    """)

    # Touch Simulation
    try:
        client = await page.context.new_cdp_session(page)
        
        # Down
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchStart", "touchPoints": [{"x": sx, "y": sy}]
        })
        await asyncio.sleep(0.2)
        
        # Move
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchMove", "touchPoints": [{"x": tx, "y": ty}]
        })
        await asyncio.sleep(0.2)
        
        # Up
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchEnd", "touchPoints": []
        })
        logger("✅ Touch Event Sent.")
        
    except Exception as e:
        logger(f"❌ Touch Failed: {e}")
        return False

    return True