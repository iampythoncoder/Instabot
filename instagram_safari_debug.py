#!/usr/bin/env python3
"""
Instagram DM Conversation Bot - Debug Version
Shows exactly what OCR captures without aggressive filtering.
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
last_message_hash = None
last_raw_text = None


def human_delay(min_s=0.3, max_s=0.8):
    time.sleep(random.uniform(min_s, max_s))


def type_human(text):
    for char in text:
        if len(char) == 1 and char.isalnum():
            pyautogui.press(char)
        else:
            pyautogui.write(char)
        time.sleep(random.uniform(0.03, 0.08))


def capture_full_chat():
    """Capture the chat region."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        h, w = screenshot.shape[:2]
        return screenshot, (w, h)


def extract_all_text(image):
    """Extract all text from image."""
    if image.size == 0:
        return ""
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    texts = []
    for img in [gray, thresh]:
        try:
            text = pytesseract.image_to_string(img).strip()
            if text:
                texts.append(text)
        except:
            continue
    
    return '\n'.join(texts)


def find_message_lines(text):
    """Find lines that look like Instagram DM messages."""
    if not text:
        return []
    
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if len(line) < 3:
            continue
        lower = line.lower()
        skip_words = ['instagram', 'bot', 'python', 'ollama', 'terminal', 'safari',
                      'great job', 'up and running', 'watching for', 'sending:',
                      'ai:', 'got message', 'new message', 'convo bot', 'make sure',
                      'press ctrl', 'it looks like', 'localhost', 'almost there']
        if any(word in lower for word in skip_words):
            continue
        lines.append(line)
    
    return lines


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


def find_input_and_send(message):
    """Find input field and send message."""
    print(f"  Sending: '{message[:50]}...'")
    
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        h, w = screenshot.shape[:2]
        
        roi = screenshot[int(h * 0.80):int(h * 0.98), :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        
        for i, text in enumerate(data['text']):
            text_lower = text.lower().strip()
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0
            
            if conf > 20 and ('message' in text_lower or text_lower == ''):
                x = data['left'][i] + data['width'][i] // 2
                y = data['top'][i] + int(h * 0.80) + data['height'][i] // 2
                
                pyautogui.click(x, y)
                human_delay(0.3, 0.5)
                
                pyautogui.hotkey('cmd', 'a')
                human_delay(0.1, 0.2)
                pyautogui.press('backspace')
                
                type_human(message)
                human_delay(0.2, 0.4)
                pyautogui.press('enter')
                
                print("  ✓ Sent!")
                return True
        
        print(f"  Using fallback position")
        pyautogui.click(int(w * 0.55), int(h * 0.90))
        human_delay(0.3, 0.5)
        
        pyautogui.hotkey('cmd', 'a')
        human_delay(0.1, 0.2)
        pyautogui.press('backspace')
        
        type_human(message)
        human_delay(0.2, 0.4)
        pyautogui.press('enter')
        
        print("  ✓ Sent!")
        return True


def run_bot():
    """Main bot loop."""
    print("=" * 60)
    print("INSTAGRAM DM BOT - DEBUG VERSION")
    print("=" * 60)
    print("\nMake sure Instagram DM is open in Safari.")
    print("Bot will show debug output of what it captures.\n")
    print("Press Ctrl+C to stop.\n")
    
    try:
        resp = requests.get(f"{OLLAMA_ENDPOINT.replace('/api/generate', '/api/tags')}", timeout=5)
        if resp.status_code == 200:
            print("✓ Ollama connected")
    except:
        print("✗ Ollama not running")
        return
    
    print("\nWatching for messages...\n")
    
    global last_raw_text
    
    try:
        while True:
            screenshot, (w, h) = capture_full_chat()
            
            raw_text = extract_all_text(screenshot)
            
            if raw_text and raw_text != last_raw_text:
                print(f"\n--- NEW CAPTURE ---")
                print(f"Raw text ({len(raw_text)} chars):")
                print(f"  {raw_text[:200]}...")
                last_raw_text = raw_text
                
                lines = find_message_lines(raw_text)
                if lines:
                    print(f"\nMessage lines found ({len(lines)}):")
                    for i, line in enumerate(lines[:5]):
                        print(f"  {i+1}. {line[:80]}")
                    
                    message = max(lines, key=len)
                    print(f"\nUsing message: '{message[:60]}...'")
                    
                    reply = get_ai_response(message)
                    if reply:
                        print(f"AI reply: '{reply[:60]}...'")
                        find_input_and_send(reply)
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n✓ Bot stopped.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    run_bot()

