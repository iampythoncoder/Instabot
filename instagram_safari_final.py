#!/usr/bin/env python3
"""
Instagram DM Bot - Fixed to type ONLY in Safari
"""

import pyautogui
import time
import random
import cv2
import numpy as np
import mss
import pytesseract
import requests


# Config
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"
SYSTEM_PROMPT = """You are a friendly Instagram DM assistant. Reply briefly (under 150 chars)."""
CHECK_INTERVAL = 2

# Safari window position (set by clicking)
safari_left = None
safari_top = None
safari_right = None
safari_bottom = None


def human_delay(min_s=0.3, max_s=0.8):
    time.sleep(random.uniform(min_s, max_s))


def type_human(text):
    for char in text:
        if len(char) == 1 and char.isalnum():
            pyautogui.press(char)
        else:
            pyautogui.write(char)
        time.sleep(random.uniform(0.03, 0.07))


def setup_safari_position():
    """Click on Safari window to set its position."""
    global safari_left, safari_top, safari_right, safari_bottom
    
    print("\n" + "=" * 60)
    print("SETUP: Click on Safari window")
    print("=" * 60)
    print("\nClick somewhere inside the Safari browser window.")
    print("Press Enter after clicking...", end='', flush=True)
    input()
    
    # Get click position
    click_pos = pyautogui.position()
    print(f"   Clicked at: {click_pos}")
    
    # Assume typical Safari window size and position
    # Set a reasonable capture area around the click
    safari_left = click_pos.x - 300
    safari_top = click_pos.y - 200
    safari_right = click_pos.x + 400
    safari_bottom = click_pos.y + 300
    
    # Ensure valid bounds
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        w, h = monitor["width"], monitor["height"]
        safari_left = max(0, safari_left)
        safari_top = max(0, safari_top)
        safari_right = min(w, safari_right)
        safari_bottom = min(h, safari_bottom)
    
    print(f"\n✓ Safari area set: ({safari_left}, {safari_top}) to ({safari_right}, {safari_bottom})")
    return (safari_left, safari_top, safari_right, safari_bottom)


def capture_safari():
    """Capture the Safari region."""
    if safari_left is None:
        return None
    
    with mss.mss() as sct:
        screenshot = np.array(sct.grab(sct.monitors[1]))
        h, w = screenshot.shape[:2]
        
        region = screenshot[safari_top:safari_bottom, safari_left:safari_right]
        return region


def extract_message_text(image):
    """Extract message text from image."""
    if image is None or image.size == 0:
        return ""
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    texts = []
    for img in [gray, thresh]:
        try:
            text = pytesseract.image_to_string(img).strip()
            if text and len(text) > 3:
                texts.append(text)
        except:
            continue
    
    if texts:
        return max(texts, key=len)
    return ""


def find_message_line(text):
    """Extract actual message from OCR text."""
    if not text:
        return None
    
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if len(line) < 5:
            continue
        # Skip code/file patterns
        skip = ['.py', '.md', 'import', 'def ', 'class ', 'return', 
                'print(', 'instagram', 'bot', 'python', 'ollama',
                'vscode', 'explorer', '_pycache_', 'venv', '>>>']
        if any(s in line.lower() for s in skip):
            continue
        lines.append(line)
    
    if lines:
        return max(lines, key=len)
    return None


def get_ai_response(message):
    if not message or len(message.strip()) < 3:
        return None
    
    prompt = f"{SYSTEM_PROMPT}\n\nUser: {message.strip()}\n\nReply:"
    
    try:
        resp = requests.post(
            OLLAMA_ENDPOINT,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except:
        return None


def find_input_position():
    """Find the message input position IN SAFARI ONLY."""
    if safari_left is None:
        return None
    
    with mss.mss() as sct:
        screenshot = np.array(sct.grab(sct.monitors[1]))
        h, w = screenshot.shape[:2]
        
        # Look at bottom portion of Safari area for input
        input_roi_top = int(safari_top + (safari_bottom - safari_top) * 0.75)
        input_roi_bottom = min(h, safari_bottom)
        
        roi = screenshot[input_roi_top:input_roi_bottom, safari_left:safari_right]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        
        for i, text in enumerate(data['text']):
            text_lower = text.lower().strip()
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0
            
            # Look for message input placeholder
            if conf > 30 and ('message' in text_lower or text_lower == ''):
                x = data['left'][i] + safari_left + data['width'][i] // 2
                y = data['top'][i] + input_roi_top + data['height'][i] // 2
                return (x, y)
        
        # Fallback: click at bottom center of Safari area
        center_x = (safari_left + safari_right) // 2
        bottom_y = safari_bottom - 40
        return (center_x, bottom_y)


def send_reply(message):
    """Send reply ONLY in Safari."""
    print(f"  Sending: '{message[:50]}...'")
    
    input_pos = find_input_position()
    
    if input_pos:
        print(f"  Clicking Safari input at {input_pos}")
        pyautogui.click(input_pos[0], input_pos[1])
        human_delay(0.4, 0.6)
    else:
        print("  Using Safari fallback position")
        pyautogui.click((safari_left + safari_right) // 2, safari_bottom - 40)
        human_delay(0.4, 0.6)
    
    # Clear and type
    pyautogui.hotkey('cmd', 'a')
    human_delay(0.15, 0.25)
    pyautogui.press('backspace')
    human_delay(0.15, 0.25)
    
    type_human(message)
    human_delay(0.3, 0.5)
    
    pyautogui.press('enter')
    print("  ✓ Sent in Safari!")
    return True


def run_bot():
    """Main bot loop."""
    print("=" * 60)
    print("INSTAGRAM DM BOT - SAFARI ONLY")
    print("=" * 60)
    
    setup_safari_position()
    
    print("\nWatching for messages in Safari...")
    print("Press Ctrl+C to stop.\n")
    
    last_text = None
    reply_count = 0
    
    try:
        while True:
            image = capture_safari()
            text = extract_message_text(image)
            
            if text and text != last_text:
                message = find_message_line(text)
                if message:
                    print(f"\n[{reply_count + 1}] Message: '{message[:60]}...'")
                    
                    reply = get_ai_response(message)
                    if reply:
                        print(f"  AI: '{reply[:50]}...'")
                        send_reply(reply)
                        reply_count += 1
                
                last_text = text
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\n✓ Bot stopped. Sent {reply_count} replies.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    run_bot()
