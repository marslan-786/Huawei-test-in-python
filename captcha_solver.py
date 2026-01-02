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
    """Loads Slice Config & Master Images EXACTLY as saved"""
    global SLICE_CONFIG, AI_KNOWLEDGE_BASE, AI_LOADED
    if AI_LOADED: return 
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        
        # 1. Load Settings (RAW PIXELS)
        doc = await db[COL_SETTINGS].find_one({"_id": "slice_config"})
        if doc:
            SLICE_CONFIG = {k: doc.get(k,0) for k in ["top","bottom","left","right"]}
            logger(f"⚙️ Using Saved Config: {SLICE_CONFIG}")
        else:
            logger("⚠️ Config Missing! Please Calibrate first.")
            return

        # 2. Build Knowledge Base
        logger("🏗️ Building Knowledge Base...")
        AI_KNOWLEDGE_BASE = []
        async for doc in db[COL_CAPTCHAS].find({"status": "labeled"}):
            try:
                nparr = np.frombuffer(doc['image'], np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Cut exactly using the saved config
                tiles = slice_image_numpy(img, SLICE_CONFIG)
                if tiles:
                    src, trg = doc.get('label_source'), doc.get('label_target')
                    tiles[src], tiles[trg] = tiles[trg], tiles[src] 
                    AI_KNOWLEDGE_BASE.append(tiles)
            except: pass
        AI_LOADED = True
        logger(f"🧠 AI Ready! {len(AI_KNOWLEDGE_BASE)} Masters (Raw Size).")
    except Exception as e: logger(f"❌ AI Load Error: {e}")

def slice_image_numpy(img, cfg):
    """Simple Slicer - No Resizing"""
    h, w, _ = img.shape
    
    # Just verify image is big enough for the crop
    if cfg['top'] + cfg['bottom'] >= h: return None
    
    # EXACT CROP based on saved pixels
    crop = img[cfg['top'] : h - cfg['bottom'], cfg['left'] : w - cfg['right']]
    if crop.size == 0: return None
    
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ch, cw = gray.shape
    th, tw = ch // 2, cw // 4
    
    return [gray[r*th:(r+1)*th, c*tw:(c+1)*tw] for r in range(2) for c in range(4)]

def get_swap_indices_logic(puzzle_img_path, logger):
    if not AI_KNOWLEDGE_BASE: return None, None
    
    # 1. Read Raw Screenshot (Big Image)
    full_img = cv2.imread(puzzle_img_path)
    if full_img is None: return None, None
    
    # 2. Slice it directly (Assuming consistent screenshot size)
    puzzle_tiles = slice_image_numpy(full_img, SLICE_CONFIG)
    if not puzzle_tiles: 
        logger("❌ Slicing failed. Check calibration.")
        return None, None

    # 3. Majority Voting (Strict Matching)
    votes = []
    # Threshhold is strictly based on pixel difference. 
    # Since size matches perfectly, diff should be low for correct match.
    threshold_score = 4000000 
    
    for master in AI_KNOWLEDGE_BASE:
        # Strict Shape Check
        if master[0].shape != puzzle_tiles[0].shape: continue
        
        diff_score = sum(np.sum(cv2.absdiff(puzzle_tiles[i], master[i])) for i in range(8))
        
        if diff_score < threshold_score: 
            tile_diffs = []
            for i in range(8):
                d = cv2.absdiff(puzzle_tiles[i], master[i])
                _, th = cv2.threshold(d, 40, 255, cv2.THRESH_BINARY)
                tile_diffs.append((np.sum(th), i))
            
            tile_diffs.sort(key=lambda x: x[0], reverse=True)
            t1, t2 = tile_diffs[0][1], tile_diffs[1][1]
            votes.append(tuple(sorted((t1, t2))))

    if not votes:
        logger("⚠️ No Exact Match found in DB.")
        return None, None

    vote_counts = Counter(votes)
    winner = vote_counts.most_common(1)[0]
    return winner[0][0], winner[0][1]

# --- MAIN SOLVER ---
async def solve_captcha(page, session_id, logger=print):
    await load_ai_brain(logger)
    
    # Viewport info is ONLY needed for converting click coordinates
    vp = page.viewport_size
    
    logger("⏳ Solver: Waiting 5s for image render...")
    await asyncio.sleep(5)

    img_path = f"./captures/{session_id}_puzzle.png"
    try: await page.screenshot(path=img_path)
    except Exception as e: logger(f"❌ Screen Error: {e}"); return False

    # Check Scale Factor purely for CLICKING (Playwright uses logical pixels)
    # This does NOT affect AI analysis
    img_cv = cv2.imread(img_path)
    real_h, real_w, _ = img_cv.shape
    click_scale_x = real_w / vp['width']
    click_scale_y = real_h / vp['height']

    # --- AI LOGIC ---
    logger("🧠 AI Analyzing (Exact Match)...")
    src_idx, trg_idx = get_swap_indices_logic(img_path, logger)
    
    if src_idx is None: 
        logger("⚠️ AI Failed.")
        return False
        
    logger(f"🎯 AI TARGET: Swap Tile {src_idx} -> {trg_idx}")

    # --- CALCULATE EXACT PIXELS FROM CONFIG ---
    # We use the raw image dimensions + raw config
    
    # 1. Determine Grid Position in RAW Image Pixels
    grid_x = SLICE_CONFIG['left']
    grid_y = SLICE_CONFIG['top']
    grid_w = real_w - SLICE_CONFIG['left'] - SLICE_CONFIG['right']
    grid_h = real_h - SLICE_CONFIG['top'] - SLICE_CONFIG['bottom']
    
    tile_w = grid_w / 4
    tile_h = grid_h / 2

    def get_center_raw(idx):
        r, c = idx // 4, idx % 4
        raw_cx = grid_x + (c * tile_w) + (tile_w / 2)
        raw_cy = grid_y + (r * tile_h) + (tile_h / 2)
        return raw_cx, raw_cy

    raw_sx, raw_sy = get_center_raw(src_idx)
    raw_tx, raw_ty = get_center_raw(trg_idx)

    # 2. Convert Raw Pixels to Viewport Pixels for Click
    # Playwright needs viewport coordinates, not image pixels
    final_sx = raw_sx / click_scale_x
    final_sy = raw_sy / click_scale_y
    final_tx = raw_tx / click_scale_x
    final_ty = raw_ty / click_scale_y

    logger(f"🖱️ Action: {src_idx}({int(final_sx)},{int(final_sy)}) -> {trg_idx}({int(final_tx)},{int(final_ty)})")

    # --- VISUAL DEBUG (On Screen) ---
    await page.evaluate(f"""
        document.querySelectorAll('.debug-dot').forEach(e => e.remove());
        function createDot(x, y, color) {{
            var d = document.createElement('div'); d.className = 'debug-dot';
            d.style.position = 'fixed'; d.style.left = (x-10)+'px'; d.style.top = (y-10)+'px';
            d.style.width = '20px'; d.style.height = '20px'; d.style.background = color; 
            d.style.zIndex = '9999999'; d.style.borderRadius='50%'; d.style.border='3px solid white';
            document.body.appendChild(d);
        }}
        createDot({final_sx}, {final_sy}, 'lime');
        createDot({final_tx}, {final_ty}, 'magenta');
    """)
    await asyncio.sleep(0.5)

    # --- EXECUTE ---
    try:
        client = await page.context.new_cdp_session(page)
        
        # Start
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchStart", 
            "touchPoints": [{"x": final_sx, "y": final_sy, "force": 1.0, "radiusX": 25, "radiusY": 25}]
        })
        
        # Hold
        logger("✊ Holding...")
        await asyncio.sleep(0.8)

        # Move
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            cx = final_sx + (final_tx - final_sx) * t
            cy = final_sy + (final_ty - final_sy) * t
            await client.send("Input.dispatchTouchEvent", {
                "type": "touchMove", 
                "touchPoints": [{"x": cx, "y": cy, "force": 1.0, "radiusX": 25, "radiusY": 25}]
            })
            await asyncio.sleep(0.04)

        # End
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchEnd", "touchPoints": []
        })
        logger("✅ Drag Done.")
        
    except Exception as e:
        logger(f"❌ Move Error: {e}"); return False

    return True