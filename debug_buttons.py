#!/usr/bin/env python3
"""Quick debug script to check profile page buttons"""
import sys
sys.path.insert(0, '/Users/saatviksantosh/Downloads/instabot-main')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

print("Starting Chrome...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://www.instagram.com/dhruva_valluru123/")

print("Waiting 15 seconds for page to load...")
time.sleep(15)

print("\nAll buttons on page:")
buttons = driver.find_elements(By.TAG_NAME, "button")
print(f"Total buttons: {len(buttons)}\n")

for i, btn in enumerate(buttons):
    text = btn.text.strip()
    aria = btn.get_attribute("aria-label")
    role = btn.get_attribute("role")
    print(f"[{i}] Text: '{text}' | Aria: '{aria}' | Role: '{role}'")
    if i >= 20:
        print("...")
        break

driver.quit()
