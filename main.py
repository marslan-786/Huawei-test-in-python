import uvicorn
import base64
import cv2
import numpy as np
import asyncio
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from bson import ObjectId

# --- CONFIGURATION ---
MONGO_URI = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"
DB_NAME = "huawei_captcha"
COL_CAPTCHAS = "captchas"
COL_SETTINGS = "bot_settings"

app = FastAPI()

# Database
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
col_captchas = db[COL_CAPTCHAS]
col_settings = db[COL_SETTINGS]

# --- GLOBAL VARIABLES (AI BRAIN RAM) ---
# یہ وہ جگہ ہے جہاں ہم "پرفیکٹ بیک گراؤنڈز" کو ریم میں رکھیں گے
AI_KNOWLEDGE_BASE = [] 
AI_READY = False

# --- HELPER FUNCTIONS (The Brain Logic) ---

async def get_config_internal():
    """Helper to get settings quickly based on your previous tool"""
    doc = await col_settings.find_one({"_id": "slice_config"})
    if doc: return {k: doc.get(k,0) for k in ["top","bottom","left","right"]}
    return {"top":0, "bottom":0, "left":0, "right":0}

def slice_image_numpy(img, cfg):
    """Crops and slices image into 8 numpy tiles (Grayscale for AI)"""
    h, w, _ = img.shape
    # Crop
    crop = img[cfg['top'] : h-cfg['bottom'], cfg['left'] : w-cfg['right']]
    if crop.size == 0: return None
    
    # Convert to Grayscale (Better for matching, ignores slight color shifts)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    
    ch, cw = gray.shape
    th, tw = ch // 2, cw // 4
    
    tiles = []
    for r in range(2):
        for c in range(4):
            tile = gray[r*th : (r+1)*th, c*tw : (c+1)*tw]
            tiles.append(tile)
    return tiles

def solve_logic(puzzle_tiles_gray):
    """The actual AI Math: Compares puzzle tiles vs knowledge base"""
    if not AI_READY or not AI_KNOWLEDGE_BASE: return None, "AI Not Trained Yet"

    best_bg_score = float('inf')
    best_bg_tiles = None

    # 1. Find the closest matching background
    # ہم چیک کریں گے کہ پزل کے 8 ٹکڑے کس "ماسٹر بیک گراؤنڈ" کے سب سے قریب ہیں
    for master_tiles in AI_KNOWLEDGE_BASE:
        total_diff = 0
        # Check shape compatibility first
        if master_tiles[0].shape != puzzle_tiles_gray[0].shape: continue

        for i in range(8):
            # Calculate absolute difference between puzzle tile and master tile
            diff = cv2.absdiff(puzzle_tiles_gray[i], master_tiles[i])
            total_diff += np.sum(diff)
        
        if total_diff < best_bg_score:
            best_bg_score = total_diff
            best_bg_tiles = master_tiles

    if best_bg_tiles is None:
        return None, "No matching background found"

    # 2. Identify the swapped tiles based on highest difference
    # اب ہمیں بہترین بیک گراؤنڈ مل گیا ہے۔ ہم دیکھتے ہیں کہ کن دو ٹائلز میں سب سے زیادہ فرق ہے۔
    tile_diffs = []
    for i in range(8):
        diff = cv2.absdiff(puzzle_tiles_gray[i], best_bg_tiles[i])
        # Thresholding to ignore minor noise
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        score = np.sum(thresh)
        tile_diffs.append((score, i))

    # Sort by difference score (descending)
    tile_diffs.sort(key=lambda x: x[0], reverse=True)

    # The top 2 tiles with highest difference are likely the swapped ones
    tile1_idx = tile_diffs[0][1]
    tile2_idx = tile_diffs[1][1]
    
    # Return sorted list for easy comparison (e.g., [2, 5])
    return sorted([tile1_idx, tile2_idx]), "Solved"

# --- MODELS ---
class SaveParams(BaseModel):
    top: int; bottom: int; left: int; right: int

