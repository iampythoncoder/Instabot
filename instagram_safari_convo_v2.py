#!/usr/bin/env python3
"""
Instagram DM Conversation Bot - Safari Version v2
Fixed capture area and input detection.
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
CHECK_INTERVAL = 3
last_message_hash = None


def human_delay(min_s=0.3, max_s=0.8):
    time.sleep(random.uniform(min_s, max_s))


def type_human(text):
    for char in text:
        if len(char) == 1 and char.isalnum():
            pyautogui.press(char)
        else:
            pyautogui.write(char)
        time.sleep(random.uniform(0.02, 0.06))


def capture_chat_region():
    """Capture chat region - Safari Instagram DM area."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        h, w = screenshot.shape[:2]
        
        # Instagram DM in Safari: chat is in center/right portion
        chat_left = int(w * 0.20)
        chat_right = int(w * 0.95)
        chat_top = int(h * 0.10)
        chat_bottom = int(h * 0.85)
        
        region = screenshot[chat_top:chat_bottom, chat_left:chat_right]
        return region, (w, h)


def extract_text_from_image(image):
    if image.size == 0:
        return ""
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inverted = 255 - thresh
    
    texts = []
    for img in [gray, thresh, inverted]:
        try:
            text = pytesseract.image_to_string(img).strip()
            if text and len(text) > 2:
                texts.append(text)
        except:
            continue
    
    if texts:
        return max(texts, key=len)
    return ""


def clean_message(text):
    if not text:
        return ""
    
    # Terminal patterns to filter out
    terminal_patterns = [
        'instagram', 'bot', 'python', 'ollama', 'safari', 'terminal', 'command',
        'great job', 'up and running', 'almost there', 'double-check', 'localhost',
        'Watching for', 'Sending:', 'AI:', 'Got message', 'New message', 'It looks like',
        'CONVO BOT', 'Make sure', 'Press Ctrl'
    ]
    
    text_lower = text.lower()
    for pattern in terminal_patterns:
        if pattern in text_lower:
            return ""
    
    if len(text) < 5:
        return ""
    
    alpha_count = sum(c.isalnum() or c.isspace() for c in text)
    if alpha_count < len(text) * 0.5:
        return ""
    
    return text.strip()


def get_ai_response(message_text):
    if not message_text or len(message_text.strip()) < 3:
        return None
    
    prompt = f"{SYSTEM_PROMPT}\n\nUser: {message_text.strip()}\n\nReply:"
    
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


def find_input_field():
    """Find message input field - use center-right position for Safari Instagram."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        h, w = screenshot.shape[:2]
        
        # Look for "Message" text in the lower portion
        roi_top = int(h * 0.75)
        roi_bottom = int(h * 0.95)
        roi_left = int(w * 0.25)
        roi_right = int(w * 0.95)
        
        roi = screenshot[roi_top:roi_bottom, roi_left:roi_right]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        
        for i, text in enumerate(data['text']):
            text_lower = text.lower().strip()
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0
            
            if conf > 25 and ('message' in text_lower or 'send' == text_lower):
                x = data['left'][i] + roi_left + data['width'][i] // 2
                y = data['top'][i] + roi_top + data['height'][i] // 2
                return (x, y)
        
        # Fallback: typical Instagram DM input position
        return (int(w * 0.55), int(h * 0.90))


def send_reply(message):
    """Send a reply message."""
    print(f"  Sending: '{message[:50]}...'")
    
    input_pos = find_input_field()
    print(f"  Clicking input at {input_pos}")
    pyautogui.moveTo(input_pos[0], input_pos[1])
    human_delay(0.1, 0.2)
    pyautogui.click()
    human_delay(0.3, 0.5)
    
    pyautogui.hotkey('cmd', 'a')
    human_delay(0.1, 0.2)
    pyautogui.press('backspace')
    human_delay(0.1, 0.2)
    
    type_human(message)
    human_delay(0.2, 0.4)
    
    pyautogui.press('enter')
    print("  ✓ Sent!")
    return True


def hash_message(text):
    return hash(text.lower().strip())


def check_for_new_messages():
    """Check if there's a new message to respond to."""
    global last_message_hash
    
    chat_image, (screen_w, screen_h) = capture_chat_region()
    
    raw_text = extract_text_from_image(chat_image)
    message = clean_message(raw_text)
    
    if not message or len(message) < 5:
        return None
    
    print(f"  [DEBUG] Captured: '{message[:80]}...'")
    
    msg_hash = hash_message(message)
    if msg_hash == last_message_hash:
        return None
    
    if last_message_hash is not None:
        print(f"  New message detected!")
        last_message_hash = msg_hash
        return message
    
    last_message_hash = msg_hash
    return None


def run_conversation_bot():
    """Main conversation bot loop."""
    print("=" * 60)
    print("INSTAGRAM DM CONVO BOT - SAFARI v2")
    print("=" * 60)
    print("\nMake sure Instagram DM is open in Safari!")
    print(f"Bot will check every {CHECK_INTERVAL} seconds.\n")
    print("Press Ctrl+C to stop.\n")
    
    try:
        resp = requests.get(f"{OLLAMA_ENDPOINT.replace('/api/generate', '/api/tags')}", timeout=5)
        if resp.status_code == 200:
            print("✓ Ollama connected")
    except:
        print("✗ Ollama not running. Start with: ollama serve")
        return
    
    print("\nWatching for messages...\n")
    
    message_count = 0
    
    try:
        while True:
            message = check_for_new_messages()
            
            if message:
                print(f"\n[{message_count + 1}] Processing: '{message[:50]}...'")
                
                reply = get_ai_response(message)
                
                if reply:
                    print(f"  AI: '{reply[:50]}...'")
                    send_reply(reply)
                    message_count += 1
                else:
                    print("  No reply generated")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\n✓ Bot stopped. Responded to {message_count} messages.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    run_conversation_bot()

