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

# --- GLOBAL MEMORY ---
SLICE_CONFIG = None
AI_KNOWLEDGE_BASE = []
AI_LOADED = False

async def load_ai_brain(logger):
    global SLICE_CONFIG, AI_KNOWLEDGE_BASE, AI_LOADED
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
                tiles = slice_image_numpy(img, SLICE_CONFIG)
                if tiles:
                    src, trg = doc.get('label_source'), doc.get('label_target')
                    tiles[src], tiles[trg] = tiles[trg], tiles[src] 
                    AI_KNOWLEDGE_BASE.append(tiles)
            except: pass
        AI_LOADED = True
        logger(f"🧠 AI Ready! {len(AI_KNOWLEDGE_BASE)} Masters Loaded.")
    except Exception as e: logger(f"❌ AI Load Error: {e}")

def slice_image_numpy(img, cfg):
    h, w, _ = img.shape
    # Validation to avoid crashing on small images
    if cfg['top']+cfg['bottom'] >= h or cfg['left']+cfg['right'] >= w: return None
    
    crop = img[cfg['top']:h-cfg['bottom'], cfg['left']:w-cfg['right']]
    if crop.size == 0: return None
    
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ch, cw = gray.shape
    th, tw = ch // 2, cw // 4
    return [gray[r*th:(r+1)*th, c*tw:(c+1)*tw] for r in range(2) for c in range(4)]

def get_swap_indices_logic(puzzle_img_path, logger):
    """
    MAJORITY VOTING LOGIC:
    Checks ALL masters, finds top matches, and takes a vote.
    """
    if not AI_KNOWLEDGE_BASE: return None, None
    
    puzzle_img = cv2.imread(puzzle_img_path)
    if puzzle_img is None: return None, None
    puzzle_tiles = slice_image_numpy(puzzle_img, SLICE_CONFIG)
    if not puzzle_tiles: return None, None

    # 1. Collect Valid Votes
    votes = []
    threshold_score = 5000000 # Loose threshold to gather candidates
    
    # Compare with EVERY master in DB
    for master in AI_KNOWLEDGE_BASE:
        if master[0].shape != puzzle_tiles[0].shape: continue
        
        # Calculate total difference for this background
        diff_score = sum(np.sum(cv2.absdiff(puzzle_tiles[i], master[i])) for i in range(8))
        
        # If this background looks similar enough
        if diff_score < threshold_score: 
            # Find the swap for THIS specific master
            tile_diffs = []
            for i in range(8):
                d = cv2.absdiff(puzzle_tiles[i], master[i])
                _, th = cv2.threshold(d, 30, 255, cv2.THRESH_BINARY)
                tile_diffs.append((np.sum(th), i))
            
            tile_diffs.sort(key=lambda x: x[0], reverse=True)
            # The top 2 distinct tiles
            t1, t2 = tile_diffs[0][1], tile_diffs[1][1]
            
            # Store vote (sorted tuple so (0,7) is same as (7,0))
            vote = tuple(sorted((t1, t2)))
            votes.append(vote)

    # 2. Count Votes
    if not votes:
        logger("⚠️ No similar backgrounds found in DB.")
        return None, None

    vote_counts = Counter(votes)
    most_common = vote_counts.most_common(1) # Get the winner
    
    winner_swap = most_common[0][0]
    winner_count = most_common[0][1]
    
    logger(f"🗳️ VOTING RESULT: Winner {winner_swap} with {winner_count}/{len(votes)} votes.")
    
    return winner_swap[0], winner_swap[1]