# --- UI ---
@app.get("/", response_class=HTMLResponse)
async def ui():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei AI Final Trainer</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.js"></script>
        <style>
            body { background: #0a0a0a; color: #eee; margin: 0; padding: 10px; font-family: 'Segoe UI', monospace; text-align: center; }
            .container { max-width: 900px; margin: 0 auto; }
            h2 { color: #00e676; border-bottom: 2px solid #333; padding-bottom: 10px; letter-spacing: 1px; }
            
            /* SECTIONS */
            .section { background: #141414; border: 1px solid #333; border-radius: 8px; padding: 15px; margin-bottom: 20px; }
            .sec-title { color: #ff9100; margin-top: 0; text-align: left; border-bottom: 1px solid #222; }

            /* CALIBRATOR STYLES */
            .img-container { height: 40vh; background: #000; border: 1px solid #333; margin-bottom: 10px; }
            img { max-width: 100%; }
            .btn-row { display: flex; gap: 10px; }
            button { flex: 1; padding: 12px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; color: white; transition: 0.2s; }
            button:hover { opacity: 0.9; transform: scale(0.98); }
            .btn-blue { background: #2979ff; } .btn-green { background: #00c853; } 
            .btn-purple { background: #6200ea; font-size: 16px; } .btn-red { background: #d50000; font-size: 16px; }

            /* AI VISUALS */
            .ai-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3px; border: 3px solid #6200ea; margin-top: 10px; display: none; }
            .tile-box { position: relative; }
            .tile-img { width: 100%; display: block; border: 1px solid #333; }
            .tile-idx { position: absolute; top: 0; left: 0; background: rgba(0,0,0,0.7); color: white; font-size: 10px; padding: 2px; }
            .highlight-ai { border: 3px solid red !important; z-index: 10; }
            .highlight-real { border: 3px solid #00e676 !important; }

            .result-box { background: #222; padding: 15px; margin-top: 10px; border-radius: 5px; text-align: left; font-size: 14px; display: none; }
            .res-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
            .match-success { color: #00e676; font-weight: bold; font-size: 18px; text-align: center; margin-top: 10px; }
            .match-fail { color: red; font-weight: bold; font-size: 18px; text-align: center; margin-top: 10px; }

            /* LOGS */
            .console { background: #000; color: #00e676; height: 150px; overflow-y: auto; text-align: left; padding: 10px; border: 1px solid #333; font-size: 11px; font-family: 'Courier New'; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🧠 HUAWEI AI TRAINER FINAL</h2>

            <div class="section">
                <h3 class="sec-title">🛠️ 1. SLICE CALIBRATION</h3>
                <div class="img-container"><img id="image" src=""></div>
                <div class="btn-row">
                    <button class="btn-blue" onclick="loadCalibImage()">🔄 LOAD NEW</button>
                    <button class="btn-green" onclick="saveCrop()">💾 SAVE SETTINGS</button>
                </div>
            </div>

            <div class="section" style="border-color: #6200ea;">
                <h3 class="sec-title" style="color: #6200ea;">🤖 2. AI BRAIN & TESTING</h3>
                <p style="font-size:12px; color:#aaa;">First build knowledge, then test solver.</p>
                
                <div class="btn-row">
                    <button class="btn-purple" onclick="trainAI()">🏗️ BUILD KNOWLEDGE BASE (RAM)</button>
                    <button class="btn-red" onclick="runSolverTest()">🧪 RUN REAL AI SOLVER</button>
                </div>

                <div id="ai-results-area" style="display:none;">
                    <div class="ai-grid" id="ai-tiles-box"></div>
                    
                    <div class="result-box" id="res-box">
                        <div class="res-row"><span>Test Image ID:</span> <span id="res-id">...</span></div>
                        <div class="res-row" style="color:#aaa;"><span>Real Answer (DB):</span> <span id="res-real">...</span></div>
                        <div class="res-row" style="color:yellow;"><span>AI Calculation:</span> <span id="res-ai">...</span></div>
                        <div id="final-verdict"></div>
                    </div>
                </div>
            </div>

            <div class="console" id="logs">System Ready.</div>
        </div>

        <script>
            let cropper;

            function log(msg) {
                const c = document.getElementById('logs');
                c.innerHTML = `<div>[${new Date().toLocaleTimeString()}] ${msg}</div>` + c.innerHTML;
            }

            // --- CALIBRATION JS ---
            function loadCalibImage() {
                log("Fetching random image for calibration...");
                fetch('/get_random').then(r=>r.json()).then(d=>{
                    if(d.status === 'error') { alert(d.message); return; }
                    const img = document.getElementById('image');
                    img.src = "data:image/jpeg;base64," + d.image;
                    if(cropper) cropper.destroy();
                    setTimeout(() => {
                        cropper = new Cropper(img, {
                            viewMode: 1, dragMode: 'move', autoCropArea: 0.5,
                            restore: false, guides: false, center: false, highlight: false,
                            cropBoxMovable: true, cropBoxResizable: true, toggleDragModeOnDblclick: false,
                        });
                    }, 100);
                });
            }

            function saveCrop() {
                if(!cropper) return;
                const data = cropper.getData(true);
                const imgData = cropper.getImageData();
                const config = {
                    top: Math.round(data.y),
                    left: Math.round(data.x),
                    right: Math.round(imgData.naturalWidth - (data.x + data.width)),
                    bottom: Math.round(imgData.naturalHeight - (data.y + data.height))
                };
                 // Safety checks
                if(config.top<0)config.top=0; if(config.left<0)config.left=0;
                if(config.right<0)config.right=0; if(config.bottom<0)config.bottom=0;

                fetch('/save_config', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(config)})
                .then(r=>r.json()).then(d=>{ log("✅ Settings saved to DB: " + JSON.stringify(config)); alert("Settings Saved!"); });
            }

            // --- AI JS ---
            function trainAI() {
                log("🏗️ Starting AI Training process (Reading DB & Building RAM Knowledge)...");
                alert("Training started! Check logs below. This might take a few seconds.");
                fetch('/train_ai').then(r=>r.json()).then(d=>{
                    log("🎉 " + d.message);
                    alert(d.message);
                });
            }

            function runSolverTest() {
                log("🧪 Running Real AI Solver on a random puzzle...");
                document.getElementById('ai-results-area').style.display = 'block';
                document.getElementById('res-box').style.display = 'block';
                document.getElementById('ai-tiles-box').innerHTML = "Loading...";
                document.getElementById('final-verdict').innerHTML = "Calculating...";

                fetch('/run_real_test').then(r=>r.json()).then(d=>{
                    if(d.status === 'error') {
                        log("❌ Error: " + d.message); alert(d.message); return;
                    }

                    // Update Text Results
                    document.getElementById('res-id').innerText = d.id;
                    document.getElementById('res-real').innerText = JSON.stringify(d.real_answer);
                    document.getElementById('res-ai').innerText = JSON.stringify(d.ai_answer);
                    
                    const verdict = document.getElementById('final-verdict');
                    if(d.match) {
                        verdict.innerHTML = "<div class='match-success'>🌟 SUCCESS! AI MATCHED REAL ANSWER.</div>";
                        log("✅ AI Test Passed for ID: " + d.id);
                    } else {
                        verdict.innerHTML = "<div class='match-fail'>❌ FAILED. AI Prediction Incorrect.</div>";
                        log("⚠️ AI Test Failed for ID: " + d.id);
                    }

                    // Render Tiles with Highlights
                    const grid = document.getElementById('ai-tiles-box');
                    grid.innerHTML = "";
                    grid.style.display = 'grid';
                    
                    d.tiles.forEach((t, idx) => {
                        let classes = "tile-img";
                        // Highlight AI prediction in RED
                        if (d.ai_answer && d.ai_answer.includes(idx)) classes += " highlight-ai";
                        
                        grid.innerHTML += `
                            <div class="tile-box">
                                <div class="${classes}">
                                    <img src="data:image/jpeg;base64,${t}" style="width:100%; display:block;">
                                </div>
                                <span class="tile-idx">${idx}</span>
                            </div>
                        `;
                    });
                });
            }

            // Auto load calib image on start
            window.onload = loadCalibImage;
        </script>
    </body>
    </html>
    """

# --- API ENDPOINTS ---

@app.get("/get_random")
async def get_random_api():
    pipeline = [{"$match": {"image": {"$exists": True}}}, {"$sample": {"size": 1}}]
    try:
        cursor = col_captchas.aggregate(pipeline)
        doc = await cursor.to_list(length=1)
        if not doc: return {"status": "error", "message": "DB Empty"}
        b64 = base64.b64encode(bytes(doc[0]['image'])).decode('utf-8')
        return {"status": "ok", "id": str(doc[0]["_id"]), "image": b64}
    except: return {"status": "error", "message": "Failed fetch"}

@app.post("/save_config")
async def save_config_api(p: SaveParams):
    await col_settings.update_one({"_id": "slice_config"}, {"$set": p.dict()}, upsert=True)
    return {"status": "saved"}

# --- NEW AI ENDPOINTS ---

@app.get("/train_ai")
async def train_ai_endpoint():
    """Fetches labeled images, fixes them, stores perfect grayscale tiles in RAM"""
    global AI_KNOWLEDGE_BASE, AI_READY
    AI_KNOWLEDGE_BASE = [] # Reset
    AI_READY = False
    
    cfg = await get_config_internal()
    if cfg['top'] == 0 and cfg['bottom'] == 0:
         return {"status": "error", "message": "Please Calibrate and Save settings first!"}

    # Fetch all labeled images
    cursor = col_captchas.find({"status": "labeled"})
    count = 0
    async for doc in cursor:
        try:
            nparr = np.frombuffer(doc['image'], np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 1. Slice into 8 grayscale tiles
            tiles_gray = slice_image_numpy(img, cfg)
            if not tiles_gray: continue

            # 2. FIX THE PUZZLE based on labels to create "Master Tiles"
            src = doc.get('label_source')
            trg = doc.get('label_target')
            if src is not None and trg is not None:
                # Swap back to original positions
                tiles_gray[src], tiles_gray[trg] = tiles_gray[trg], tiles_gray[src]
                
                # Store this set of 8 perfect grayscale tiles in RAM
                AI_KNOWLEDGE_BASE.append(tiles_gray)
                count += 1
        except Exception as e:
            print(f"Train Error: {e}")

    if count > 0:
        AI_READY = True
        msg = f"AI Knowledge Base Built successfully with {count} perfect backgrounds in RAM."
    else:
        msg = "Failed to build knowledge base. Are there labeled images?"
        
    return {"status": "ok", "message": msg, "count": count}


@app.get("/run_real_test")
async def run_real_test_endpoint():
    """Picks a random puzzle, runs solver logic against RAM knowledge base"""
    if not AI_READY:
        return {"status": "error", "message": "AI Brain is empty. Please click 'BUILD KNOWLEDGE BASE' first."}
    
    cfg = await get_config_internal()

    # Pick a random labeled puzzle to test (acting as an unsolved one)
    pipeline = [{"$match": {"status": "labeled"}}, {"$sample": {"size": 1}}]
    cursor = col_captchas.aggregate(pipeline)
    docs = await cursor.to_list(length=1)
    if not docs: return {"status": "error", "message": "No test data found."}
    doc = docs[0]

    # 1. Prepare the Puzzle
    nparr = np.frombuffer(doc['image'], np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    # Slice puzzle into grayscale tiles for the solver
    puzzle_tiles_gray = slice_image_numpy(img, cfg)
    
    if not puzzle_tiles_gray:
         return {"status": "error", "message": "Slicing failed with current config."}

    # 2. RUN THE SOLVER LOGIC
    # This function does the heavy lifting: matching and difference calculation
    ai_swap_indices, _ = solve_logic(puzzle_tiles_gray)
    
    # 3. Prepare Results for UI
    real_src = doc.get('label_source')
    real_trg = doc.get('label_target')
    real_swap = sorted([real_src, real_trg])
    
    # Check if AI got it right
    match = (ai_swap_indices == real_swap)

    # Generate visual tiles for UI (Base64)
    tiles_b64 = []
    for t_gray in puzzle_tiles_gray:
        _, buf = cv2.imencode('.jpg', t_gray)
        tiles_b64.append(base64.b64encode(buf).decode('utf-8'))

    return {
        "status": "ok",
        "id": str(doc["_id"]),
        "tiles": tiles_b64,
        "real_answer": real_swap,
        "ai_answer": ai_swap_indices,
        "match": match
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)