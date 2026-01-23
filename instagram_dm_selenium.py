#!/usr/bin/env python3
"""
Instagram DM Chatbot - Selenium-based (More Reliable)
Uses DOM access instead of OCR for reading/sending messages.

This is more reliable than pyautogui + OCR because it accesses
the actual page elements directly.
"""

import time
import random
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests


# ==============================================================================
# CONFIG
# ==============================================================================

# Ollama settings for AI responses
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"

# System prompt for AI
SYSTEM_PROMPT = """You are a friendly Instagram DM assistant. Reply briefly (under 150 chars), naturally, and helpful."""


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def random_delay(min_sec=1.5, max_sec=3.0):
    """Human-like random delay."""
    delay = random.uniform(min_sec, max_sec)
    print(f"   (delay {delay:.1f}s)")
    time.sleep(delay)


def create_driver():
    """Create Chrome driver for Instagram automation."""
    print("Starting Chrome...")
    
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.implicitly_wait(5)
        print("✓ Chrome started!")
        return driver
    except Exception as e:
        print(f"Chrome error: {e}")
        return None


def get_ai_response(message_text):
    """Get AI response from Ollama."""
    if not message_text or len(message_text.strip()) < 3:
        return None
    
    prompt = f"{SYSTEM_PROMPT}\n\nUser said: {message_text.strip()}\n\nYour reply:"
    
    try:
        resp = requests.post(
            OLLAMA_ENDPOINT,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        resp.raise_for_status()
        reply = resp.json().get("response", "").strip()
        if reply and len(reply) > 2:
            return reply
        return "Thanks for your message! 🙏"
    except Exception as e:
        print(f"  AI error: {e}")
        return "Thanks for your message!"


# ==============================================================================
# DM FUNCTIONS
# ==============================================================================

def navigate_to_dms(driver):
    """Navigate to Instagram DMs."""
    print("\nNavigating to DMs...")
    driver.get("https://www.instagram.com/direct/inbox/")
    random_delay(3, 5)
    
    # Wait for inbox to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@role,'button')]//span[contains(text(),'Message')]"))
        )
        print("✓ Inbox loaded")
        return True
    except:
        print("⚠ Inbox may not have loaded properly")
        return True  # Continue anyway


