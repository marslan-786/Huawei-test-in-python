import base64
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel
from datetime import datetime

# --- CONFIGURATION ---
MONGO_URI = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"
DB_NAME = "huawei_captcha"
COLLECTION_NAME = "captchas"

app = FastAPI()

# Database Connection
client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

class LabelRequest(BaseModel):
    id: str
    source_idx: int
    target_idx: int

# Test DB Connection on Startup
@app.on_event("startup")
async def startup_db():
    try:
        await client.server_info()
        count = await collection.count_documents({})
        print(f"✅ MongoDB Connected! Total Documents: {count}")
    except Exception as e:
        print(f"❌ MongoDB Connection Failed: {e}")

# --- DASHBOARD UI ---
@app.get("/", response_class=HTMLResponse)
async def labeler_ui():
    return """
    <html>
    <head>
        <title>Huawei AI Trainer</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #0a0a0a; color: #fff; font-family: 'Segoe UI', sans-serif; text-align: center; padding: 10px; margin: 0; }
            .container { max-width: 600px; margin: 0 auto; background: #141414; padding: 20px; border-radius: 12px; border: 1px solid #333; }
            h2 { color: #00e676; margin-top: 0; }
            
            /* IMAGE WRAPPER */
            .img-wrapper { 
                position: relative; 
                width: 100%;
                max-width: 500px;
                height: 250px; 
                margin: 20px auto; 
                border: 2px solid #444;
                background: #000;
            }
            /* FULL IMAGE DISPLAY */
            #captcha-img { 
                width: 100%; 
                height: 100%; 
                display: block; 
                object-fit: contain; 
            }
            
            /* VISUAL GRID (CSS Only - No Image Cutting) */
            .grid-overlay { 
                position: absolute; 
                top: 0; 
                left: 0; 
                width: 100%; 
                height: 100%; 
                display: grid; 
                grid-template-columns: repeat(4, 1fr); 
                grid-template-rows: repeat(2, 1fr);
                pointer-events: none;
            }
            .grid-cell { 
                border: 1px solid rgba(255,255,255,0.3); 
                display: flex; 
                align-items: center; 
                justify-content: center;
                font-size: 28px; 
                font-weight: bold; 
                color: rgba(255, 255, 255, 0.6);
                cursor: pointer; 
                user-select: none; 
                text-shadow: 2px 2px 4px black;
                pointer-events: auto;
            }
            .grid-cell:hover { background: rgba(255,255,255,0.15); }
            
            /* SELECTION COLORS */
            .src-cell { 
                background: rgba(255, 61, 0, 0.6) !important; 
                border: 3px solid red !important; 
                color: white; 
            }
            .trg-cell { 
                background: rgba(0, 230, 118, 0.6) !important; 
                border: 3px solid #00e676 !important; 
                color: white; 
            }

            .btn { 
                width: 100%; 
                padding: 15px; 
                border: none; 
                border-radius: 6px; 
                font-weight: bold; 
                font-size: 16px; 
                cursor: pointer; 
                margin-top: 15px; 
            }
            .btn-save { 
                background: #6200ea; 
                color: white; 
                opacity: 0.5; 
                pointer-events: none; 
            }
            .btn-active { 
                opacity: 1; 
                pointer-events: auto; 
                animation: pulse 1s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.02); }
            }
            
            .btn-del { 
                background: #d32f2f; 
                color: white; 
                margin-top: 10px; 
            }
            
            .info { 
                margin-top: 10px; 
                color: #aaa; 
                font-size: 14px; 
            }
            
            .loading { 
                color: yellow; 
                font-size: 16px; 
                margin: 20px; 
            }
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

            <div class="info" style="font-size: 18px; margin: 20px 0;">
                Move Tile <span id="disp-src" style="color:red; font-weight:bold; font-size: 24px;">?</span> 
                ➡️ To <span id="disp-trg" style="color:#00e676; font-weight:bold; font-size: 24px;">?</span>
            </div>

            <button id="btn-save" class="btn btn-save" onclick="saveLabel()">✅ SAVE (Enter)</button>
            <button class="btn btn-del" onclick="deleteImage()">🗑️ DELETE IMAGE</button>
            
            <div class="loading" id="loading">Loading...</div>
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
                // Clear previous selections
                document.querySelectorAll('.grid-cell').forEach(c => {
                    c.classList.remove('src-cell'); 
                    c.classList.remove('trg-cell');
                });

                // Select logic
                if (idx === -1) {
                    // Reset
                    src = null;
                    trg = null;
                } else if (src === null) {
                    // First click - select source
                    src = idx;
                } else if (src === idx) {
                    // Click same cell - deselect
                    src = null;
                } else if (trg === null) {
                    // Second click - select target
                    trg = idx;
                } else {
                    // Third click - reset and start over
                    src = idx;
                    trg = null;
                }

                // Update visual feedback
                if(src !== null) document.getElementById('cell-'+src).classList.add('src-cell');
                if(trg !== null) document.getElementById('cell-'+trg).classList.add('trg-cell');
                
                document.getElementById('disp-src').innerText = src !== null ? src : "?";
                document.getElementById('disp-trg').innerText = trg !== null ? trg : "?";

                // Enable/Disable save button
                const btn = document.getElementById('btn-save');
                if(src !== null && trg !== null) {
                    btn.classList.add('btn-active');
                    btn.innerText = "✅ SAVE NOW (Enter)";
                } else {
                    btn.classList.remove('btn-active');
                    btn.innerText = "Select Source & Target";
                }
            }

            function loadNext() {
                // Reset state
                src = null; 
                trg = null; 
                handleCellClick(-1);
                
                document.getElementById('captcha-img').style.opacity = 0.3;
                document.getElementById('loading').style.display = 'block';

                fetch('/get_task')
                    .then(r => r.json())
                    .then(d => {
                        document.getElementById('loading').style.display = 'none';
                        
                        if (d.status === "done") {
                            alert("🎉 All images labeled!");
                            document.getElementById('captcha-img').src = "";
                            return;
                        }
                        
                        if (d.status === "error") {
                            alert("❌ Error: " + d.message);
                            console.error("Error details:", d);
                            return;
                        }
                        
                        currentId = d.id;
                        
                        // Load Full Image
                        const img = document.getElementById('captcha-img');
                        img.onload = () => {
                            img.style.opacity = 1;
                        };
                        img.onerror = () => {
                            alert("Failed to load image!");
                            loadNext();
                        };
                        img.src = "data:image/jpeg;base64," + d.image_data;
                        
                        document.getElementById('s-done').innerText = d.stats.labeled;
                        document.getElementById('s-remain').innerText = d.stats.total - d.stats.labeled;
                    })
                    .catch(err => {
                        document.getElementById('loading').style.display = 'none';
                        console.error("Fetch error:", err);
                        alert("Network error: " + err);
                    });
            }

            function saveLabel() {
                if(!currentId || src === null || trg === null) {
                    alert("Please select both source and target!");
                    return;
                }
                
                document.getElementById('loading').style.display = 'block';
                
                fetch('/save_label', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        id: currentId, 
                        source_idx: src, 
                        target_idx: trg 
                    })
                })
                .then(r => r.json())
                .then(() => {
                    loadNext();
                })
                .catch(err => {
                    document.getElementById('loading').style.display = 'none';
                    alert("Save failed: " + err);
                });
            }

            function deleteImage() {
                if(!currentId) return;
                
                if(confirm("Delete this image? This cannot be undone!")) {
                    document.getElementById('loading').style.display = 'block';
                    
                    fetch('/delete_image', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ 
                            id: currentId, 
                            source_idx: 0, 
                            target_idx: 0 
                        })
                    })
                    .then(() => {
                        loadNext();
                    })
                    .catch(err => {
                        document.getElementById('loading').style.display = 'none';
                        alert("Delete failed: " + err);
                    });
                }
            }

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                if(e.key === "Enter") {
                    saveLabel();
                } else if(e.key >= "0" && e.key <= "7") {
                    handleCellClick(parseInt(e.key));
                } else if(e.key === "Delete" || e.key === "Backspace") {
                    if(e.ctrlKey) deleteImage();
                }
            });

            // Auto-load on page load
            loadNext();
        </script>
    </body>
    </html>
    """

