import network
import socket
import uasyncio
import utime
import ujson
import ws2812
from machine import Pin

# Configuration
SSID = "Number9"
PASSWORD = "freyacat"
NUM_LEDS = 283

# Static IP Configuration
STATIC_IP = "192.168.0.20"
SUBNET_MASK = "255.255.255.0"
GATEWAY = "192.168.0.1"
DNS = "8.8.8.8"

# Global state
current_brightness = 128
web_server_task = None
animation_task = None
led_states = ['#000000'] * 283  # Track current LED colors

# Onboard LED setup
onboard_led = Pin("LED", Pin.OUT)
led_status_task = None

# Onboard LED status patterns
async def led_status_connecting():
    """Fast blink while connecting to WiFi"""
    print('LED Status: Connecting to WiFi')
    while True:
        onboard_led.toggle()
        await uasyncio.sleep(0.2)

async def led_status_connected():
    """Slow pulse when connected and server running"""
    print('LED Status: Connected and running')
    while True:
        onboard_led.on()
        await uasyncio.sleep(1.5)
        onboard_led.off()
        await uasyncio.sleep(0.5)

async def led_status_request():
    """Quick double blink when handling a request"""
    onboard_led.on()
    await uasyncio.sleep(0.05)
    onboard_led.off()
    await uasyncio.sleep(0.05)
    onboard_led.on()
    await uasyncio.sleep(0.05)
    onboard_led.off()

async def led_status_error():
    """Rapid blink on error"""
    print('LED Status: Error')
    for _ in range(10):
        onboard_led.toggle()
        await uasyncio.sleep(0.1)

def set_led_status(status):
    """Change the LED status pattern"""
    global led_status_task
    
    if led_status_task and not led_status_task.done():
        led_status_task.cancel()
    
    if status == 'connecting':
        led_status_task = uasyncio.create_task(led_status_connecting())
    elif status == 'connected':
        led_status_task = uasyncio.create_task(led_status_connected())
    elif status == 'error':
        led_status_task = uasyncio.create_task(led_status_error())

# Connect to WiFi
async def connect_wifi():
    set_led_status('connecting')
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if STATIC_IP:
        wlan.ifconfig((STATIC_IP, SUBNET_MASK, GATEWAY, DNS))
        print('Static IP configured:', STATIC_IP)
    
    wlan.connect(SSID, PASSWORD)
    
    max_wait = 20
    while max_wait > 0:
        status = wlan.status()
        if status < 0 or status >= 3:
            break
        max_wait -= 1
        print('Waiting for connection...')
        await uasyncio.sleep(1)
    
    if wlan.status() != 3:
        set_led_status('error')
        raise RuntimeError('Network connection failed')
    else:
        print('Connected')
        status = wlan.ifconfig()
        print('IP:', status[0])
        print('Subnet:', status[1])
        print('Gateway:', status[2])
        print('DNS:', status[3])
        set_led_status('connected')
        return status[0]

