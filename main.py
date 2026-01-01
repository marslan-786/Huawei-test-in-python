import base64
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel

# --- 1. CONFIGURATION (MUST MATCH MAIN.PY) ---
MONGO_URI = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"

# 🔥 FIX: Database Name updated to match your Main.py
DB_NAME = "huawei_captcha"      
COLLECTION_NAME = "captchas"    

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
            
            /* IMAGE WRAPPER */
            .img-wrapper { 
                position: relative; 
                width: 340px; 
                height: 170px; 
                margin: 20px auto; 
                border: 2px solid #444;
                background: #000;
            }
            /* FULL IMAGE DISPLAY */
            #captcha-img { width: 100%; height: 100%; display: block; object-fit: contain; }
            
            /* VISUAL GRID (CSS Only - No Image Cutting) */
            .grid-overlay { 
                position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(2, 1fr);
            }
            .grid-cell { 
                border: 1px solid rgba(255,255,255,0.2); 
                display: flex; align-items: center; justify-content: center;
                font-size: 24px; font-weight: bold; color: rgba(255, 255, 255, 0.5);
                cursor: pointer; user-select: none; text-shadow: 1px 1px 2px black;
            }
            .grid-cell:hover { background: rgba(255,255,255,0.1); }
            
            /* SELECTION COLORS */
            .src-cell { background: rgba(255, 61, 0, 0.5) !important; border: 2px solid red; color: white; }
            .trg-cell { background: rgba(0, 230, 118, 0.5) !important; border: 2px solid #00e676; color: white; }

            .btn { width: 100%; padding: 15px; border: none; border-radius: 6px; font-weight: bold; font-size: 16px; cursor: pointer; margin-top: 15px; }
            .btn-save { background: #6200ea; color: white; opacity: 0.5; pointer-events: none; }
            .btn-active { opacity: 1; pointer-events: auto; }
            .btn-del { background: #d32f2f; color: white; margin-top: 10px; }
            
            .info { margin-top: 10px; color: #aaa; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🧠 AI DATA TRAINER</h2>
            
            <div class="info">
                Images Left: <span id="s-remain" style="color:yellow; font-weight:bold">...</span> | 
                Done: <span id="s-done" style="color:#00e676">...</span>
            </div>

            <div class="img-wrapper">
                <img id="captcha-img" src="" alt="Loading...">
                <div class="grid-overlay" id="grid"></div>
            </div>

            <div class="info" style="font-size: 16px;">
                Move Tile <span id="disp-src" style="color:red; font-weight:bold">?</span> 
                ➡️ To <span id="disp-trg" style="color:#00e676; font-weight:bold">?</span>
            </div>

            <button id="btn-save" class="btn btn-save" onclick="saveLabel()">✅ SAVE (Enter)</button>
            <button class="btn btn-del" onclick="deleteImage()">🗑️ DELETE IMAGE</button>
        </div>

        <script>
            let currentId = null;
            let src = null;
            let trg = null;

            // Generate Visual Grid
            const grid = document.getElementById('grid');
            for(let i=0; i<8; i++) {
                let cell = document.createElement('div');
                cell.className = 'grid-cell';
                cell.innerText = i;
                cell.id = 'cell-' + i;
                cell.onclick = () => handleCellClick(i);
                grid.appendChild(cell);
            }

            function handleCellClick(idx) {
                document.querySelectorAll('.grid-cell').forEach(c => {
                    c.classList.remove('src-cell'); c.classList.remove('trg-cell');
                });

                if (src === null) src = idx;
                else if (src === idx) src = null;
                else trg = idx;

                if(src !== null) document.getElementById('cell-'+src).classList.add('src-cell');
                if(trg !== null) document.getElementById('cell-'+trg).classList.add('trg-cell');
                
                document.getElementById('disp-src').innerText = src !== null ? src : "?";
                document.getElementById('disp-trg').innerText = trg !== null ? trg : "?";

                const btn = document.getElementById('btn-save');
                if(src !== null && trg !== null) {
                    btn.classList.add('btn-active');
                    btn.innerText = "✅ SAVE NOW";
                } else {
                    btn.classList.remove('btn-active');
                    btn.innerText = "Select Source & Target";
                }
            }

            function loadNext() {
                src = null; trg = null; handleCellClick(-1);
                document.getElementById('captcha-img').style.opacity = 0.5;

                fetch('/get_task').then(r => r.json()).then(d => {
                    if (d.status === "done") {
                        alert("🎉 All images labeled!");
                        return;
                    }
                    if (d.status === "error") {
                        alert("Error: " + d.message);
                        return;
                    }
                    
                    currentId = d.id;
                    // Load Full Image
                    document.getElementById('captcha-img').src = "data:image/jpeg;base64," + d.image_data;
                    document.getElementById('captcha-img').style.opacity = 1;
                    
                    document.getElementById('s-done').innerText = d.stats.labeled;
                    document.getElementById('s-remain').innerText = d.stats.total - d.stats.labeled;
                });
            }

            function saveLabel() {
                if(!currentId || src === null || trg === null) return;
                
                fetch('/save_label', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id: currentId, source_idx: src, target_idx: trg })
                }).then(() => loadNext());
            }

            function deleteImage() {
                if(!currentId) return;
                if(confirm("Delete this image?")) {
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

            loadNext();
        </script>
    </body>
    </html>
    """

# --- 3. API ENDPOINTS ---

@app.get("/get_task")
async def get_task():
    print("🔄 Fetching next image from DB...")
    
    # Check DB Connection
    try:
        count = await collection.count_documents({})
        print(f"📊 Total Docs in DB: {count}")
    except Exception as e:
        print(f"❌ DB Connection Error: {e}")
        return {"status": "error", "message": str(e)}

    # Find unlabeled image
    doc = await collection.find_one({
        "$and": [
            {"label_source": {"$exists": False}}, 
            {"image": {"$exists": True}}
        ]
    })
    
    labeled = await collection.count_documents({"label_source": {"$exists": True}})
    
    if not doc:
        print("✅ No more images found!")
        return {"status": "done"}
    
    try:
        print(f"📸 Image Found ID: {doc['_id']}")
        
        # Binary Extraction
        binary_data = doc['image']
        print(f"📏 Image Size: {len(binary_data)} bytes")
        
        # Base64 Conversion
        b64_string = base64.b64encode(binary_data).decode('utf-8')
        
        return {
            "status": "ok",
            "id": str(doc["_id"]),
            "image_data": b64_string,
            "stats": {"total": count, "labeled": labeled}
        }
    except Exception as e:
        print(f"❌ Corrupt Image: {e}")
        # Delete corrupt image to avoid loop
        await collection.delete_one({"_id": doc["_id"]})
        return await get_task()

@app.post("/save_label")
async def save_label(req: LabelRequest):
    print(f"💾 Saving Label: {req.source_idx} -> {req.target_idx}")
    await collection.update_one(
        {"_id": ObjectId(req.id)},
        {"$set": {
            "label_source": req.source_idx,
            "label_target": req.target_idx,
            "status": "labeled",
            "labeled_at": "now"
        }}
    )
    return {"status": "saved"}

@app.post("/delete_image")
async def delete_image(req: LabelRequest):
    print(f"🗑️ Deleting Image ID: {req.id}")
    await collection.delete_one({"_id": ObjectId(req.id)})
    return {"status": "deleted"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)