import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from playwright.async_api import async_playwright

app = FastAPI()

# --- GLOBAL STATE ---
browser = None
page = None
playwright = None

# --- HTML DASHBOARD (Remote Controller) ---
@app.get("/", response_class=HTMLResponse)
async def remote_dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🕹️ REMOTE BROWSER CONTROLLER</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #222; color: #fff; font-family: sans-serif; text-align: center; margin: 0; }
            #screen-container { position: relative; display: inline-block; border: 2px solid #00e676; margin-top: 10px; }
            img { display: block; max-width: 100%; height: auto; cursor: crosshair; }
            .controls { padding: 10px; background: #333; position: sticky; top: 0; z-index: 100; }
            input { padding: 8px; width: 60%; border-radius: 4px; border: none; }
            button { padding: 8px 15px; font-weight: bold; cursor: pointer; background: #00bcd4; border: none; border-radius: 4px; color: white; margin: 2px; }
            .btn-red { background: #f44336; }
            .btn-green { background: #4caf50; }
            #status { margin-top: 5px; font-size: 12px; color: #aaa; }
            #final-link { word-break: break-all; color: #00e676; font-family: monospace; padding: 10px; background: #111; margin: 10px; display: none;}
        </style>
    </head>
    <body>
        <div class="controls">
            <button onclick="startBrowser()" class="btn-green">🚀 START CHROME</button>
            <input type="text" id="typeText" placeholder="Type here (e.g. Huawei)...">
            <button onclick="sendType()">⌨️ TYPE</button>
            <button onclick="pressEnter()">↵ ENTER</button>
            <br>
            <button onclick="goGoogle()">🌐 GO GOOGLE</button>
            <button onclick="getLink()" class="btn-red">🔗 GET FINAL LINK</button>
            <div id="status">Ready to launch...</div>
        </div>

        <div id="final-link"></div>

        <div id="screen-container">
            <img id="remote-screen" src="" onclick="handleClick(event)">
        </div>

        <script>
            // --- IMAGE STREAMING ---
            setInterval(() => {
                const img = document.getElementById('remote-screen');
                // Add timestamp to prevent caching
                img.src = "/screenshot?" + new Date().getTime();
            }, 1000); // Update every 1 second

            // --- CLICK HANDLER ---
            function handleClick(event) {
                const img = document.getElementById('remote-screen');
                const rect = img.getBoundingClientRect();
                
                // Calculate scale (because image might be shrunk on mobile)
                // Real Browser Width = 1280 (Set in python)
                // Displayed Width = rect.width
                
                const scaleX = 1280 / rect.width;
                const scaleY = 720 / rect.height;

                const x = (event.clientX - rect.left) * scaleX;
                const y = (event.clientY - rect.top) * scaleY;

                fetch(`/click?x=${x}&y=${y}`);
                document.getElementById('status').innerText = `Clicked at ${Math.round(x)}, ${Math.round(y)}`;
            }

            // --- COMMANDS ---
            function startBrowser() { fetch('/start'); document.getElementById('status').innerText = "Browser Starting..."; }
            
            function sendType() { 
                const txt = document.getElementById('typeText').value;
                fetch(`/type?text=${encodeURIComponent(txt)}`);
                document.getElementById('status').innerText = `Typing: ${txt}`;
                document.getElementById('typeText').value = "";
            }

            function pressEnter() { fetch('/enter'); document.getElementById('status').innerText = "Sent Enter"; }
            function goGoogle() { fetch('/goto?url=https://google.com'); document.getElementById('status').innerText = "Loading Google..."; }
            
            function getLink() {
                fetch('/get_url').then(r => r.text()).then(url => {
                    const box = document.getElementById('final-link');
                    box.style.display = 'block';
                    box.innerText = url;
                    alert("URL Copied to bottom of page!");
                });
            }
        </script>
    </body>
    </html>
    """

# --- BACKEND LOGIC ---

@app.get("/start")
async def start_browser():
    global playwright, browser, page
    if browser is None:
        playwright = await async_playwright().start()
        # Launching HEADLESS but with UI args
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720}, # Fixed resolution for calculation
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto("about:blank")
    return {"status": "started"}

@app.get("/screenshot")
async def get_screenshot():
    global page
    if page:
        # Take screenshot and return directly as image
        bytes = await page.screenshot(type='jpeg', quality=50) # Low quality for speed
        return Response(content=bytes, media_type="image/jpeg")
    return Response(status_code=404)

@app.get("/click")
async def perform_click(x: float, y: float):
    global page
    if page:
        try:
            # Human-like click
            await page.mouse.move(x, y)
            await page.mouse.down()
            await asyncio.sleep(0.1)
            await page.mouse.up()
        except: pass
    return {"status": "clicked"}

@app.get("/type")
async def perform_type(text: str):
    global page
    if page:
        await page.keyboard.type(text)
    return {"status": "typed"}

@app.get("/enter")
async def perform_enter():
    global page
    if page:
        await page.keyboard.press("Enter")
    return {"status": "enter_pressed"}

@app.get("/goto")
async def perform_goto(url: str):
    global page
    if page:
        await page.goto(url)
    return {"status": "navigating"}

@app.get("/get_url")
async def get_current_url():
    global page
    if page:
        return Response(content=page.url, media_type="text/plain")
    return "No Browser"