# --- API ENDPOINTS ---

@app.get("/get_task")
async def get_task():
    print("\n🔄 Fetching next image from DB...")
    
    try:
        # Check DB Connection
        count = await collection.count_documents({})
        print(f"📊 Total Documents in DB: {count}")
        
        if count == 0:
            print("❌ No documents found in database!")
            return {"status": "error", "message": "Database is empty"}
        
        # Find unlabeled image
        doc = await collection.find_one({
            "$and": [
                {"label_source": {"$exists": False}}, 
                {"image": {"$exists": True}}
            ]
        })
        
        # Count labeled images
        labeled = await collection.count_documents({"label_source": {"$exists": True}})
        print(f"✅ Labeled: {labeled}, Unlabeled: {count - labeled}")
        
        if not doc:
            print("✅ No more unlabeled images!")
            return {"status": "done"}
        
        print(f"📸 Image Found - ID: {doc['_id']}")
        
        # Extract image binary data
        if 'image' not in doc:
            print("❌ No image field in document!")
            return {"status": "error", "message": "Document has no image"}
        
        binary_data = doc['image']
        
        # Check if it's bytes or Binary object
        if hasattr(binary_data, '__bytes__'):
            binary_data = bytes(binary_data)
        
        print(f"📏 Image Size: {len(binary_data)} bytes")
        
        if len(binary_data) < 100:
            print("❌ Image too small, possibly corrupt")
            await collection.delete_one({"_id": doc["_id"]})
            return await get_task()
        
        # Convert to base64
        b64_string = base64.b64encode(binary_data).decode('utf-8')
        print(f"✅ Base64 string length: {len(b64_string)}")
        
        return {
            "status": "ok",
            "id": str(doc["_id"]),
            "image_data": b64_string,
            "stats": {
                "total": count, 
                "labeled": labeled
            }
        }
        
    except Exception as e:
        print(f"❌ Error in get_task: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.post("/save_label")
async def save_label(req: LabelRequest):
    try:
        print(f"\n💾 Saving Label: Tile {req.source_idx} ➡️ Tile {req.target_idx}")
        
        result = await collection.update_one(
            {"_id": ObjectId(req.id)},
            {"$set": {
                "label_source": req.source_idx,
                "label_target": req.target_idx,
                "status": "labeled",
                "labeled_at": datetime.now()
            }}
        )
        
        if result.modified_count > 0:
            print("✅ Label saved successfully")
            return {"status": "saved"}
        else:
            print("⚠️ Document not found or not modified")
            return {"status": "error", "message": "Failed to update"}
            
    except Exception as e:
        print(f"❌ Error saving label: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/delete_image")
async def delete_image(req: LabelRequest):
    try:
        print(f"\n🗑️ Deleting Image ID: {req.id}")
        
        result = await collection.delete_one({"_id": ObjectId(req.id)})
        
        if result.deleted_count > 0:
            print("✅ Image deleted successfully")
            return {"status": "deleted"}
        else:
            print("⚠️ Image not found")
            return {"status": "error", "message": "Image not found"}
            
    except Exception as e:
        print(f"❌ Error deleting image: {e}")
        return {"status": "error", "message": str(e)}

# Health check endpoint
@app.get("/health")
async def health():
    try:
        count = await collection.count_documents({})
        return {
            "status": "healthy",
            "db_connected": True,
            "total_images": count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "db_connected": False,
            "error": str(e)
        }

if __name__ == "__main__":
    print("🚀 Starting Labeler on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)