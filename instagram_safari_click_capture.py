ea#!/usr/bin/env python3
"""
Instagram DM Conversation Bot - Click to Define Region
First click = top-left of Safari DM, Second click = bottom-right
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
SYSTEM_PROMPT = """You are a friendly, casual Instagram DM assistant. Reply briefly (under 150 chars), naturally and friendly."""
CHECK_INTERVAL = 2

# Region to capture (set by clicking)
capture_region = None  # (left, top, right, bottom)


def human_delay(min_s=0.3, max_s=0.8):
    time.sleep(random.uniform(min_s, max_s))


def type_human(text):
    for char in text:
        if len(char) == 1 and char.isalnum():
            pyautogui.press(char)
        else:
            pyautogui.write(char)
        time.sleep(random.uniform(0.03, 0.08))


def setup_capture_region():
    """Let user click to define the capture region."""
    print("\n" + "=" * 60)
    print("SETUP: Define Safari Instagram DM capture region")
    print("=" * 60)
    print("\n1. Move mouse to TOP-LEFT corner of Safari DM window")
    print("2. Click to set the point")
    print("\nPress Enter when ready...", end='', flush=True)
    input()
    
    pos1 = pyautogui.position()
    print(f"   Top-left set at: {pos1}")
    
    print("\n1. Move mouse to BOTTOM-RIGHT corner of Safari DM window")
    print("2. Click to set the point")
    print("\nPress Enter when ready...", end='', flush=True)
    input()
    
    pos2 = pyautogui.position()
    print(f"   Bottom-right set at: {pos2}")
    
    # Store region
    global capture_region
    capture_region = (
        min(pos1.x, pos2.x),  # left
        min(pos1.y, pos2.y),  # top
        max(pos1.x, pos2.x),  # right
        max(pos1.y, pos2.y)   # bottom
    )
    
    print(f"\n✓ Capture region set: {capture_region}")
    print(f"   Size: {capture_region[2]-capture_region[0]} x {capture_region[3]-capture_region[1]}")
    return capture_region


def capture_region_image():
    """Capture the defined region."""
    global capture_region
    
    if capture_region is None:
        return None, None
    
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        h, w = screenshot.shape[:2]
        
        left = max(0, capture_region[0])
        top = max(0, capture_region[1])
        right = min(w, capture_region[2])
        bottom = min(h, capture_region[3])
        
        if right <= left or bottom <= top:
            return None, None
        
        region = screenshot[top:bottom, left:right]
        return region, (w, h)


def extract_text(image):
    """Extract text from image."""
    if image is None or image.size == 0:
        return ""
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    texts = []
    for img in [gray, thresh]:
        try:
            text = pytesseract.image_to_string(img).strip()
            if text and len(text) > 2:
                texts.append(text)
        except:
            continue
    
    if texts:
        return max(texts, key=len)
    return ""


def find_message_line(text):
    """Extract what looks like a message."""
    if not text:
        return None
    
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if len(line) < 5:
            continue
        skip = ['instagram', 'bot', 'python', 'ollama', 'terminal', 'watching', 
                'sending', 'ai:', 'convo', 'localhost', 'press ctrl']
        if any(s in line.lower() for s in skip):
            continue
        if '/' in line and ('.' in line or '_pycache_' in line):
            continue
        lines.append(line)
    
    if lines:
        return max(lines, key=len)
    return None


def get_ai_response(message):
    if not message or len(message.strip()) < 3:
        return None
    
    prompt = f"{SYSTEM_PROMPT}\n\nUser said: {message.strip()}\n\nYour reply:"
    
    try:
        resp = requests.post(
            OLLAMA_ENDPOINT,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        resp.raise_for_status()
        reply = resp.json().get("response", "").strip()
        return reply if reply and len(reply) > 2 else None
    except Exception as e:
        print(f"  AI error: {e}")
        return None


def find_input_position():
    """Find message input in the capture region."""
    global capture_region
    
    if capture_region is None:
        return None
    
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        h, w = screenshot.shape[:0]
        
        region_height = capture_region[3] - capture_region[1]
        roi_top = int(capture_region[1] + region_height * 0.7)
        roi_bottom = min(h, capture_region[3])
        
        roi = screenshot[roi_top:roi_bottom, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        
        for i, text in enumerate(data['text']):
            if 'message' in text.lower() and float(data['conf'][i]) > 20:
                x = data['left'][i] + data['width'][i] // 2
                y = data['top'][i] + roi_top + data['height'][i] // 2
                return (x, y)
        
        center_x = (capture_region[0] + capture_region[2]) // 2
        bottom_y = capture_region[3] - 30
        return (center_x, bottom_y)


def send_reply(message):
    """Send a reply."""
    print(f"  Sending: '{message[:50]}...'")
    
    input_pos = find_input_position()
    
    if input_pos:
        print(f"  Clicking at {input_pos}")
        pyautogui.click(input_pos[0], input_pos[1])
        human_delay(0.3, 0.5)
    else:
        print("  Using default position")
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = np.array(sct.grab(monitor))
            h, w = screenshot.shape[:2]
            pyautogui.click(int(w * 0.55), int(h * 0.90))
    
    human_delay(0.2, 0.3)
    
    pyautogui.hotkey('cmd', 'a')
    human_delay(0.1, 0.2)
    pyautogui.press('backspace')
    human_delay(0.1, 0.2)
    
    type_human(message)
    human_delay(0.2, 0.4)
    pyautogui.press('enter')
    
    print("  ✓ Sent!")
    return True


def run_bot():
    """Main bot loop."""
    print("=" * 60)
    print("INSTAGRAM DM BOT - CLICK TO SETUP")
    print("=" * 60)
    
    setup_capture_region()
    
    print("\n\nNow watching for messages in the selected region...")
    print("Press Ctrl+C to stop.\n")
    
    last_text = None
    reply_count = 0
    
    try:
        while True:
            image, _ = capture_region_image()
            text = extract_text(image)
            
            if text and text != last_text:
                print(f"\n--- NEW TEXT DETECTED ({len(text)} chars) ---")
                print(f"  {text[:150]}...")
                
                message = find_message_line(text)
                if message:
                    print(f"\nMessage: '{message[:80]}...'")
                    
                    reply = get_ai_response(message)
                    if reply:
                        print(f"AI: '{reply[:60]}...'")
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

