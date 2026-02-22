import pyautogui
import time
import random
import cv2
import numpy as np
import mss
import pytesseract
import requests
import re


# ==============================================================================
# CONFIG
# ==============================================================================

MISTRAL_ENDPOINT = "http://localhost:11434/api/generate"
MISTRAL_MODEL = "mistral"

WAIT_TIME = 10  # Seconds between checking for new messages


# ==============================================================================
# HELPERS
# ==============================================================================

def human_delay(min_s=0.5, max_s=1.0):
    time.sleep(random.uniform(min_s, max_s))


def type_human(text):
    for char in text:
        if len(char) == 1 and char.isalnum():
            pyautogui.press(char)
        else:
            pyautogui.write(char)
        time.sleep(random.uniform(0.02, 0.05))


def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        return screenshot, monitor["width"], monitor["height"]


# ==============================================================================
# SEND MESSAGE
# ==============================================================================

def send_reply(message):
    screenshot, screen_w, screen_h = capture_screen()
    
    # Input field is at bottom center of chat
    input_x = int(screen_w * 0.50)
    input_y = int(screen_h * 0.88)
    
    print(f"  [Sending] {message[:50]}...")
    pyautogui.click(input_x, input_y)
    human_delay(0.3, 0.5)
    
    type_human(message)
    human_delay(0.2, 0.4)
    pyautogui.press("enter")
    return True


# ==============================================================================
# AI REPLY
# ==============================================================================