# --- MAIN SOLVER ---
async def solve_captcha(page, session_id, logger=print):
    await load_ai_brain(logger)
    
    vp = page.viewport_size
    logger(f"📏 Viewport: {vp['width']}x{vp['height']}")

    logger("⏳ Solver: Waiting 5s for image render...")
    await asyncio.sleep(5)

    img_path = f"./captures/{session_id}_puzzle.png"
    try: await page.screenshot(path=img_path)
    except Exception as e: logger(f"❌ Screen Error: {e}"); return False

    # --- AUTO SCALING FACTOR ---
    # Compare Screenshot Width vs Viewport Width
    img_cv = cv2.imread(img_path)
    real_h, real_w, _ = img_cv.shape
    
    scale_x = real_w / vp['width']
    scale_y = real_h / vp['height']
    
    logger(f"📐 Scale Factor Detected: X={scale_x:.2f}, Y={scale_y:.2f}")

    # --- AI LOGIC (WITH VOTING) ---
    logger("🧠 AI holding an election...")
    src_idx, trg_idx = get_swap_indices_logic(img_path, logger)
    if src_idx is None: logger("⚠️ AI Failed."); return False
        
    logger(f"🎯 AI TARGET: Swap Tile {src_idx} -> {trg_idx}")

    # --- COORDINATE CALCULATION (With Scaling) ---
    grid_x = SLICE_CONFIG['left']
    grid_y = SLICE_CONFIG['top']
    grid_w = real_w - SLICE_CONFIG['left'] - SLICE_CONFIG['right']
    grid_h = real_h - SLICE_CONFIG['top'] - SLICE_CONFIG['bottom']
    
    tile_w = grid_w / 4
    tile_h = grid_h / 2

    def get_center(idx):
        r, c = idx // 4, idx % 4
        # Original High-Res Coords
        raw_cx = grid_x + (c * tile_w) + (tile_w / 2)
        raw_cy = grid_y + (r * tile_h) + (tile_h / 2)
        
        # 🔥 APPLY SCALING DOWN TO VIEWPORT 🔥
        final_x = raw_cx / scale_x
        final_y = raw_cy / scale_y
        return final_x, final_y

    sx, sy = get_center(src_idx)
    tx, ty = get_center(trg_idx)

    logger(f"📍 SCALED COORDS: Start({int(sx)},{int(sy)}) -> End({int(tx)},{int(ty)})")

    # Safety Check
    if sx > vp['width'] or sy > vp['height']:
        logger("❌ ERROR: Coords still outside! Calibration might be totally wrong.")
        return False

    # --- VISUAL DEBUG DOTS ---
    await page.evaluate(f"""
        document.querySelectorAll('.debug-dot').forEach(e => e.remove());
        function createDot(x, y, color) {{
            var d = document.createElement('div'); d.className = 'debug-dot';
            d.style.position = 'fixed'; d.style.left = (x - 10) + 'px'; d.style.top = (y - 10) + 'px';
            d.style.width = '20px'; d.style.height = '20px'; d.style.background = color; 
            d.style.borderRadius = '50%'; d.style.border = '3px solid white'; d.style.zIndex = '9999999';
            document.body.appendChild(d);
        }}
        createDot({sx}, {sy}, 'red');
        createDot({tx}, {ty}, 'blue');
    """)
    await asyncio.sleep(1) 

    # --- EXECUTE FORCE DRAG ---
    try:
        client = await page.context.new_cdp_session(page)
        
        # 1. FORCE TOUCH START
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchStart", 
            "touchPoints": [{"x": sx, "y": sy, "force": 1.0, "radiusX": 25, "radiusY": 25}]
        })
        
        # 2. HOLD
        logger("✊ Holding (Force Click)...")
        await asyncio.sleep(1.0) 

        # 3. FORCE DRAG
        logger("➡️ Force Dragging...")
        steps = 25
        for i in range(steps + 1):
            t = i / steps
            cx = sx + (tx - sx) * t
            cy = sy + (ty - sy) * t
            
            await client.send("Input.dispatchTouchEvent", {
                "type": "touchMove", 
                "touchPoints": [{"x": cx, "y": cy, "force": 1.0, "radiusX": 25, "radiusY": 25}]
            })
            await asyncio.sleep(0.04)

        # 4. RELEASE
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchEnd", "touchPoints": []
        })
        logger("✅ Drag Complete.")
        
    except Exception as e:
        logger(f"❌ Move Failed: {e}"); return False

    return True