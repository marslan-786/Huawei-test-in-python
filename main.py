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

# In-Memory Settings Cache
current_settings = {"top": 0, "bottom": 0, "left": 0, "right": 0}

# --- STARTUP ---
@app.on_event("startup")
async def startup():
    global current_settings
    try:
        await client.server_info()
        doc = await col_settings.find_one({"_id": "slice_config"})
        if doc:
            current_settings = {k: doc.get(k,0) for k in ["top","bottom","left","right"]}
            print(f"✅ Loaded Settings from DB: {current_settings}")
    except Exception as e:
        print(f"❌ DB Error: {e}")

# --- MODELS ---
class SliceParams(BaseModel):
    id: str
    top: int
    bottom: int
    left: int
    right: int

class SaveConfigParams(BaseModel):
    top: int
    bottom: int
    left: int
    right: int

# --- UI ---
@app.get("/", response_class=HTMLResponse)
async def ui():
    return """
    <html>
    <head>
        <title>Huawei AI Master Tool</title>
        <style>
            body { background: #0d0d0d; color: #eee; font-family: monospace; padding: 20px; text-align: center; }
            .container { max-width: 950px; margin: 0 auto; background: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #333; }
            h2 { color: #00e676; margin-top: 0; border-bottom: 1px solid #333; padding-bottom: 10px; }
            
            /* GRID LAYOUT */
            .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; text-align: left; }
            
            /* INPUTS */
            .control-panel { background: #222; padding: 15px; border-radius: 8px; }
            .inp-row { display: flex; justify-content: space-between; margin-bottom: 10px; }
            input { width: 60px; background: #000; border: 1px solid #555; color: #00e676; text-align: center; font-weight: bold; padding: 5px; }
            label { font-size: 12px; color: #aaa; align-self: center; }

            /* BUTTONS */
            button { width: 100%; padding: 12px; margin-top: 5px; font-weight: bold; cursor: pointer; border: none; border-radius: 5px; color: white; transition: 0.2s; }
            button:hover { opacity: 0.8; }
            .btn-blue { background: #2979ff; }
            .btn-org { background: #ff9100; }
            .btn-green { background: #00c853; }
            .btn-red { background: #d50000; }
            
            /* VISUALS */
            .preview-area { background: #000; border: 1px solid #444; padding: 10px; text-align: center; min-height: 200px; }
            #raw-img { max-width: 100%; max-height: 150px; display: none; margin: 0 auto; }
            
            .tiles-wrapper { display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px; margin-top: 10px; border: 2px solid #ff9100; display:none; }
            .tile { width: 100%; display: block; border: 1px solid #333; }
            
            /* CONSOLE */
            .console { background: #000; color: #00e676; height: 150px; overflow-y: auto; text-align: left; padding: 10px; border: 1px solid #333; margin-top: 20px; font-size: 12px; }
            .log-entry { margin-bottom: 4px; border-bottom: 1px solid #111; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🛠️ SLICER & AI LOGIC TESTER</h2>
            
            <div class="main-grid">
                <div class="control-panel">
                    <h3 style="margin-top:0">1. CALIBRATION</h3>
                    <div class="inp-row"><label>TOP Crop</label><input type="number" id="t"></div>
                    <div class="inp-row"><label>BOTTOM Crop</label><input type="number" id="b"></div>
                    <div class="inp-row"><label>LEFT Crop</label><input type="number" id="l"></div>
                    <div class="inp-row"><label>RIGHT Crop</label><input type="number" id="r"></div>
                    
                    <button class="btn-blue" onclick="loadImage()">🔄 LOAD IMAGE</button>
                    <button class="btn-org" onclick="slicePreview()">🔪 PREVIEW CUTS</button>
                    <button class="btn-green" onclick="saveSettings()">💾 SAVE TO DB</button>
                    
                    <hr style="border-color:#333; margin:15px 0;">
                    
                    <h3 style="margin-top:0">2. AI TESTING</h3>
                    <button class="btn-red" onclick="testAI()">🧠 TEST LOGIC (Random)</button>
                    <button class="btn-blue" style="background:#6200ea" onclick="batchCheck()">⚡ CHECK ALL IMAGES</button>
                </div>

                <div class="preview-area">
                    <h4 style="margin:0; color:#aaa;">VISUAL FEEDBACK</h4>
                    <br>
                    <img id="raw-img">
                    <div id="tiles-box" class="tiles-wrapper"></div>
                    <div id="ai-result" style="margin-top:10px; font-weight:bold; color:yellow;"></div>
                </div>
            </div>

            <div class="console" id="logs">System Ready...</div>
        </div>

        <script>
            let currentId = null;

            // Init
            window.onload = () => {
                log("Connecting to DB...");
                fetch('/get_config').then(r=>r.json()).then(d=>{
                    document.getElementById('t').value = d.top;
                    document.getElementById('b').value = d.bottom;
                    document.getElementById('l').value = d.left;
                    document.getElementById('r').value = d.right;
                    log("✅ Loaded Config: " + JSON.stringify(d));
                });
            };

            function log(msg) {
                const c = document.getElementById('logs');
                c.innerHTML = `<div class='log-entry'>[${new Date().toLocaleTimeString()}] ${msg}</div>` + c.innerHTML;
            }

            function loadImage() {
                log("Fetching random image...");
                fetch('/get_random').then(r=>r.json()).then(d=>{
                    if(d.status === 'error') { alert(d.message); return; }
                    currentId = d.id;
                    const img = document.getElementById('raw-img');
                    img.src = "data:image/jpeg;base64," + d.image;
                    img.style.display = 'block';
                    document.getElementById('tiles-box').style.display = 'none';
                    document.getElementById('ai-result').innerText = "";
                    log("📸 Loaded Image ID: " + d.id);
                });
            }

            function slicePreview() {
                if(!currentId) { alert("Load image first"); return; }
                const p = getParams();
                p.id = currentId;
                
                log("🔪 Slicing...");
                fetch('/slice', {
                    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(p)
                }).then(r=>r.json()).then(d=>{
                    const box = document.getElementById('tiles-box');
                    box.innerHTML = "";
                    box.style.display = 'grid';
                    d.tiles.forEach(t => {
                        box.innerHTML += `<img class="tile" src="data:image/jpeg;base64,${t}">`;
                    });
                    log("✅ Sliced into 8 tiles.");
                });
            }

            function saveSettings() {
                const p = getParams();
                fetch('/save_config', {
                    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(p)
                }).then(r=>r.json()).then(d=>{
                    log("💾 CONFIG SAVED TO MONGODB!");
                    alert("Settings Saved!");
                });
            }

            function testAI() {
                log("🤖 Starting AI Logic Test...");
                fetch('/test_ai').then(r=>r.json()).then(d=>{
                    document.getElementById('ai-result').innerText = d.message;
                    
                    if(d.image) {
                        document.getElementById('raw-img').src = "data:image/jpeg;base64," + d.image;
                        document.getElementById('raw-img').style.display = 'block';
                        
                        // Show slices
                        const box = document.getElementById('tiles-box');
                        box.innerHTML = "";
                        box.style.display = 'grid';
                        d.tiles.forEach((t, i) => {
                            let border = "1px solid #333";
                            if(i === d.solution[0] || i === d.solution[1]) border = "2px solid yellow";
                            box.innerHTML += `<img class="tile" style="border:${border}" src="data:image/jpeg;base64,${t}">`;
                        });
                    }
                    log("🏁 " + d.message);
                });
            }

            function batchCheck() {
                log("⚡ Starting Batch Process on DB...");
                fetch('/batch_check').then(r=>r.json()).then(d=>{
                    log(`📊 BATCH RESULT: Checked ${d.total}. Success: ${d.success}. Failed: ${d.failed}`);
                    alert(`Check Complete!\nSuccess: ${d.success}\nFailed: ${d.failed}`);
                });
            }

            function getParams() {
                return {
                    top: parseInt(document.getElementById('t').value)||0,
                    bottom: parseInt(document.getElementById('b').value)||0,
                    left: parseInt(document.getElementById('l').value)||0,
                    right: parseInt(document.getElementById('r').value)||0
                };
            }
        </script>
    </body>
    </html>
    """

