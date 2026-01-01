import uvicorn
import base64
import cv2
import numpy as np
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

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
col_captchas = db[COL_CAPTCHAS]
col_settings = db[COL_SETTINGS]

# --- UI WITH CROPPER.JS ---
@app.get("/", response_class=HTMLResponse)
async def ui():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Visual Calibrator</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.js"></script>
        
        <style>
            body { background: #121212; color: #fff; margin: 0; padding: 10px; font-family: sans-serif; text-align: center; }
            .container { max-width: 100%; }
            
            /* IMAGE AREA */
            .img-container { 
                height: 70vh; /* Takes 70% of mobile screen */
                background: #000;
                margin-bottom: 10px;
                border: 2px solid #333;
            }
            img { max-width: 100%; }

            /* BUTTONS */
            .btn-row { display: flex; gap: 10px; justify-content: center; }
            button { flex: 1; padding: 15px; border: none; border-radius: 5px; font-weight: bold; font-size: 16px; color: white; cursor: pointer; }
            .btn-load { background: #2979ff; }
            .btn-save { background: #00c853; }
            .btn-test { background: #ff9100; margin-top: 10px; width: 100%; }

            /* CUSTOM GRID OVERLAY FOR CROPPER */
            /* This draws the 2x4 lines inside the selection box */
            .cropper-view-box {
                outline: 2px solid #00e676;
            }
            .cropper-view-box::before {
                content: ''; position: absolute; top: 0; left: 25%; width: 25%; height: 100%;
                border-left: 1px solid rgba(255, 255, 0, 0.8);
                border-right: 1px solid rgba(255, 255, 0, 0.8);
                pointer-events: none;
            }
            .cropper-view-box::after {
                content: ''; position: absolute; top: 50%; left: 0; width: 100%; height: 50%;
                border-top: 1px solid rgba(255, 255, 0, 0.8);
                border-right: 1px solid rgba(255, 255, 0, 0.8); /* 3rd vert line hack */
                width: 75%; /* Stop right border at 75% to act as 3rd line */
                pointer-events: none;
            }
            /* Extra line helper */
            .grid-helper {
                position: absolute; top: 0; right: 25%; width: 1px; height: 100%; background: rgba(255,255,0,0.8); z-index: 999; pointer-events:none;
            }

            .info { color: #aaa; font-size: 12px; margin-bottom: 5px; }
            
            /* RESULT PREVIEW */
            .tiles-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px; margin-top: 10px; display: none; }
            .tile { width: 100%; border: 1px solid #444; }
        </style>
    </head>
    <body>
        <div class="container">
            <h3 style="margin:0 0 10px 0; color:#00e676;">📐 VISUAL CALIBRATOR</h3>
            <div class="info">Drag the box to fit the Captcha ONLY.</div>

            <div class="img-container">
                <img id="image" src="">
            </div>

            <div class="btn-row">
                <button class="btn-load" onclick="loadImage()">🔄 Load Image</button>
                <button class="btn-save" onclick="saveCrop()">💾 Save Settings</button>
            </div>
            <button class="btn-test" onclick="testSlice()">✂️ Test Slice & Verify</button>

            <div id="result-area">
                <h4 style="margin:10px 0 5px 0; display:none;" id="res-title">SLICED RESULT:</h4>
                <div class="tiles-grid" id="tiles-box"></div>
            </div>
        </div>

        <script>
            let cropper;
            let currentImgId = null;

            // 1. Load Image
            function loadImage() {
                fetch('/get_random').then(r=>r.json()).then(d=>{
                    if(d.status === 'error') { alert(d.message); return; }
                    currentImgId = d.id;
                    
                    const img = document.getElementById('image');
                    img.src = "data:image/jpeg;base64," + d.image;
                    
                    // Destroy old cropper if exists
                    if(cropper) cropper.destroy();

                    // Initialize Cropper
                    setTimeout(() => {
                        cropper = new Cropper(img, {
                            viewMode: 1,
                            dragMode: 'move',
                            autoCropArea: 0.5,
                            restore: false,
                            guides: false,
                            center: false,
                            highlight: false,
                            cropBoxMovable: true,
                            cropBoxResizable: true,
                            toggleDragModeOnDblclick: false,
                        });
                    }, 100);
                });
            }

            // 2. Save Config
            function saveCrop() {
                if(!cropper) return;
                
                // Get Crop Data (x, y, width, height) relative to original image size
                const data = cropper.getData(true); // true = raw image dimensions
                const imgData = cropper.getImageData();
                
                // Calculate Cuts for Backend
                // Backend expects: Top, Bottom, Left, Right cuts to remove
                const originalH = imgData.naturalHeight;
                const originalW = imgData.naturalWidth;

                const config = {
                    top: Math.round(data.y),
                    left: Math.round(data.x),
                    right: Math.round(originalW - (data.x + data.width)),
                    bottom: Math.round(originalH - (data.y + data.height))
                };

                // Safety: No negative values
                if(config.top < 0) config.top = 0;
                if(config.left < 0) config.left = 0;
                if(config.right < 0) config.right = 0;
                if(config.bottom < 0) config.bottom = 0;

                fetch('/save_config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(config)
                }).then(r=>r.json()).then(d=>{
                    alert(`✅ Settings Saved!\nTop: ${config.top}, Bottom: ${config.bottom}\nLeft: ${config.left}, Right: ${config.right}`);
                });
            }

            // 3. Test Slice
            function testSlice() {
                if(!currentImgId) return;
                
                fetch('/test_slice?id=' + currentImgId).then(r=>r.json()).then(d=>{
                    const box = document.getElementById('tiles-box');
                    document.getElementById('res-title').style.display = 'block';
                    box.style.display = 'grid';
                    box.innerHTML = "";
                    
                    d.tiles.forEach(t => {
                        box.innerHTML += `<img class="tile" src="data:image/jpeg;base64,${t}">`;
                    });
                });
            }
            
            // Auto Load on Start
            window.onload = loadImage;
        </script>
    </body>
    </html>
    """

# --- API ---
class SaveParams(BaseModel):
    top: int
    bottom: int
    left: int
    right: int

@app.get("/get_random")
async def get_random():
    pipeline = [{"$match": {"image": {"$exists": True}}}, {"$sample": {"size": 1}}]
    try:
        cursor = col_captchas.aggregate(pipeline)
        doc = await cursor.to_list(length=1)
        if not doc: return {"status": "error", "message": "DB Empty"}
        b64 = base64.b64encode(bytes(doc[0]['image'])).decode('utf-8')
        return {"status": "ok", "id": str(doc[0]["_id"]), "image": b64}
    except: return {"status": "error", "message": "Failed to fetch"}

@app.post("/save_config")
async def save_config(p: SaveParams):
    # Save the calculation results
    await col_settings.update_one(
        {"_id": "slice_config"}, 
        {"$set": p.dict()}, 
        upsert=True
    )
    return {"status": "saved"}

@app.get("/test_slice")
async def test_slice(id: str):
    # 1. Get Settings
    conf_doc = await col_settings.find_one({"_id": "slice_config"})
    if not conf_doc: return {"tiles": []}
    
    # 2. Get Image
    doc = await col_captchas.find_one({"_id": ObjectId(id)})
    nparr = np.frombuffer(doc['image'], np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 3. Crop based on Saved Settings
    h, w, _ = img.shape
    top, bot = conf_doc.get('top',0), conf_doc.get('bottom',0)
    left, right = conf_doc.get('left',0), conf_doc.get('right',0)
    
    # Validation
    if top + bot >= h or left + right >= w: return {"tiles": []}
    
    # Crop
    crop = img[top:h-bot, left:w-right]
    
    # 4. Slice 8 Tiles
    ch, cw, _ = crop.shape
    th, tw = ch // 2, cw // 4
    
    tiles = []
    for r in range(2):
        for c in range(4):
            tile = crop[r*th:(r+1)*th, c*tw:(c+1)*tw]
            _, buf = cv2.imencode('.jpg', tile)
            tiles.append(base64.b64encode(buf).decode('utf-8'))
            
    return {"tiles": tiles}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)