#!/usr/bin/env python3
"""
Instagram DM Conversation Bot - Safari Version
Maintains a conversation on an Instagram DM open in Safari.
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
    """Capture only Safari browser content, avoiding terminal area."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        h, w = screenshot.shape[:2]
        
        # Safari is typically on the right side (avoid terminal on left)
        # Start capture at 35% of screen width to avoid terminal completely
        chat_left = int(w * 0.35)
        chat_right = int(w * 0.98)
        chat_top = int(h * 0.08)
        chat_bottom = int(h * 0.88)
        
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
            if text and len(text) > 3:
                texts.append(text)
        except:
            continue
    
    return max(texts, key=len) if texts else ""


def clean_message(text):
    if not text:
        return ""
    
    # Common UI noise from Instagram
    noise = ['Message', 'Send', 'Like', 'Photo', 'Video', 'GIF', 'Sticker', 'Heart', 'Reply', 'Message...']
    
    # Terminal/common CLI patterns to exclude
    terminal_patterns = [
        'instagram', 'bot', 'python', 'ollama', 'safari', 'terminal', 'command',
        'great job', 'up and running', 'almost there', 'double-check', 'localhost',
        'Watching for', 'Sending:', 'AI:', 'Got message', 'New message', 'It looks like'
    ]
    
    text_lower = text.lower()
    
    # Skip if text contains terminal patterns
    for pattern in terminal_patterns:
        if pattern in text_lower:
            return ""
    
    lines = text.split('\n')
    cleaned = []
    
    for line in lines:
        line = line.strip()
        if len(line) < 3:
            continue
        if line in noise:
            continue
        alpha_count = sum(c.isalnum() for c in line)
        if alpha_count > len(line) * 0.4:
            cleaned.append(line)
    
    return ' '.join(cleaned)


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
    """Find message input field by OCR."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        h, w = screenshot.shape[:2]
        
        # Look at right portion where input usually is (Safari area)
        roi = screenshot[int(h * 0.85):int(h * 0.98), int(w * 0.35):]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        
        for i, text in enumerate(data['text']):
            text_lower = text.lower().strip()
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0
            
            if conf > 30 and ('message' in text_lower):
                x = data['left'][i] + int(w * 0.35) + data['width'][i] // 2
                y = data['top'][i] + int(h * 0.85) + data['height'][i] // 2
                return (x, y)
        
        # Fallback position (center-right of screen)
        return (int(w * 0.60), int(h * 0.92))


def send_reply(message):
    """Send a reply message."""
    print(f"  Sending: '{message[:50]}...'")
    
    # Find and click input field
    input_pos = find_input_field()
    pyautogui.click(input_pos[0], input_pos[1])
    human_delay(0.3, 0.5)
    
    # Clear existing text
    pyautogui.hotkey('cmd', 'a')
    human_delay(0.1, 0.2)
    pyautogui.press('backspace')
    
    # Type message
    type_human(message)
    human_delay(0.2, 0.4)
    
    # Send
    pyautogui.press('enter')
    print("  ✓ Sent!")
    return True


def hash_message(text):
    """Create simple hash of message for change detection."""
    return hash(text.lower().strip())


def check_for_new_messages():
    """Check if there's a new message to respond to."""
    global last_message_hash
    
    # Capture chat
    chat_image, (screen_w, screen_h) = capture_chat_region()
    
    # Extract text
    raw_text = extract_text_from_image(chat_image)
    message = clean_message(raw_text)
    
    if not message or len(message) < 3:
        return None
    
    # Check if this is a new message
    msg_hash = hash_message(message)
    if msg_hash == last_message_hash:
        return None  # Same message, no new activity
    
    # Check if message is different enough from last
    if last_message_hash is not None:
        # New message detected
        print(f"  New message detected: '{message[:60]}...'")
        last_message_hash = msg_hash
        return message
    
    # First time seeing a message
    last_message_hash = msg_hash
    return None


def run_conversation_bot():
    """Main conversation bot loop."""
    print("=" * 60)
    print("INSTAGRAM DM CONVO BOT - SAFARI VERSION")
    print("=" * 60)
    print("\nMake sure Instagram DM is open in Safari!")
    print(f"Bot will check every {CHECK_INTERVAL} seconds for new messages.\n")
    print("Press Ctrl+C to stop.\n")
    
    # Verify Ollama is running
    try:
        resp = requests.get(f"{OLLAMA_ENDPOINT.replace('/api/generate', '/api/tags')}", timeout=5)
        if resp.status_code == 200:
            print("✓ Ollama connected")
        else:
            print("✗ Ollama not responding")
            return
    except:
        print("✗ Ollama not running. Start with: ollama serve")
        return
    
    print("\nWatching for messages...\n")
    
    message_count = 0
    
    try:
        while True:
            # Check for new messages
            message = check_for_new_messages()
            
            if message:
                print(f"\n[{message_count + 1}] Got message: '{message[:50]}...'")
                
                # Get AI response
                reply = get_ai_response(message)
                
                if reply:
                    print(f"  AI: '{reply[:50]}...'")
                    send_reply(reply)
                    message_count += 1
                else:
                    print("  No reply generated")
            
            # Wait before checking again
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\n✓ Bot stopped. Responded to {message_count} messages.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    run_conversation_bot()