# --- API ---

@app.get("/get_config")
async def get_config():
    doc = await col_settings.find_one({"_id": "slice_config"})
    if doc: return {k: doc.get(k,0) for k in ["top","bottom","left","right"]}
    return current_settings

@app.get("/get_random")
async def get_random():
    pipeline = [{"$match": {"image": {"$exists": True}}}, {"$sample": {"size": 1}}]
    cursor = col_captchas.aggregate(pipeline)
    docs = await cursor.to_list(length=1)
    if not docs: return {"status": "error", "message": "DB Empty"}
    doc = docs[0]
    b64 = base64.b64encode(bytes(doc['image'])).decode('utf-8')
    return {"status": "ok", "id": str(doc["_id"]), "image": b64}

@app.post("/slice")
async def slice_img(p: SliceParams):
    try:
        doc = await col_captchas.find_one({"_id": ObjectId(p.id)})
        nparr = np.frombuffer(doc['image'], np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Crop & Slice Logic
        h, w, _ = img.shape
        crop = img[p.top : h-p.bottom, p.left : w-p.right]
        ch, cw, _ = crop.shape
        th, tw = ch//2, cw//4
        
        tiles = []
        for r in range(2):
            for c in range(4):
                tile = crop[r*th:(r+1)*th, c*tw:(c+1)*tw]
                _, buf = cv2.imencode('.jpg', tile)
                tiles.append(base64.b64encode(buf).decode('utf-8'))
        
        return {"tiles": tiles}
    except Exception as e:
        return {"tiles": []}

@app.post("/save_config")
async def save_conf(p: SaveConfigParams):
    global current_settings
    current_settings = p.dict()
    await col_settings.update_one({"_id": "slice_config"}, {"$set": current_settings}, upsert=True)
    return {"status": "saved"}

@app.get("/test_ai")
async def test_ai():
    # 1. Get Labeled Image
    pipeline = [{"$match": {"status": "labeled"}}, {"$sample": {"size": 1}}]
    cursor = col_captchas.aggregate(pipeline)
    docs = await cursor.to_list(length=1)
    
    if not docs: return {"message": "No Labeled Images found!"}
    doc = docs[0]
    
    # 2. Slice using SAVED Settings
    nparr = np.frombuffer(doc['image'], np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    h, w, _ = img.shape
    
    # Apply Config
    cfg = current_settings
    crop = img[cfg['top'] : h-cfg['bottom'], cfg['left'] : w-cfg['right']]
    
    # 3. Create Tiles
    ch, cw, _ = crop.shape
    th, tw = ch//2, cw//4
    tiles = []
    for r in range(2):
        for c in range(4):
            tile = crop[r*th:(r+1)*th, c*tw:(c+1)*tw]
            _, buf = cv2.imencode('.jpg', tile)
            tiles.append(base64.b64encode(buf).decode('utf-8'))
    
    full_b64 = base64.b64encode(doc['image']).decode('utf-8')
    real_src = doc.get('label_source')
    real_trg = doc.get('label_target')
    
    return {
        "message": f"AI LOGIC TEST: Database expects Swap {real_src} <-> {real_trg}",
        "image": full_b64,
        "tiles": tiles,
        "solution": [real_src, real_trg]
    }

@app.get("/batch_check")
async def batch_check():
    # Validate how many images can be successfully sliced with current config
    success = 0
    failed = 0
    limit = 50
    
    cursor = col_captchas.find({}).limit(limit)
    cfg = current_settings
    
    async for doc in cursor:
        try:
            nparr = np.frombuffer(doc['image'], np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            h, w, _ = img.shape
            
            # Try Crop
            if cfg['top'] + cfg['bottom'] >= h or cfg['left'] + cfg['right'] >= w:
                failed += 1
                continue
                
            crop = img[cfg['top'] : h-cfg['bottom'], cfg['left'] : w-cfg['right']]
            if crop.size == 0:
                failed += 1
            else:
                success += 1
        except:
            failed += 1
            
    return {"total": limit, "success": success, "failed": failed}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)