def get_conversation_list(driver):
    """Get list of conversation elements from DM sidebar."""
    conversations = []
    
    # Try multiple selectors for conversation list (updated for current Instagram)
    selectors = [
        # Main conversation list - div elements with click handlers
        "//div[contains(@class, '_aagv')]",
        "//div[contains(@class, '_aagz')]",
        # Links to conversations
        "//a[contains(@href, '/direct/t/')]",
        # List items in conversation list
        "//li[contains(@class, '_aagx')]",
        # Any clickable div in the sidebar
        "//div[@role='button'][contains(@tabindex, '0')]",
        # Generic conversation element
        "//*[contains(@class, 'conversation')]",
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                for elem in elements[:15]:  # Max 15 conversations
                    try:
                        text = elem.text.strip()
                        # Include if it has meaningful text (username or message)
                        if text and len(text) > 1:
                            conversations.append(elem)
                    except:
                        pass
                if conversations:
                    print(f"  Found {len(conversations)} potential conversations")
                    break
        except:
            continue
    
    # Remove duplicates based on location
    seen_positions = set()
    unique_conversations = []
    for conv in conversations:
        try:
            loc = (conv.location['x'], conv.location['y'])
            if loc not in seen_positions:
                seen_positions.add(loc)
                unique_conversations.append(conv)
        except:
            unique_conversations.append(conv)
    
    print(f"  Unique conversations: {len(unique_conversations)}")
    return unique_conversations


def click_conversation(driver, conversation):
    """Click on a conversation to open it."""
    try:
        # Scroll into view and click using JavaScript
        driver.execute_script("arguments[0].scrollIntoView(true);", conversation)
        random_delay(0.5, 1)
        
        # Try regular click first
        try:
            conversation.click()
        except:
            # Fallback to JavaScript click
            driver.execute_script("arguments[0].click();", conversation)
        
        print("  Opened conversation")
        random_delay(1.5, 2.5)
        return True
    except Exception as e:
        print(f"  Error opening conversation: {e}")
        return False


def read_current_message(driver):
    """Read the current message in the open conversation."""
    # Wait for messages to load
    random_delay(1, 2)
    
    # Try multiple selectors for message bubbles (updated for current Instagram)
    selectors = [
        # Main message text spans/divs
        "//span[contains(@class, '_aacl')]",
        "//div[contains(@class, '_aacl')]",
        "//div[contains(@class, '_aacu')]",
        "//span[contains(@class, '_aacw')]",
        # Message content in paragraphs
        "//p[contains(@class, '_aacl')]",
        # Last message (newer Instagram)
        "(//div[contains(@class, '_aacl')])[last()]",
        # Message bubbles
        "//div[contains(@class, 'message')]",
        "//div[contains(@class, '_aaz7')]",
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                # Get the last few messages (most recent)
                for elem in reversed(elements[-10:]):
                    text = elem.text.strip()
                    if text and len(text) > 2:
                        # Filter out UI text
                        ui_words = ['message', 'send', 'like', 'react', 'emoji', 'send message']
                        text_lower = text.lower()
                        if not any(word in text_lower for word in ui_words):
                            # Additional check: not just numbers or symbols
                            if sum(c.isalnum() for c in text) > len(text) * 0.3:
                                print(f"  Read message: '{text[:80]}...'")
                                return text
        except:
            continue
    
    # Try getting all text from the chat area as fallback
    try:
        chat_area = driver.find_element(By.XPATH, "//div[contains(@class, '_aa_y')]//div[contains(@class, '_aa_z')]")
        all_text = chat_area.text
        if all_text and len(all_text) > 5:
            lines = all_text.split('\n')
            for line in reversed(lines):
                line = line.strip()
                if len(line) > 3:
                    print(f"  Chat area text: '{line[:60]}...'")
                    return line
    except:
        pass
    
    print("  No message found")
    return None


def send_message(driver, message_text):
    """Send a message in the current conversation."""
    if not message_text:
        return False
    
    print(f"  Sending: '{message_text[:50]}...'")
    
    # Try to find message input
    input_selectors = [
        "//textarea[contains(@placeholder, 'Message')]",
        "//div[contains(@aria-label, 'Message')]",
        "//p[contains(@aria-label, 'Message')]",
        "//div[@role='textbox']",
        "//textarea[@dir='auto']",
        "//div[contains(@style, 'resize')]",
    ]
    
    input_elem = None
    for selector in input_selectors:
        try:
            elem = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
            input_elem = elem
            print(f"  Found input field")
            break
        except:
            continue
    
    if not input_elem:
        print("  Could not find message input")
        return False
    
    # Type the message
    try:
        input_elem.clear()
        
        # Type character by character for human-like feel
        for char in message_text:
            input_elem.send_keys(char)
            time.sleep(random.uniform(0.02, 0.08))
        
        random_delay(0.3, 0.6)
        
        # Press enter to send
        input_elem.send_keys("\n")
        
        print("  ✓ Message sent!")
        return True
        
    except Exception as e:
        print(f"  Error sending message: {e}")
        return False


def go_back_to_inbox(driver):
    """Go back to the inbox/conversation list."""
    try:
        # Look for back button
        back_selectors = [
            "//a[contains(@href, '/direct/inbox/')]",
            "//div[contains(@aria-label, 'Back')]",
            "//button[contains(@aria-label, 'Back')]",
        ]
        
        for selector in back_selectors:
            try:
                back_btn = driver.find_element(By.XPATH, selector)
                back_btn.click()
                print("  Back to inbox")
                random_delay(1.5, 2.5)
                return True
            except:
                continue
        
        # Fallback: navigate directly
        driver.get("https://www.instagram.com/direct/inbox/")
        random_delay(2, 4)
        return True
        
    except Exception as e:
        print(f"  Error going back: {e}")
        return False


# ==============================================================================
# MAIN BOT
# ==============================================================================

def run_bot():
    """Main bot loop."""
    print("=" * 60)
    print("INSTAGRAM DM CHATBOT - SELENIUM VERSION")
    print("=" * 60)
    
    driver = create_driver()
    if not driver:
        print("Failed to start Chrome")
        return
    
    try:
        # Navigate to DMs
        navigate_to_dms(driver)
        
        conversations_processed = 0
        max_conversations = 10
        
        while conversations_processed < max_conversations:
            print(f"\n--- Processing conversation {conversations_processed + 1}/{max_conversations} ---")
            
            # Get conversation list
            conversations = get_conversation_list(driver)
            
            if not conversations:
                print("No more conversations found")
                break
            
            # Get the next unprocessed conversation
            if conversations_processed < len(conversations):
                conv = conversations[conversations_processed]
                
                # Open conversation
                if not click_conversation(driver, conv):
                    conversations_processed += 1
                    continue
                
                # Read message
                message = read_current_message(driver)
                
                if message and len(message) > 3:
                    # Get AI response
                    reply = get_ai_response(message)
                    
                    if reply:
                        # Send reply
                        send_message(driver, reply)
                    else:
                        print("  No reply generated")
                else:
                    print("  No valid message to reply to")
                
                # Go back to inbox
                random_delay(1, 2)
                go_back_to_inbox(driver)
                
                conversations_processed += 1
            else:
                break
            
            # Delay between conversations
            random_delay(2, 4)
        
        print(f"\n✓ Done! Processed {conversations_processed} conversations")
        
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        try:
            driver.quit()
        except:
            pass


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    run_bot()

