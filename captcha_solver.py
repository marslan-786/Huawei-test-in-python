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
        logger(f"🧠 AI Ready! {len(AI_KNOWLEDGE_BASE)} Masters.")
    except Exception as e: logger(f"❌ AI Load Error: {e}")

def slice_image_numpy(img, cfg):
    h, w, _ = img.shape
    crop = img[cfg['top']:h-cfg['bottom'], cfg['left']:w-cfg['right']]
    if crop.size == 0: return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ch, cw = gray.shape
    th, tw = ch // 2, cw // 4
    return [gray[r*th:(r+1)*th, c*tw:(c+1)*tw] for r in range(2) for c in range(4)]

def get_swap_indices_logic(puzzle_img_path):
    if not AI_KNOWLEDGE_BASE: return None, None
    puzzle_img = cv2.imread(puzzle_img_path)
    if puzzle_img is None: return None, None
    puzzle_tiles = slice_image_numpy(puzzle_img, SLICE_CONFIG)
    if not puzzle_tiles: return None, None

    best_score = float('inf'); best_master = None
    for master in AI_KNOWLEDGE_BASE:
        if master[0].shape != puzzle_tiles[0].shape: continue
        diff = sum(np.sum(cv2.absdiff(puzzle_tiles[i], master[i])) for i in range(8))
        if diff < best_score: best_score = diff; best_master = master

    if not best_master: return None, None

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
    
    # Check viewport size to prevent clicking out of bounds
    vp = page.viewport_size
    logger(f"📏 Viewport Size: {vp['width']}x{vp['height']}")

    logger("⏳ Solver: Waiting 5s for image render...")
    await asyncio.sleep(5)

    img_path = f"./captures/{session_id}_puzzle.png"
    try: await page.screenshot(path=img_path)
    except Exception as e: logger(f"❌ Screen Error: {e}"); return False

    logger("🧠 AI Calculating...")
    src_idx, trg_idx = get_swap_indices_logic(img_path)
    if src_idx is None: logger("⚠️ AI Failed: No match."); return False
        
    logger(f"🎯 AI TARGET: Swap Tile {src_idx} -> {trg_idx}")

    # Calculate Coordinates
    img = cv2.imread(img_path)
    h, w, _ = img.shape
    
    grid_x = SLICE_CONFIG['left']
    grid_y = SLICE_CONFIG['top']
    grid_w = w - SLICE_CONFIG['left'] - SLICE_CONFIG['right']
    grid_h = h - SLICE_CONFIG['top'] - SLICE_CONFIG['bottom']
    
    tile_w = grid_w / 4
    tile_h = grid_h / 2

    def get_center(idx):
        r, c = idx // 4, idx % 4
        cx = grid_x + (c * tile_w) + (tile_w / 2)
        cy = grid_y + (r * tile_h) + (tile_h / 2)
        return cx, cy

    sx, sy = get_center(src_idx)
    tx, ty = get_center(trg_idx)

    logger(f"📍 COORDS: Start({int(sx)},{int(sy)}) -> End({int(tx)},{int(ty)})")

    # Safety Check: Is click inside viewport?
    if sx > vp['width'] or sy > vp['height']:
        logger("❌ CRITICAL: Click coordinates are OUTSIDE viewport! Re-calibrate.")
        return False

    # --- 🔥 FIXED VISUAL DOTS (ALWAYS ON TOP) 🔥 ---
    await page.evaluate(f"""
        // Clean old dots
        document.querySelectorAll('.debug-dot').forEach(e => e.remove());

        function createDot(x, y, color) {{
            var d = document.createElement('div');
            d.className = 'debug-dot';
            d.style.position = 'fixed'; // FIXED stays on screen glass
            d.style.left = (x - 10) + 'px';
            d.style.top = (y - 10) + 'px';
            d.style.width = '20px'; 
            d.style.height = '20px'; 
            d.style.background = color; 
            d.style.borderRadius = '50%'; 
            d.style.border = '3px solid white';
            d.style.boxShadow = '0 0 10px black';
            d.style.zIndex = '2147483647'; // MAX Z-INDEX
            d.style.pointerEvents = 'none';
            document.body.appendChild(d);
        }}
        createDot({sx}, {sy}, 'red');  // START
        createDot({tx}, {ty}, 'blue'); // END
    """)
    
    # Wait to see dots in video
    await asyncio.sleep(1) 

    # --- EXECUTE FORCE DRAG ---
    try:
        client = await page.context.new_cdp_session(page)
        
        # 1. FORCE TOUCH START (Simulate Thumb Press)
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchStart", 
            "touchPoints": [{
                "x": sx, "y": sy, 
                "force": 1.0,      # MAX PRESSURE
                "radiusX": 25,     # THUMB SIZE
                "radiusY": 25
            }]
        })
        
        # 2. HOLD (Wait for physics to engage)
        logger("✊ Holding (Force Click)...")
        await asyncio.sleep(1.0) 

        # 3. HEAVY DRAG
        logger("➡️ Force Dragging...")
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            cx = sx + (tx - sx) * t
            cy = sy + (ty - sy) * t
            
            await client.send("Input.dispatchTouchEvent", {
                "type": "touchMove", 
                "touchPoints": [{
                    "x": cx, "y": cy,
                    "force": 1.0,  # KEEP PRESSURE
                    "radiusX": 25,
                    "radiusY": 25
                }]
            })
            await asyncio.sleep(0.05) # Slower drag

        # 4. RELEASE
        await client.send("Input.dispatchTouchEvent", {
            "type": "touchEnd", 
            "touchPoints": []
        })
        logger("✅ Force Drag Complete.")
        
    except Exception as e:
        logger(f"❌ Move Failed: {e}"); return False

    return True