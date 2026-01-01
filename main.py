import base64
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel

# --- 1. CONFIGURATION (MATCHING YOUR MAIN.PY) ---
MONGO_URI = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"
DB_NAME = "huawei_captcha"      # As per your script
COLLECTION_NAME = "captchas"    # As per your script

app = FastAPI()

# Database Connection
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

class LabelRequest(BaseModel):
    id: str
    source_idx: int
    target_idx: int

# --- 2. DASHBOARD UI ---
@app.get("/", response_class=HTMLResponse)
async def labeler_ui():
    return """
    <html>
    <head>
        <title>Huawei AI Trainer</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #0a0a0a; color: #fff; font-family: 'Segoe UI', sans-serif; text-align: center; padding: 10px; }
            .container { max-width: 600px; margin: 0 auto; background: #141414; padding: 20px; border-radius: 12px; border: 1px solid #333; }
            h2 { color: #00e676; margin-top: 0; }
            
            /* STATS */
            .stats-bar { display: flex; justify-content: space-between; background: #222; padding: 10px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; }
            .stat-val { color: #00e676; font-weight: bold; font-size: 16px; }

            /* IMAGE CONTAINER */
            .img-wrapper { 
                position: relative; 
                width: 340px; 
                height: 170px; 
                margin: 0 auto; 
                border: 2px solid #444;
                background: #000;
            }
            #captcha-img { width: 100%; height: 100%; display: block; object-fit: contain; }
            
            /* GRID OVERLAY */
            .grid-overlay { 
                position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(2, 1fr);
            }
            .grid-cell { 
                border: 1px solid rgba(255,255,255,0.15); 
                display: flex; align-items: center; justify-content: center;
                font-size: 24px; font-weight: bold; color: rgba(255, 255, 255, 0.4);
                cursor: pointer; user-select: none;
            }
            .grid-cell:hover { background: rgba(255,255,255,0.1); }
            
            /* SELECTION STYLES */
            .src-cell { background: rgba(255, 61, 0, 0.5) !important; border: 2px solid red; color: white; }
            .trg-cell { background: rgba(0, 230, 118, 0.5) !important; border: 2px solid #00e676; color: white; }

            /* CONTROLS */
            .control-panel { display: flex; justify-content: space-between; margin-top: 20px; align-items: center; background: #222; padding: 10px; border-radius: 8px; }
            .sel-box { font-size: 14px; color: #aaa; }
            .sel-val { font-size: 20px; font-weight: bold; display: block; margin-top: 5px; }
            
            .btn { flex-grow: 1; padding: 15px; border: none; border-radius: 6px; font-weight: bold; font-size: 16px; cursor: pointer; margin-left: 10px; transition: 0.2s; }
            .btn-save { background: #6200ea; color: white; opacity: 0.5; pointer-events: none; }
            .btn-active { opacity: 1; pointer-events: auto; box-shadow: 0 0 10px #6200ea; }
            .btn-del { background: #d32f2f; color: white; width: 100%; margin-top: 15px; padding: 10px; }

        </style>
    </head>
    <body>
        <div class="container">
            <h2>🧠 AI DATA TRAINER</h2>
            
            <div class="stats-bar">
                <span>Total Images: <span id="s-total" class="stat-val">...</span></span>
                <span>Remaining: <span id="s-remain" class="stat-val" style="color:yellow">...</span></span>
                <span>Done: <span id="s-done" class="stat-val">...</span></span>
            </div>

            <div class="img-wrapper">
                <img id="captcha-img" src="" alt="Loading Database Image...">
                <div class="grid-overlay" id="grid"></div>
            </div>

            <div class="control-panel">
                <div class="sel-box">Move From<span id="disp-src" class="sel-val" style="color:#ff3d00">?</span></div>
                <div style="font-size:24px; color:#555">➡️</div>
                <div class="sel-box">Move To<span id="disp-trg" class="sel-val" style="color:#00e676">?</span></div>
                <button id="btn-save" class="btn btn-save" onclick="saveLabel()">✅ SAVE (Enter)</button>
            </div>

            <button class="btn btn-del" onclick="deleteImage()">🗑️ DELETE (Bad Image)</button>
            <p style="font-size:12px; color:#666; margin-top:10px;">Shortcut: Click Source -> Click Target -> Press Enter</p>
        </div>

        <script>
            let currentId = null;
            let src = null;
            let trg = null;

            // 1. Generate Grid
            const grid = document.getElementById('grid');
            for(let i=0; i<8; i++) {
                let cell = document.createElement('div');
                cell.className = 'grid-cell';
                cell.innerText = i;
                cell.id = 'cell-' + i;
                cell.onclick = () => handleCellClick(i);
                grid.appendChild(cell);
            }

            // 2. Logic
            function handleCellClick(idx) {
                // Clear styles
                document.querySelectorAll('.grid-cell').forEach(c => {
                    c.classList.remove('src-cell');
                    c.classList.remove('trg-cell');
                });

                if (src === null) {
                    src = idx;
                } else if (src === idx) {
                    src = null; // Unselect
                } else {
                    trg = idx;
                }

                // Apply Styles & Update UI
                if(src !== null) document.getElementById('cell-'+src).classList.add('src-cell');
                if(trg !== null) document.getElementById('cell-'+trg).classList.add('trg-cell');
                
                document.getElementById('disp-src').innerText = src !== null ? src : "?";
                document.getElementById('disp-trg').innerText = trg !== null ? trg : "?";

                // Enable Save
                const btn = document.getElementById('btn-save');
                if(src !== null && trg !== null) {
                    btn.classList.add('btn-active');
                    btn.innerText = "✅ SAVE NOW";
                } else {
                    btn.classList.remove('btn-active');
                    btn.innerText = "Select 2 Tiles...";
                }
            }

            // 3. Load from DB
            function loadNext() {
                src = null; trg = null; handleCellClick(-1); // Reset
                document.getElementById('captcha-img').style.opacity = 0.5;

                fetch('/get_task').then(r => r.json()).then(d => {
                    if (d.status === "done") {
                        alert("🎉 Awesome! No more unlabeled images.");
                        document.body.innerHTML = "<h1>🏁 All Done! Great Job.</h1>";
                        return;
                    }
                    
                    currentId = d.id;
                    // DIRECT BINARY RENDER
                    document.getElementById('captcha-img').src = "data:image/jpeg;base64," + d.image_data;
                    document.getElementById('captcha-img').style.opacity = 1;
                    
                    // Stats
                    document.getElementById('s-total').innerText = d.stats.total;
                    document.getElementById('s-done').innerText = d.stats.labeled;
                    document.getElementById('s-remain').innerText = d.stats.total - d.stats.labeled;
                });
            }

            // 4. Save
            function saveLabel() {
                if(!currentId || src === null || trg === null) return;
                
                fetch('/save_label', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id: currentId, source_idx: src, target_idx: trg })
                }).then(() => loadNext());
            }

            // 5. Delete
            function deleteImage() {
                if(!currentId) return;
                if(confirm("Delete this image permanently from DB?")) {
                    fetch('/delete_image', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ id: currentId, source_idx:0, target_idx:0 })
                    }).then(() => loadNext());
                }
            }

            document.addEventListener('keydown', (e) => {
                if(e.key === "Enter") saveLabel();
            });

            // Start
            loadNext();
        </script>
    </body>
    </html>
    """

