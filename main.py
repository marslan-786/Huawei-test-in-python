import os
import base64
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel

# --- CONFIGURATION ---
MONGO_URL = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"
DB_NAME = "huawei_bot"
COLLECTION_NAME = "captcha_dataset"

app = FastAPI()

# Database Connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

class LabelRequest(BaseModel):
    id: str
    source_idx: int
    target_idx: int

# --- DASHBOARD UI ---
@app.get("/", response_class=HTMLResponse)
async def labeler_ui():
    return """
    <html>
    <head>
        <title>AI Data Labeler</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #121212; color: #e0e0e0; font-family: sans-serif; text-align: center; padding: 20px; }
            h2 { color: #00e676; margin-bottom: 5px; }
            
            .container { max-width: 500px; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; }
            
            /* IMAGE CONTAINER WITH GRID OVERLAY */
            .img-wrapper { position: relative; width: 340px; height: 170px; margin: 20px auto; background: #000; border: 2px solid #00e676; }
            #captcha-img { width: 100%; height: 100%; display: block; }
            
            .grid-overlay { 
                position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(2, 1fr);
            }
            .grid-cell { 
                border: 1px solid rgba(255,255,255,0.3); 
                display: flex; align-items: center; justify-content: center;
                font-size: 24px; font-weight: bold; color: rgba(255, 255, 255, 0.8);
                text-shadow: 2px 2px 2px #000; cursor: pointer;
            }
            .grid-cell:hover { background: rgba(0, 230, 118, 0.2); }
            
            /* CONTROLS */
            .controls { display: flex; justify-content: space-between; gap: 10px; margin-top: 20px; }
            select { width: 100%; padding: 15px; background: #333; color: white; border: 1px solid #555; border-radius: 5px; font-size: 18px; }
            
            .btn { width: 100%; padding: 15px; font-size: 18px; font-weight: bold; border: none; border-radius: 5px; cursor: pointer; margin-top: 20px; }
            .btn-save { background: #6200ea; color: white; }
            .btn-skip { background: #d50000; color: white; margin-top: 10px; }
            
            .stats { display: flex; justify-content: space-around; margin-top: 20px; font-size: 14px; color: #888; }
            .highlight { color: #fff; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🧠 AI TRAINER TOOL</h2>
            <p>Select the two tiles that need to be swapped.</p>
            
            <div class="stats">
                <span>Remaining: <span id="s-remain" class="highlight">0</span></span>
                <span>Labeled: <span id="s-done" class="highlight">0</span></span>
            </div>

            <div class="img-wrapper">
                <img id="captcha-img" src="" alt="Loading...">
                <div class="grid-overlay" id="grid">
                    </div>
            </div>

            <div class="controls">
                <div style="width: 48%;">
                    <label>Move From (Source)</label>
                    <select id="sel-source">
                        <option value="0">0</option><option value="1">1</option><option value="2">2</option><option value="3">3</option>
                        <option value="4">4</option><option value="5">5</option><option value="6">6</option><option value="7">7</option>
                    </select>
                </div>
                <div style="width: 48%;">
                    <label>Move To (Target)</label>
                    <select id="sel-target">
                        <option value="0">0</option><option value="1">1</option><option value="2">2</option><option value="3">3</option>
                        <option value="4">4</option><option value="5">5</option><option value="6">6</option><option value="7" selected>7</option>
                    </select>
                </div>
            </div>

            <button class="btn btn-save" onclick="saveLabel()">✅ SAVE & NEXT (Enter)</button>
            <button class="btn btn-skip" onclick="skipImage()">🗑️ DELETE / SKIP</button>
        </div>

        <script>
            let currentId = null;

            // Generate Grid Numbers
            const grid = document.getElementById('grid');
            for(let i=0; i<8; i++) {
                let div = document.createElement('div');
                div.className = 'grid-cell';
                div.innerText = i;
                div.onclick = () => autoSelect(i);
                grid.appendChild(div);
            }

            // Auto-fill dropdowns by clicking on image
            let clickCount = 0;
            function autoSelect(idx) {
                if(clickCount === 0) {
                    document.getElementById('sel-source').value = idx;
                    clickCount = 1;
                } else {
                    document.getElementById('sel-target').value = idx;
                    clickCount = 0;
                }
            }

            function loadNext() {
                fetch('/get_task').then(r => r.json()).then(d => {
                    if (d.status === "done") {
                        alert("🎉 All images labeled! Great job.");
                        document.getElementById('captcha-img').style.display = 'none';
                        return;
                    }
                    currentId = d.id;
                    document.getElementById('captcha-img').src = "data:image/jpeg;base64," + d.image;
                    document.getElementById('s-remain').innerText = d.stats.remaining;
                    document.getElementById('s-done').innerText = d.stats.labeled;
                    
                    // Reset selection
                    clickCount = 0;
                });
            }

            function saveLabel() {
                if(!currentId) return;
                
                const s = document.getElementById('sel-source').value;
                const t = document.getElementById('sel-target').value;

                fetch('/save_label', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id: currentId, source_idx: parseInt(s), target_idx: parseInt(t) })
                }).then(() => loadNext());
            }

            function skipImage() {
                if(!currentId) return;
                if(confirm("Delete this image from dataset?")) {
                    fetch('/delete_image', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ id: currentId, source_idx:0, target_idx:0 }) # dummies
                    }).then(() => loadNext());
                }
            }

            // Keyboard Shortcut (Enter to Save)
            document.addEventListener('keydown', function(event) {
                if (event.key === "Enter") saveLabel();
            });

            // Init
            loadNext();
        </script>
    </body>
    </html>
    """

# --- API ENDPOINTS ---

@app.get("/get_task")
async def get_task():
    # Find one image that is NOT labeled yet
    # We look for documents where 'label_source' does NOT exist
    doc = await collection.find_one({"label_source": {"$exists": False}})
    
    # Stats
    total = await collection.count_documents({})
    labeled = await collection.count_documents({"label_source": {"$exists": True}})
    
    if not doc:
        return {"status": "done", "stats": {"total": total, "remaining": 0, "labeled": labeled}}
    
    # Read Image File from Disk (Filename is stored in DB)
    # Note: Assuming images are in ./dataset_training/ folder relative to this script
    # If using direct Mongo GridFS, logic changes. Here we use file path from your previous script.
    
    # Fallback: Check if we stored binary in DB (future proofing) or just filename
    # Previous script stored 'filename'.
    
    image_path = f"./dataset_training/{doc['filename']}"
    
    # If file doesn't exist locally but is in DB, we might have an issue unless we use DB binary.
    # For now, let's assume files are present.
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
    else:
        # If image missing, delete record and get next
        await collection.delete_one({"_id": doc["_id"]})
        return await get_task()

    return {
        "status": "ok",
        "id": str(doc["_id"]),
        "image": encoded,
        "stats": {
            "total": total,
            "remaining": total - labeled,
            "labeled": labeled
        }
    }

@app.post("/save_label")
async def save_label(req: LabelRequest):
    await collection.update_one(
        {"_id": ObjectId(req.id)},
        {"$set": {
            "label_source": req.source_idx,
            "label_target": req.target_idx,
            "status": "labeled"
        }}
    )
    return {"status": "saved"}

@app.post("/delete_image")
async def delete_image(req: LabelRequest):
    # Fetch filename to delete from disk too
    doc = await collection.find_one({"_id": ObjectId(req.id)})
    if doc:
        try:
            os.remove(f"./dataset_training/{doc['filename']}")
        except: pass
        await collection.delete_one({"_id": ObjectId(req.id)})
    return {"status": "deleted"}