def get_ai_reply(message_text):
    """Generate AI reply using Mistral model."""
    if not message_text or not message_text.strip():
        return None

    cleaned = clean_message_text(message_text)
    if not is_valid_message(cleaned):
        return None

    prompt = (
        "You are a friendly, helpful Instagram DM assistant. Reply briefly, naturally, and under 3 sentences.\n\n"
        f"User said: {cleaned}\n\n"
        "Your reply:"
    )

    try:
        resp = requests.post(
            MISTRAL_ENDPOINT,
            json={"model": MISTRAL_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        resp.raise_for_status()
        reply = resp.json().get("response", "").strip()
        
        if reply and len(reply) > 2:
            return reply
        else:
            return "Thanks for your message! 👍"
    except Exception as e:
        print(f"  [AI Error] {e}")
        return "Thanks for your message!"


# ==============================================================================
# MESSAGE CLEANING
# ==============================================================================

def clean_message_text(text):
    """Clean extracted message text."""
    if not text:
        return ""
    
    # Very strict UI noise filter
    ui_noise = [
        'send', 'message', 'like', 'emoji', 'photo', 'video', 'gif', 'sticker',
        'heart', 'reply', 'forward', 'info', 'call', 'video call',
        'follow', 'following', 'followers', 'profile', 'settings', 'search',
        'home', 'explore', 'notifications', 'likes', 'comments', 'share',
        'more', 'options', 'cancel', 'done', 'save', 'delete', 'archive',
        'note', 'notes', 'instagram', 'inbox', 'requests', 'hidden',
        'thread', 'chat', 'text', 'new', 'create', 'shared', 'followers',
        'active', 'now', 'ago', 'minutes', 'hours', 'you', 'your',
    ]
    
    # Remove timestamps
    text = re.sub(r'\d{1,2}:\d{2}\s*[AP]M', '', text)
    text = re.sub(r'\d{1,2}:\d{2}', '', text)
    text = re.sub(r'\d{1,2}/\d{1,2}/\d{2}', '', text)
    text = re.sub(r'[A-Z][a-z]{2}\s*\d{1,2}', '', text)
    text = re.sub(r'\b\d+\s*(min|hour|day)s?\s*ago\b', '', text, flags=re.IGNORECASE)
    
    # Remove "You sent" or similar outgoing message indicators
    text = re.sub(r'^you\s+(sent|said|wrote|replied)', '', text, flags=re.IGNORECASE)
    
    # Split into words and filter
    words = text.split()
    cleaned_words = []
    
    for word in words:
        word = word.strip()
        if len(word) < 2:
            continue
        
        if word.lower() in ui_noise:
            continue
        
        # Skip if mostly symbols
        alpha_count = sum(c.isalnum() for c in word)
        if alpha_count < len(word) * 0.5:
            continue
        
        # Skip numbers only
        if word.isdigit():
            continue
        
        # Skip short fragments
        if len(word) <= 2 and not word.isalpha():
            continue
            
        cleaned_words.append(word)
    
    result = ' '.join(cleaned_words)
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


def is_valid_message(text):
    """Check if text is a valid incoming message."""
    if not text or len(text) < 5:
        return False
    
    words = text.split()
    if len(words) < 2:
        return False
    
    if len(text) < 15:
        return False
    
    alpha_count = sum(c.isalpha() for c in text)
    if alpha_count < len(text) * 0.6:
        return False
    
    # Skip if it sounds like a response (starts with common reply words)
    reply_starters = ['thanks', 'okay', 'sure', 'yes', 'no', 'lol', 'haha', 'ok']
    if words[0].lower() in reply_starters and len(words) < 5:
        return False
    
    return True


# ==============================================================================
# READ MESSAGE - FOCUS ON INCOMING MESSAGES
# ==============================================================================

def read_message():
    """Read incoming messages from the RIGHT side of chat (not sent messages)."""
    screenshot, screen_w, screen_h = capture_screen()

    # Focus on the RIGHT side of chat where incoming messages appear
    # Instagram DM layout: 
    # - Left side: your messages (right-aligned or colored differently)
    # - Right side: their messages (left-aligned, white background)
    
    # The incoming message area is on the RIGHT side of the chat
    chat_left = int(screen_w * 0.45)  # Middle of screen - focus on right side
    chat_right = int(screen_w * 0.92)
    chat_top = int(screen_h * 0.15)   # After header
    chat_bottom = int(screen_h * 0.82)  # Before input area
    
    chat_region = screenshot[chat_top:chat_bottom, chat_left:chat_right]
    
    if chat_region.size == 0:
        return ""
    
    gray = cv2.cvtColor(chat_region, cv2.COLOR_BGR2GRAY)
    
    # Try simple OCR first
    try:
        text = pytesseract.image_to_string(gray, config='--psm 6').strip()
        if text and len(text) > 10:
            return text
    except:
        pass
    
    # Try with threshold
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    try:
        text = pytesseract.image_to_string(binary, config='--psm 6').strip()
        if text and len(text) > 10:
            return text
    except:
        pass
    
    return ""


# ==============================================================================
# MAIN CONVERSATION LOOP
# ==============================================================================

def run_conversation_mode():
    """Stay on ONE conversation and maintain the chat."""
    
    print(f"\n{'='*60}")
    print("🤖 INSTAGRAM CONVERSATION BOT")
    print(f"{'='*60}")
    print()
    print("INSTRUCTIONS:")
    print("1. Open Instagram DMs in your browser")
    print("2. Click on the conversation you want to bot")
    print("3. The bot will read incoming messages and respond")
    print(f"4. Checking for new messages every {WAIT_TIME} seconds")
    print("5. Press Ctrl+C to stop")
    print()
    print("STARTING IN 5 SECONDS...")
    print(f"{'='*60}\n")
    
    time.sleep(5)
    
    # Track last message and last response
    last_message = ""
    last_response = ""
    last_response_time = 0
    
    cycle = 0
    while True:
        cycle += 1
        print(f"[{time.strftime('%H:%M:%S')}] Cycle #{cycle}")
        
        try:
            # Read current message from INCOMING message area
            current_msg = read_message()
            current_clean = clean_message_text(current_msg)
            
            if current_clean:
                print(f"  Read: '{current_clean[:40]}...'")
                
                # Check if it's a new, valid incoming message
                # And NOT the message we just sent
                is_new = current_clean != last_message
                is_not_our_response = current_clean != last_response
                is_valid = is_valid_message(current_clean)
                has_cooldown = time.time() - last_response_time > 8  # 8s cooldown
                
                if is_new and is_not_our_response and is_valid and has_cooldown:
                    print(f"  ✨ NEW INCOMING MESSAGE!")
                    last_message = current_clean
                    
                    # Get AI reply
                    reply = get_ai_reply(current_clean)
                    
                    if reply:
                        send_reply(reply)
                        last_response = clean_message_text(reply)
                        last_response_time = time.time()
                        print(f"  ✓ Sent: '{reply[:40]}...'")
                    else:
                        print(f"  Skipped: no reply generated")
                else:
                    if not is_new:
                        print(f"  - Same message as before")
                    elif not is_not_our_response:
                        print(f"  - That's our previous response")
                    elif not is_valid:
                        print(f"  - Message too short/invalid")
                    elif not has_cooldown:
                        print(f"  - Cooldown active")
            else:
                print(f"  (No incoming message detected)")
            
            # Wait before next check
            print(f"  Sleeping {WAIT_TIME}s...\n")
            time.sleep(WAIT_TIME)
            
        except KeyboardInterrupt:
            print("\n\n👋 Bot stopped by user!")
            break
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(WAIT_TIME)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    try:
        run_conversation_mode()
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped!")
    except Exception as e:
        print(f"Error: {e}")

