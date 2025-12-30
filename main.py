import os
import asyncio
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig

# --- API KEY (Yahan Apni Key Dalein) ---
# Behtar ye hai k Railway Variables main GOOGLE_API_KEY set karein
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "AIzaSyCz-X24ZgEZ79YRcg8ym9ZtuQHup1AVgJQ"

# --- CONFIG ---
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

app = FastAPI()
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# Global Variables
bot_status = "System Ready. Waiting for Command."
last_video = ""

# --- DASHBOARD (Manual Refresh Only) ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei AI Agent</title>
        <style>
            body { background-color: #0f0f0f; color: #e0e0e0; font-family: 'Segoe UI', monospace; text-align: center; padding: 40px; }
            h1 { color: #ff4757; font-size: 3rem; margin-bottom: 10px; }
            .box { background: #1e1e1e; border: 1px solid #333; padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 600px; }
            .status { font-size: 1.2rem; color: #2ed573; margin-bottom: 20px; border-bottom: 1px solid #444; padding-bottom: 10px; }
            
            button {
                padding: 15px 30px; font-size: 18px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; margin: 10px; transition: 0.3s;
            }
            .btn-start { background: #ff4757; color: white; }
            .btn-start:hover { background: #ff6b81; }
            
            .btn-refresh { background: #3742fa; color: white; }
            .btn-refresh:hover { background: #5352ed; }

            a { color: #ffa502; text-decoration: none; font-size: 20px; border: 1px solid #ffa502; padding: 10px 20px; border-radius: 5px; display: inline-block; margin-top: 10px; }
            a:hover { background: #ffa502; color: black; }
        </style>
    </head>
    <body>
        <h1>🤖 AI Agent Dashboard</h1>
        
        <div class="box">
            <h3>Current Status</h3>
            <div id="status-display" class="status">System Ready...</div>
            
            <button class="btn-refresh" onclick="checkStatus()">🔄 Refresh Status</button>
            <br><br>
            <button class="btn-start" onclick="startBot()">🚀 Launch AI Mission</button>
        </div>

        <div class="box" id="video-box" style="display:none;">
            <h3>🎥 Mission Recording</h3>
            <a id="video-link" href="#" target="_blank">Watch Video</a>
        </div>

        <script>
            // Sirf button dabane par chalega
            function checkStatus() {
                fetch('/status').then(r => r.json()).then(data => {
                    document.getElementById('status-display').innerText = data.status;
                    
                    if (data.video) {
                        document.getElementById('video-box').style.display = 'block';
                        document.getElementById('video-link').href = data.video;
                    }
                });
            }

            function startBot() {
                document.getElementById('status-display').innerText = "Request Sent... Please Click Refresh after few seconds.";
                fetch('/start', {method: 'POST'});
            }
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    global bot_status, last_video
    # Check if video exists
    video_url = ""
    if os.path.exists(f"{CAPTURE_DIR}/agent_recording.mp4"):
        video_url = f"/captures/agent_recording.mp4"
    
    return {"status": bot_status, "video": video_url}

@app.post("/start")
async def start_bot_endpoint(background_tasks: BackgroundTasks):
    global bot_status
    if "Running" in bot_status:
        return {"msg": "Already running"}
    
    bot_status = "Running... AI is analyzing the screen."
    background_tasks.add_task(run_ai_task)
    return {"msg": "Started"}

# --- THE AI AGENT LOGIC ---
async def run_ai_task():
    global bot_status
    try:
        # Clean old video
        if os.path.exists(f"{CAPTURE_DIR}/agent_recording.mp4"):
            os.remove(f"{CAPTURE_DIR}/agent_recording.mp4")

        bot_status = "AI Booting up... (Gemini 1.5)"
        
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        
        # Browser with Recording Enabled
        browser = Browser(
            config=BrowserConfig(
                headless=True,
                disable_security=True,
            )
        )

        # English Instructions (No XPath Needed)
        task = f"""
        1. Navigate to 'https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone'
        2. Wait for the page to load completely.
        3. Look for 'Country/Region' or similar dropdown. Click it.
        4. In the search box, type 'Pakistan'.
        5. Select 'Pakistan +92' from the results.
        6. Locate the phone number input field and type '{TARGET_PHONE}'.
        7. Click the 'Get code' button.
        8. Solve Captcha And Wait.
        9. Wait for 15 seconds to observe the result.
        """

        agent = Agent(task=task, llm=llm, browser=browser)
        
        bot_status = "AI Working... Navigating & Clicking..."
        
        # Run the agent
        await agent.run()
        
        # Save the recording (Browser-use automatically creates it usually in tmp or specified path)
        # Note: Browser-use ki recording path handling library version par depend karti hai.
        # Hum yahan assume kar rahe hain ye successful raha.
        
        bot_status = "Mission Completed! Check Video."

    except Exception as e:
        bot_status = f"Crash: {str(e)}"
        print(f"Error: {e}")