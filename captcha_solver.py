import asyncio
import cv2
import numpy as np
import base64
from collections import Counter
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATION ---
MONGO_URI = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"
DB_NAME = "huawei_captcha"
COL_SETTINGS = "bot_settings"
COL_CAPTCHAS = "captchas"

# --- GLOBAL MEMORY (Logic Unchanged) ---
SLICE_CONFIG = None
AI_KNOWLEDGE_BASE = []
AI_LOADED = False
MASTER_SHAPE = None 

async def load_ai_brain(logger):
    global SLICE_CONFIG, AI_KNOWLEDGE_BASE, AI_LOADED, MASTER_SHAPE
    if AI_LOADED: return 
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        
        doc = await db[COL_SETTINGS].find_one({"_id": "slice_config"})
        if doc: SLICE_CONFIG = {k: doc.get(k,0) for k in ["top","bottom","left","right"]}
        else: SLICE_CONFIG = {"top":0, "bottom":0, "left":0, "right":0}

        logger("🏗️ Building Knowledge Base...")
        AI_KNOWLEDGE_BASE = []
        async for doc in db[COL_CAPTCHAS].find({"status": "labeled"}):
            try:
                nparr = np.frombuffer(doc['image'], np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if MASTER_SHAPE is None:
                    h, w, _ = img.shape
                    MASTER_SHAPE = (w, h)
                
                if (img.shape[1], img.shape[0]) != MASTER_SHAPE:
                    img = cv2.resize(img, MASTER_SHAPE)

                tiles = slice_image_numpy(img, SLICE_CONFIG)
                if tiles:
                    src, trg = doc.get('label_source'), doc.get('label_target')
                    tiles[src], tiles[trg] = tiles[trg], tiles[src] 
                    AI_KNOWLEDGE_BASE.append(tiles)
            except: pass
        
        AI_LOADED = True
        logger(f"🧠 AI Ready! {len(AI_KNOWLEDGE_BASE)} Masters. Std Size: {MASTER_SHAPE}")
    except Exception as e: logger(f"❌ AI Load Error: {e}")

def slice_image_numpy(img, cfg):
    h, w, _ = img.shape
    if cfg['top']+cfg['bottom'] >= h: return None
    crop = img[cfg['top']:h-cfg['bottom'], cfg['left']:w-cfg['right']]
    if crop.size == 0: return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ch, cw = gray.shape
    th, tw = ch // 2, cw // 4
    return [gray[r*th:(r+1)*th, c*tw:(c+1)*tw] for r in range(2) for c in range(4)]

def get_swap_indices_logic(puzzle_img_path, logger):
    if not AI_KNOWLEDGE_BASE or MASTER_SHAPE is None: return None, None
    full_img = cv2.imread(puzzle_img_path)
    if full_img is None: return None, None
    target_w, target_h = MASTER_SHAPE
    full_img_resized = cv2.resize(full_img, (target_w, target_h))
    puzzle_tiles = slice_image_numpy(full_img_resized, SLICE_CONFIG)
    if not puzzle_tiles: return None, None

    votes = []
    threshold_score = 6000000 
    
    for master in AI_KNOWLEDGE_BASE:
        if master[0].shape != puzzle_tiles[0].shape: 
             puzzle_tiles = [cv2.resize(t, (master[0].shape[1], master[0].shape[0])) for t in puzzle_tiles]

        diff_score = sum(np.sum(cv2.absdiff(puzzle_tiles[i], master[i])) for i in range(8))
        if diff_score < threshold_score: 
            tile_diffs = []
            for i in range(8):
                d = cv2.absdiff(puzzle_tiles[i], master[i])
                _, th = cv2.threshold(d, 50, 255, cv2.THRESH_BINARY)
                tile_diffs.append((np.sum(th), i))
            tile_diffs.sort(key=lambda x: x[0], reverse=True)
            votes.append(tuple(sorted((tile_diffs[0][1], tile_diffs[1][1]))))

    if not votes: return None, None
    return Counter(votes).most_common(1)[0][0]

# --- MAIN SOLVER ---
async def solve_captcha(page, session_id, logger=print):
    await load_ai_brain(logger)
    vp = page.viewport_size
    
    logger("⏳ Solver: Waiting 5s for image render...")
    await asyncio.sleep(5)

    img_path = f"./captures/{session_id}_puzzle.png"
    try: await page.screenshot(path=img_path)
    except Exception as e: logger(f"❌ Screen Error: {e}"); return False

    img_cv = cv2.imread(img_path)
    real_h, real_w, _ = img_cv.shape
    scale_x = real_w / vp['width']
    scale_y = real_h / vp['height']
    
    logger("🧠 AI Calculating...")
    src_idx, trg_idx = get_swap_indices_logic(img_path, logger)
    
    if src_idx is None: logger("⚠️ AI Failed."); return False
    logger(f"🎯 AI TARGET: Swap Tile {src_idx} -> {trg_idx}")

    # Coordinate Calculation
    grid_x = SLICE_CONFIG['left']
    grid_y = SLICE_CONFIG['top']
    grid_w = real_w - SLICE_CONFIG['left'] - SLICE_CONFIG['right']
    grid_h = real_h - SLICE_CONFIG['top'] - SLICE_CONFIG['bottom']
    tile_w, tile_h = grid_w / 4, grid_h / 2

    def get_center(idx):
        r, c = idx // 4, idx % 4
        raw_cx = grid_x + (c * tile_w) + (tile_w / 2)
        raw_cy = grid_y + (r * tile_h) + (tile_h / 2)
        final_x = raw_cx / scale_x
        final_y = raw_cy / scale_y
        return int(final_x), int(final_y)

    sx, sy = get_center(src_idx)
    tx, ty = get_center(trg_idx)

    # --- VISUAL DEBUG (Pass-through) ---
    # pointer-events: none ensures clicks go THROUGH the dot to the image
    await page.evaluate(f"""
        document.querySelectorAll('.debug-dot').forEach(e => e.remove());
        function createDot(x, y, color) {{
            var d = document.createElement('div'); d.className = 'debug-dot';
            d.style.position = 'fixed'; d.style.left = (x-10)+'px'; d.style.top = (y-10)+'px';
            d.style.width = '20px'; d.style.height = '20px'; d.style.background = color; 
            d.style.zIndex = '9999999'; d.style.borderRadius='50%'; d.style.border='3px solid white';
            d.style.pointerEvents = 'none'; // 🔥 CRITICAL: Allows clicking through
            document.body.appendChild(d);
        }}
        createDot({sx}, {sy}, 'lime'); createDot({tx}, {ty}, 'magenta');
    """)
    await asyncio.sleep(0.5)

    # --- 🦾 ROBOTIC FORCE DRAG (UPDATED) ---
    logger(f"🦾 ROBOT MOVE: {sx},{sy} -> {tx},{ty}")
    
    try:
        client = await page.context.new_cdp_session(page)
        
        # 1. FORCE DOWN (Touch & Press)
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchStart", 
            "touchPoints": [{
                "x": sx, "y": sy, 
                "force": 1.0, "pressure": 1.0, # Max Force
                "radiusX": 25, "radiusY": 25   # Fat Thumb
            }]
        })
        
        # 2. HOLD (Crucial for drag detection)
        logger("✊ Holding (0.6s)...")
        await asyncio.sleep(0.6) 

        # 3. WAKE UP MOVE (Jitter to trigger listener)
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchMove", 
            "touchPoints": [{
                "x": sx, "y": sy + 2, # Tiny move down
                "force": 1.0, "pressure": 1.0, "radiusX": 25, "radiusY": 25
            }]
        })
        await asyncio.sleep(0.1)

        # 4. ROBOT DRAG (Fast & Direct)
        # Reduced steps = Faster robot speed
        steps = 8 
        for i in range(1, steps + 1):
            t = i / steps
            cx = sx + (tx - sx) * t
            cy = sy + (ty - sy) * t
            
            await client.send("Input.dispatchTouchEvent", {
                "type": "touchMove", 
                "touchPoints": [{
                    "x": cx, "y": cy,
                    "force": 1.0, "pressure": 1.0, "radiusX": 25, "radiusY": 25
                }]
            })
            await asyncio.sleep(0.02) # Very fast updates

        # 5. DROP
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchEnd", "touchPoints": []
        })
        logger("✅ Robot Drag Done.")
        
    except Exception as e:
        logger(f"❌ Move Failed: {e}"); return False

    return True