# --- 3. API ENDPOINTS ---

@app.get("/get_task")
async def get_task():
    # Find image where 'label_source' does NOT exist
    doc = await collection.find_one({"label_source": {"$exists": False}})
    
    total = await collection.count_documents({})
    labeled = await collection.count_documents({"label_source": {"$exists": True}})
    
    if not doc:
        return {"status": "done"}
    
    try:
        # Extract Binary Data directly from 'image' field
        binary_data = doc['image']
        # Convert to Base64 for Browser
        b64_string = base64.b64encode(binary_data).decode('utf-8')
        
        return {
            "status": "ok",
            "id": str(doc["_id"]),
            "image_data": b64_string,
            "stats": {"total": total, "labeled": labeled}
        }
    except Exception as e:
        print(f"❌ Corrupt Image ID {doc['_id']}: {e}")
        # Auto-delete corrupt data to unblock queue
        await collection.delete_one({"_id": doc["_id"]})
        return await get_task()

@app.post("/save_label")
async def save_label(req: LabelRequest):
    await collection.update_one(
        {"_id": ObjectId(req.id)},
        {"$set": {
            "label_source": req.source_idx,
            "label_target": req.target_idx,
            "status": "labeled",
            "labeled_at": "now" # Just a timestamp placeholder
        }}
    )
    return {"status": "saved"}

@app.post("/delete_image")
async def delete_image(req: LabelRequest):
    await collection.delete_one({"_id": ObjectId(req.id)})
    return {"status": "deleted"}