# HTML webpage
def webpage():
    html = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>LED Controller</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0a;
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { 
            text-align: center; 
            margin-bottom: 30px; 
            font-size: 2em;
            font-family: monospace;
        }
        .controls {
            background: #1a1a1a;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .control-group {
            margin: 15px 0;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 14px;
            color: #aaa;
        }
        input[type="color"] {
            width: 100%;
            height: 50px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        input[type="range"] {
            width: 100%;
            height: 8px;
            border-radius: 5px;
            background: #333;
            outline: none;
            -webkit-appearance: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #4CAF50;
            cursor: pointer;
        }
        .button-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 10px;
            margin-top: 20px;
        }
        button {
            background: #2a2a2a;
            color: white;
            padding: 15px;
            border: 2px solid #444;
            border-radius: 10px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
        }
        button:hover {
            background: #3a3a3a;
            border-color: #666;
            transform: translateY(-2px);
        }
        button:active { transform: translateY(0); }
        .btn-fill { background: #4CAF50; border-color: #4CAF50; }
        .btn-clear { background: #f44336; border-color: #f44336; }
        .btn-rainbow { background: linear-gradient(90deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3); border: none; }
        .btn-wave { background: linear-gradient(90deg, #1e3a8a, #3b82f6, #06b6d4); border: none; }
        .range-group {
            margin: 20px 0;
        }
        .range-inputs {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }
        .range-inputs input {
            background: #2a2a2a;
            color: white;
            border: 2px solid #444;
            border-radius: 8px;
            padding: 10px;
            font-size: 14px;
        }
        .tree-container {
            background: #1a1a1a;
            padding: 30px;
            border-radius: 15px;
            margin: 20px auto;
            max-width: 800px;
            overflow: auto;
        }
        .tree-svg {
            display: block;
            margin: 0 auto;
        }
        .led-dot {
            cursor: pointer;
            transition: all 0.2s;
        }
        .led-dot:hover {
            r: 8;
            stroke: #fff;
            stroke-width: 2;
        }
        .led-line {
            stroke: #333;
            stroke-width: 2;
            fill: none;
        }
        .led-text {
            font-size: 10px;
            fill: #888;
            font-family: monospace;
            pointer-events: none;
            text-anchor: middle;
        }
        .status {
            text-align: center;
            padding: 10px;
            background: #1a1a1a;
            border-radius: 8px;
            margin-top: 10px;
            font-size: 12px;
            color: #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>LED Controller (283 LEDs)</h1>
        
        <div class="controls">
            <div class="control-group">
                <label>Color Picker</label>
                <input type="color" id="colorPicker" value="#00ff00">
            </div>
            
            <div class="control-group">
                <label>Brightness: <span id="brightnessValue">128</span></label>
                <input type="range" id="brightness" min="0" max="255" value="128">
            </div>
            
            <div class="button-grid">
                <button class="btn-fill" onclick="fillAll()">Fill All</button>
                <button class="btn-clear" onclick="clearAll()">Clear All</button>
                <button class="btn-rainbow" onclick="rainbow()">Rainbow</button>
                <button class="btn-wave" onclick="wave()">Wave Effect</button>
            </div>

            <div class="range-group">
                <label>Fill Range</label>
                <div class="range-inputs">
                    <input type="number" id="rangeStart" placeholder="Start (0)" min="0" max="282" value="0">
                    <input type="number" id="rangeEnd" placeholder="End (282)" min="0" max="282" value="282">
                </div>
                <button onclick="fillRange()" style="width: 100%; margin-top: 10px;">Fill Range</button>
            </div>
        </div>
        
        <div id="treeMap" class="tree-container"></div>
        <div class="status" id="status">Ready</div>
    </div>
    
    <script>
        const numLeds = 283;
        const ledStates = new Array(numLeds).fill('#000000');
        
        function buildLedPath() {
            const path = [];
            // Start from bottom right - LED 0
            let x = 900, y = 300;
            const hSpacing = 3;  // Horizontal spacing
            const vSpacing = 12; // Vertical spacing
            
            // LED 0 at start (bottom right)
            path.push({num: 0, x: x, y: y});
            
            // L 7 to LED 7 (going left from 0)
            for (let i = 1; i <= 7; i++) {
                x -= hSpacing;
                path.push({num: i, x: x, y: y});
            }
            // Now at LED 7, x ≈ 879, y = 300
            
            // U 4 to LED 11 (going up from 7)
            for (let i = 8; i <= 11; i++) {
                y -= vSpacing;
                path.push({num: i, x: x, y: y});
            }
            // Now at LED 11, y ≈ 252
            
            // R 3 to LED 14 (going right from 11)
            for (let i = 12; i <= 14; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            // Now at LED 14
            
            // UL 5 to LED 19 (diagonal up-left)
            for (let i = 15; i <= 19; i++) {
                x -= hSpacing * 0.8;
                y -= vSpacing * 0.8;
                path.push({num: i, x: x, y: y});
            }
            
            // R 3 to LED 22
            for (let i = 20; i <= 22; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // UL 4 to LED 26
            for (let i = 23; i <= 26; i++) {
                x -= hSpacing * 0.8;
                y -= vSpacing * 0.8;
                path.push({num: i, x: x, y: y});
            }
            
            // R 2 to LED 28
            for (let i = 27; i <= 28; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // UL 3 to LED 31
            for (let i = 29; i <= 31; i++) {
                x -= hSpacing * 0.8;
                y -= vSpacing * 0.8;
                path.push({num: i, x: x, y: y});
            }
            
            // U 1 to LED 32
            y -= vSpacing;
            path.push({num: 32, x: x, y: y});
            
            // Star LEDs 33-37 (clustered at top)
            const starX = x;
            const starY = y - vSpacing;
            for (let i = 33; i <= 37; i++) {
                path.push({num: i, x: starX + (i - 35) * 2, y: starY});
            }
            
            // D 1 from star to LED 38
            y -= vSpacing;
            path.push({num: 38, x: x, y: y});
            
            // D 1 to LED 39
            y += vSpacing;
            path.push({num: 39, x: x, y: y});
            
            // DL 3 to LED 42
            for (let i = 40; i <= 42; i++) {
                x -= hSpacing * 0.8;
                y += vSpacing * 0.8;
                path.push({num: i, x: x, y: y});
            }
            
            // R 3 to LED 45
            for (let i = 43; i <= 45; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // DL 3 to LED 48
            for (let i = 46; i <= 48; i++) {
                x -= hSpacing * 0.8;
                y += vSpacing * 0.8;
                path.push({num: i, x: x, y: y});
            }
            
            // R 4 to LED 52
            for (let i = 49; i <= 52; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // DL 5 to LED 57
            for (let i = 53; i <= 57; i++) {
                x -= hSpacing * 0.8;
                y += vSpacing * 0.8;
                path.push({num: i, x: x, y: y});
            }
            
            // R 5 to LED 62
            for (let i = 58; i <= 62; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // D 3 to LED 65
            for (let i = 63; i <= 65; i++) {
                y += vSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // L 30 to LED 95 (long horizontal line to left side)
            const targetX = 600;  // Left side position
            const ledCount = 95 - 65;
            const stepX = (targetX - x) / ledCount;
            for (let i = 66; i <= 95; i++) {
                x += stepX;
                path.push({num: i, x: x, y: y});
            }
            x = targetX;  // Ensure we're at exact position
            
            // Now on left side - zigzag pattern
            // U 2 to LED 97
            for (let i = 96; i <= 97; i++) {
                y -= vSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // R 23 to LED 120
            for (let i = 98; i <= 120; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // U 2 to LED 122
            for (let i = 121; i <= 122; i++) {
                y -= vSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // L 22 to LED 144
            for (let i = 123; i <= 144; i++) {
                x -= hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // U 2 to LED 146
            for (let i = 145; i <= 146; i++) {
                y -= vSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // R 24 to LED 170
            for (let i = 147; i <= 170; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // U 2 to LED 172
            for (let i = 171; i <= 172; i++) {
                y -= vSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // L 24 to LED 196
            for (let i = 173; i <= 196; i++) {
                x -= hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // U 2 to LED 198
            for (let i = 197; i <= 198; i++) {
                y -= vSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // R 23 to LED 221
            for (let i = 199; i <= 221; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // U 2 to LED 223
            for (let i = 222; i <= 223; i++) {
                y -= vSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // L 22 to LED 245
            for (let i = 224; i <= 245; i++) {
                x -= hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // U 2 to LED 247
            for (let i = 246; i <= 247; i++) {
                y -= vSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // R 14 to LED 261
            for (let i = 248; i <= 261; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // U 2 to LED 263
            for (let i = 262; i <= 263; i++) {
                y -= vSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // L 15 to LED 278
            for (let i = 264; i <= 278; i++) {
                x -= hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            // U 1 to LED 279
            y -= vSpacing;
            path.push({num: 279, x: x, y: y});
            
            // R 3 to LED 282
            for (let i = 280; i <= 282; i++) {
                x += hSpacing;
                path.push({num: i, x: x, y: y});
            }
            
            return path;
        }
        
        const ledPath = buildLedPath();
        
        const treeContainer = document.getElementById('treeMap');
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'tree-svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '350');
        svg.setAttribute('viewBox', '550 50 400 330');
        svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
        
        for (let i = 0; i < ledPath.length - 1; i++) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('class', 'led-line');
            line.setAttribute('x1', ledPath[i].x);
            line.setAttribute('y1', ledPath[i].y);
            line.setAttribute('x2', ledPath[i + 1].x);
            line.setAttribute('y2', ledPath[i + 1].y);
            svg.appendChild(line);
        }
        
        ledPath.forEach((led, idx) => {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('class', 'led-dot');
            circle.setAttribute('cx', led.x);
            circle.setAttribute('cy', led.y);
            circle.setAttribute('r', '2');
            circle.setAttribute('fill', '#0a0a0a');
            circle.setAttribute('stroke', '#333');
            circle.setAttribute('stroke-width', '0.5');
            circle.setAttribute('data-index', led.num);
            circle.style.cursor = 'pointer';
            circle.onclick = () => toggleLed(led.num);
            
            const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
            title.textContent = 'LED ' + led.num;
            circle.appendChild(title);
            
            svg.appendChild(circle);
            
            if (led.num === 0 || led.num === 7 || led.num === 11 || led.num === 14 || 
                led.num === 19 || led.num === 22 || led.num === 26 || led.num === 28 || 
                led.num === 31 || led.num === 35 || led.num === 65 || led.num === 95 ||
                led.num % 50 === 0) {
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('class', 'led-text');
                text.setAttribute('x', led.x);
                text.setAttribute('y', led.y - 3);
                text.textContent = led.num;
                svg.appendChild(text);
            }
        });
        
        treeContainer.appendChild(svg);
        
        // Poll for LED state updates every 500ms
        setInterval(() => {
            fetch('/state')
                .then(response => response.json())
                .then(data => {
                    if (data.states) {
                        // Update local state from server
                        data.states.forEach((color, index) => {
                            ledStates[index] = color;
                        });
                        updateDisplay();
                    }
                })
                .catch(err => console.log('Sync error:', err));
        }, 500);
        
        document.getElementById('brightness').oninput = function() {
            document.getElementById('brightnessValue').textContent = this.value;
        };
        
        function updateStatus(msg) {
            document.getElementById('status').textContent = msg;
        }
        
        function toggleLed(index) {
            const color = document.getElementById('colorPicker').value;
            ledStates[index] = color;
            updateDisplay();
            sendCommand('set', {index: index, color: color});
        }
        
        function fillAll() {
            const color = document.getElementById('colorPicker').value;
            ledStates.fill(color);
            updateDisplay();
            sendCommand('fill', {color: color});
        }
        
        function clearAll() {
            ledStates.fill('#000000');
            updateDisplay();
            sendCommand('clear', {});
        }
        
        function fillRange() {
            const start = parseInt(document.getElementById('rangeStart').value) || 0;
            const end = parseInt(document.getElementById('rangeEnd').value) || 282;
            const color = document.getElementById('colorPicker').value;
            
            for (let i = start; i <= end && i < numLeds; i++) {
                ledStates[i] = color;
            }
            updateDisplay();
            sendCommand('range', {start: start, end: end, color: color});
        }
        
        function rainbow() {
            updateStatus('Running rainbow...');
            sendCommand('rainbow', {});
        }
        
        function wave() {
            updateStatus('Running wave...');
            sendCommand('wave', {});
        }
        
        function updateDisplay() {
            document.querySelectorAll('.led-dot').forEach(circle => {
                const index = parseInt(circle.getAttribute('data-index'));
                const color = ledStates[index];
                circle.setAttribute('fill', color);
                if (color !== '#000000') {
                    circle.setAttribute('r', '3');
                    circle.style.filter = `drop-shadow(0 0 4px ${color})`;
                } else {
                    circle.setAttribute('r', '2');
                    circle.style.filter = 'none';
                }
            });
        }
        
        function sendCommand(action, data) {
            const brightness = document.getElementById('brightness').value;
            updateStatus('Sending: ' + action);
            fetch('/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: action, data: data, brightness: parseInt(brightness)})
            }).then(() => {
                updateStatus('Ready');
            }).catch(err => {
                updateStatus('Error: ' + err);
            });
        }
    </script>
</body>
</html>"""
    return html

# Convert hex color to RGB with brightness
def hex_to_rgb(hex_color, brightness=255):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) * brightness // 255
    g = int(hex_color[2:4], 16) * brightness // 255
    b = int(hex_color[4:6], 16) * brightness // 255
    print(f'hex_to_rgb: {hex_color} -> ({r}, {g}, {b}) with brightness {brightness}')
    return (r, g, b)

# Helper function to stop any running animation
async def stop_animation():
    global animation_task
    if animation_task and not animation_task.done():
        print('Stopping running animation')
        animation_task.cancel()
        try:
            await animation_task
        except uasyncio.CancelledError:
            pass
        animation_task = None

# LED control functions
async def set_led(index, color, brightness):
    global led_states
    await stop_animation()
    rgb = hex_to_rgb(color, brightness)
    print(f'Setting LED {index} to {rgb} (brightness: {brightness})')
    ws2812.pixels_set(index, rgb)
    await ws2812.pixels_show()
    led_states[index] = color
    print('LED updated')

async def fill_all(color, brightness):
    global led_states
    await stop_animation()
    rgb = hex_to_rgb(color, brightness)
    print(f'Filling all LEDs with {rgb} (brightness: {brightness})')
    ws2812.pixels_fill(rgb)
    await ws2812.pixels_show()
    led_states = [color] * NUM_LEDS
    print('All LEDs filled')

async def fill_range(start, end, color, brightness):
    global led_states
    await stop_animation()
    rgb = hex_to_rgb(color, brightness)
    print(f'Filling range {start}-{end} with {rgb} (brightness: {brightness})')
    for i in range(start, min(end + 1, NUM_LEDS)):
        ws2812.pixels_set(i, rgb)
        led_states[i] = color
    await ws2812.pixels_show()
    print(f'Range {start}-{end} filled')

async def clear_all():
    global led_states
    await stop_animation()
    print('Clearing all LEDs')
    ws2812.pixels_fill((0, 0, 0))
    await ws2812.pixels_show()
    led_states = ['#000000'] * NUM_LEDS
    print('All LEDs cleared')

async def rainbow_effect(brightness):
    print(f'Starting rainbow effect (brightness: {brightness})')
    try:
        for j in range(255):
            for i in range(NUM_LEDS):
                pixel_index = (i * 256 // NUM_LEDS) + j
                r = int((128 + 127 * (pixel_index & 0xFF) / 255) * brightness / 255)
                g = int((128 + 127 * ((pixel_index >> 8) & 0xFF) / 255) * brightness / 255)
                b = int((128 + 127 * ((pixel_index >> 16) & 0xFF) / 255) * brightness / 255)
                ws2812.pixels_set(i, (r, g, b))
            await ws2812.pixels_show()
            await uasyncio.sleep_ms(20)
        print('Rainbow effect complete')
    except uasyncio.CancelledError:
        print('Rainbow effect cancelled')
        raise

async def wave_effect(brightness):
    print(f'Starting wave effect (brightness: {brightness})')
    try:
        for j in range(100):
            for i in range(NUM_LEDS):
                val = int((128 + 127 * ((i + j * 3) % NUM_LEDS) / NUM_LEDS) * brightness / 255)
                ws2812.pixels_set(i, (0, val, val))
            await ws2812.pixels_show()
            await uasyncio.sleep_ms(30)
        print('Wave effect complete')
    except uasyncio.CancelledError:
        print('Wave effect cancelled')
        raise

# Handle HTTP requests
async def handle_client(reader, writer):
    try:
        uasyncio.create_task(led_status_request())
        
        request_line = await reader.readline()
        if not request_line:
            return
        
        request = request_line.decode().strip()
        print('Request:', request)
        
        headers = {}
        content_length = 0
        while True:
            line = await reader.readline()
            if line == b'\r\n' or line == b'\n' or not line:
                break
            if b':' in line:
                key, value = line.decode().strip().split(':', 1)
                headers[key.strip().lower()] = value.strip()
                if key.strip().lower() == 'content-length':
                    content_length = int(value.strip())
        
        parts = request.split()
        if len(parts) < 2:
            return
        
        method = parts[0]
        path = parts[1]
        
        if path == '/' and method == 'GET':
            response = webpage()
            writer.write('HTTP/1.1 200 OK\r\n')
            writer.write('Content-Type: text/html\r\n')
            writer.write('Connection: close\r\n')
            writer.write('\r\n')
            writer.write(response)
            await writer.drain()
        
        elif path == '/state' and method == 'GET':
            # Return current LED states for synchronization
            state_json = ujson.dumps({'states': led_states})
            writer.write('HTTP/1.1 200 OK\r\n')
            writer.write('Content-Type: application/json\r\n')
            writer.write('Connection: close\r\n')
            writer.write('\r\n')
            writer.write(state_json)
            await writer.drain()
        
        elif path == '/control' and method == 'POST':
            body = b''
            if content_length > 0:
                body = await reader.read(content_length)
            
            try:
                data = ujson.loads(body.decode())
                action = data['action']
                brightness = data['brightness']
                
                print('='*40)
                print(f'Received command: {action}')
                print(f'Data: {data}')
                print(f'Brightness: {brightness}')
                print('='*40)
                
                if action == 'set':
                    await set_led(data['data']['index'], data['data']['color'], brightness)
                elif action == 'fill':
                    await fill_all(data['data']['color'], brightness)
                elif action == 'clear':
                    await clear_all()
                elif action == 'range':
                    await fill_range(data['data']['start'], data['data']['end'], 
                                   data['data']['color'], brightness)
                elif action == 'rainbow':
                    global animation_task
                    await stop_animation()
                    animation_task = uasyncio.create_task(rainbow_effect(brightness))
                elif action == 'wave':
                    global animation_task
                    await stop_animation()
                    animation_task = uasyncio.create_task(wave_effect(brightness))
                
                print(f'Command {action} completed successfully')
                
                writer.write('HTTP/1.1 200 OK\r\n')
                writer.write('Content-Type: text/plain\r\n')
                writer.write('Connection: close\r\n')
                writer.write('\r\n')
                writer.write('OK')
                await writer.drain()
            except Exception as e:
                print('Control error:', e)
                writer.write('HTTP/1.1 500 Error\r\n\r\n')
                await writer.drain()
        
    except Exception as e:
        print('Request error:', e)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass

# Start web server
async def start_server(ip):
    print('Starting server on', ip)
    server = await uasyncio.start_server(handle_client, "0.0.0.0", 80)
    print('Server running on http://{}:80'.format(ip))
    print('Multiple devices can connect!')
    while True:
        await uasyncio.sleep(1)

# Main function
async def main():
    await clear_all()
    ip = await connect_wifi()
    await start_server(ip)

# Run the server
if __name__ == "__main__":
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        print('Server stopped')
        uasyncio.run(clear_all())