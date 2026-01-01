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
    
    if AI_LOADED: return 
    
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        
        # 1. Load Settings
        doc = await db[COL_SETTINGS].find_one({"_id": "slice_config"})
        if doc:
            SLICE_CONFIG = {k: doc.get(k,0) for k in ["top","bottom","left","right"]}
            logger(f"⚙️ Loaded Config from DB: {SLICE_CONFIG}")
        else:
            SLICE_CONFIG = {"top":0, "bottom":0, "left":0, "right":0}
            logger("⚠️ No Config Found! Using defaults.")

        # 2. Build Knowledge Base
        logger("🏗️ Building Knowledge Base...")
        AI_KNOWLEDGE_BASE = []
        async for doc in db[COL_CAPTCHAS].find({"status": "labeled"}):
            try:
                nparr = np.frombuffer(doc['image'], np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                tiles = slice_image_numpy(img, SLICE_CONFIG)
                if tiles:
                    src, trg = doc.get('label_source'), doc.get('label_target')
                    tiles[src], tiles[trg] = tiles[trg], tiles[src] 
                    AI_KNOWLEDGE_BASE.append(tiles)
            except: pass
        
        AI_LOADED = True
        logger(f"🧠 AI Ready! Loaded {len(AI_KNOWLEDGE_BASE)} Masters.")
    except Exception as e:
        logger(f"❌ AI Load Error: {e}")

def slice_image_numpy(img, cfg):
    """Cuts the image using Global Config"""
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
        if master[0].shape != puzzle_tiles[0].shape: continue
        diff = sum(np.sum(cv2.absdiff(puzzle_tiles[i], master[i])) for i in range(8))
        if diff < best_score:
            best_score = diff
            best_master = master

    if not best_master: return None, None

    # 2. Find differences
    diffs = []
    for i in range(8):
        d = cv2.absdiff(puzzle_tiles[i], best_master[i])
        _, th = cv2.threshold(d, 30, 255, cv2.THRESH_BINARY)
        diffs.append((np.sum(th), i))
    
    diffs.sort(key=lambda x: x[0], reverse=True)
    return diffs[0][1], diffs[1][1]

# --- MAIN SOLVER ---
async def solve_captcha(page, session_id, logger=print):
    await load_ai_brain(logger)
    logger("🧩 SOLVER STARTED: Taking Full Screenshot...")

    # 1. Wait for render (Crucial)
    logger("⏳ Waiting 5s for clear image...")
    await asyncio.sleep(5)

    # 2. Take FULL PAGE Screenshot (Like Calibration)
    img_path = f"./captures/{session_id}_puzzle.png"
    try:
        await page.screenshot(path=img_path)
        logger(f"📸 Full Screenshot Saved: {img_path}")
    except Exception as e:
        logger(f"❌ Screen Error: {e}")
        return False

    # 3. AI Logic
    logger("🧠 AI Calculating...")
    src_idx, trg_idx = get_swap_indices_logic(img_path)
    
    if src_idx is None:
        logger("⚠️ AI Failed: Could not match background.")
        return False
        
    logger(f"🎯 AI RESULT: Swap Tile {src_idx} -> {trg_idx}")

    # 4. Calculate Coordinates from CONFIG
    # We use the raw image dimensions to determine where the grid is
    # Just like we did in the Slicer Tool
    
    # Read image to get current dimensions (should match calibration)
    img = cv2.imread(img_path)
    h, w, _ = img.shape
    
    # Calculate Grid Box from Config
    # Grid Starts at: x=left, y=top
    # Grid Width = TotalWidth - left - right
    # Grid Height = TotalHeight - top - bottom
    
    grid_x = SLICE_CONFIG['left']
    grid_y = SLICE_CONFIG['top']
    grid_w = w - SLICE_CONFIG['left'] - SLICE_CONFIG['right']
    grid_h = h - SLICE_CONFIG['top'] - SLICE_CONFIG['bottom']
    
    tile_w = grid_w / 4
    tile_h = grid_h / 2

    def get_center(idx):
        r, c = idx // 4, idx % 4
        # Calculate center relative to the full page
        cx = grid_x + (c * tile_w) + (tile_w / 2)
        cy = grid_y + (r * tile_h) + (tile_h / 2)
        return cx, cy

    sx, sy = get_center(src_idx)
    tx, ty = get_center(trg_idx)

    # 5. EXECUTE MOVE
    logger(f"🖱️ Moving from ({int(sx)},{int(sy)}) to ({int(tx)},{int(ty)})")
    
    # Visual Marker (For Video Proof)
    await page.evaluate(f"""
        var d = document.createElement('div');
        d.style.position='absolute'; d.style.left='{sx}px'; d.style.top='{sy}px';
        d.style.width='20px'; d.style.height='20px'; d.style.background='red'; 
        d.style.zIndex='999999'; d.style.border='2px solid white'; d.style.borderRadius='50%';
        document.body.appendChild(d);
    """)

    try:
        client = await page.context.new_cdp_session(page)
        
        # Touch Down
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchStart", "touchPoints": [{"x": sx, "y": sy}]
        })
        await asyncio.sleep(0.2)
        
        # Touch Move (Direct)
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchMove", "touchPoints": [{"x": tx, "y": ty}]
        })
        await asyncio.sleep(0.2)
        
        # Touch Up
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchEnd", "touchPoints": []
        })
        logger("✅ Action Completed.")
        
    except Exception as e:
        logger(f"❌ Move Failed: {e}")
        return False

    return True