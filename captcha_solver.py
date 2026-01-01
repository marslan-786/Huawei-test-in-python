import asyncio
import math
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

async def load_ai_brain():
    global SLICE_CONFIG, AI_KNOWLEDGE_BASE, AI_LOADED
    if AI_LOADED: return 
    
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        
        # Load Config
        doc = await db[COL_SETTINGS].find_one({"_id": "slice_config"})
        if doc:
            SLICE_CONFIG = {k: doc.get(k,0) for k in ["top","bottom","left","right"]}
        else:
            SLICE_CONFIG = {"top":0, "bottom":0, "left":0, "right":0}

        # Build Knowledge Base
        AI_KNOWLEDGE_BASE = []
        async for doc in db[COL_CAPTCHAS].find({"status": "labeled"}):
            try:
                nparr = np.frombuffer(doc['image'], np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                tiles = slice_image_numpy(img, SLICE_CONFIG)
                if tiles:
                    src, trg = doc.get('label_source'), doc.get('label_target')
                    tiles[src], tiles[trg] = tiles[trg], tiles[src] # Fix
                    AI_KNOWLEDGE_BASE.append(tiles)
            except: pass
        
        AI_LOADED = True
        print(f"🧠 AI Brain Loaded: {len(AI_KNOWLEDGE_BASE)} Masters")
    except Exception as e:
        print(f"❌ AI Load Error: {e}")

def slice_image_numpy(img, cfg):
    h, w, _ = img.shape
    crop = img[cfg['top']:h-cfg['bottom'], cfg['left']:w-cfg['right']]
    if crop.size == 0: return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ch, cw = gray.shape
    th, tw = ch // 2, cw // 4
    return [gray[r*th:(r+1)*th, c*tw:(c+1)*tw] for r in range(2) for c in range(4)]

def get_swap_indices_logic(puzzle_img_path):
    if not AI_KNOWLEDGE_BASE: return 0, 7
    puzzle_img = cv2.imread(puzzle_img_path)
    if puzzle_img is None: return 0, 7
    
    puzzle_tiles = slice_image_numpy(puzzle_img, SLICE_CONFIG)
    if not puzzle_tiles: return 0, 7

    best_score = float('inf')
    best_master = None

    for master in AI_KNOWLEDGE_BASE:
        if master[0].shape != puzzle_tiles[0].shape: continue
        diff = sum(np.sum(cv2.absdiff(puzzle_tiles[i], master[i])) for i in range(8))
        if diff < best_score:
            best_score = diff
            best_master = master

    if not best_master: return 0, 7

    diffs = []
    for i in range(8):
        d = cv2.absdiff(puzzle_tiles[i], best_master[i])
        _, th = cv2.threshold(d, 30, 255, cv2.THRESH_BINARY)
        diffs.append((np.sum(th), i))
    
    diffs.sort(key=lambda x: x[0], reverse=True)
    return diffs[0][1], diffs[1][1]

# --- MAIN SOLVER ---
async def solve_captcha(page, session_id, logger=print):
    await load_ai_brain()
    logger("🧩 SOLVER: Analyzing...")

    # 1. Locate Frame
    frames = page.frames
    captcha_frame = None
    for frame in frames:
        try:
            if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                captcha_frame = frame; break
        except: continue
    
    if not captcha_frame: 
        logger("❌ Error: Captcha Frame Not Found"); return False

    # 2. Screenshot
    try:
        # Using the main image container selector
        # Adjust selector based on your calibration if needed
        # Commonly it's the image inside the puzzle container
        img_locator = captcha_frame.locator("img").first 
        # Fallback if specific ID known: captcha_frame.locator("#captcha-img")
        
        if await img_locator.count() == 0:
            logger("❌ Error: Image element missing"); return False
            
        box = await img_locator.bounding_box()
        if not box: return False
        
        img_path = f"./captures/{session_id}_puzzle.png"
        await page.screenshot(path=img_path, clip=box)
        
    except Exception as e:
        logger(f"❌ Screen Error: {e}"); return False

    # 3. AI Logic
    src_idx, trg_idx = get_swap_indices_logic(img_path)
    logger(f"🤖 AI Result: Swap Tile {src_idx} -> {trg_idx}")

    # 4. Coordinates
    grid_w, grid_h = box['width'], box['height']
    start_x, start_y = box['x'], box['y']
    tile_w, tile_h = grid_w / 4, grid_h / 2

    def get_center(idx):
        r, c = idx // 4, idx % 4
        cx = start_x + (c * tile_w) + (tile_w / 2)
        cy = start_y + (r * tile_h) + (tile_h / 2)
        return cx, cy

    sx, sy = get_center(src_idx)
    tx, ty = get_center(trg_idx)

    # 5. FAST DIRECT DRAG (Testing Mode)
    logger(f"🚀 Moving: ({int(sx)},{int(sy)}) to ({int(tx)},{int(ty)})")
    
    # Use CDP for low-level touch simulation
    client = await page.context.new_cdp_session(page)
    
    # Touch Start
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchStart", 
        "touchPoints": [{"x": sx, "y": sy}]
    })
    
    # Direct Move (No intermediate steps for speed testing)
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchMove", 
        "touchPoints": [{"x": tx, "y": ty}]
    })
    
    # Touch End
    await client.send("Input.dispatchTouchEvent", {
        "type": "touchEnd", 
        "touchPoints": []
    })
    
    logger("✅ Move Complete.")
    return True