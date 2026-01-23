# Instagram DM Chatbot

Automated chatbot for Instagram direct messages that uses AI to understand context and generate intelligent responses.

## Features

✅ **Auto-monitors** Instagram DMs  
✅ **Reads conversation context** for accurate replies  
✅ **AI-powered responses** using GPT-3.5 Turbo  
✅ **Appears human-like** with natural delays and typing  
✅ **Handles multiple conversations** sequentially  
✅ **Customizable personality** via system prompt  

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

or manually:

```bash
pip install selenium webdriver-manager openai python-dotenv
```

### 2. Get OpenAI API Key

1. Go to https://platform.openai.com/api/keys
2. Create a new API key
3. Copy it

### 3. Create `.env` File

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 4. Run the Chatbot

```bash
python3 instagram_dm_chatbot.py
```

**What happens:**
1. Chrome opens automatically
2. Navigate to Instagram and log in (if needed)
3. The chatbot waits for incoming DMs
4. When a message arrives, it reads the conversation context
5. AI generates an intelligent response
6. Message is sent automatically
7. Repeats every 60 seconds

## How It Works

```
Incoming Message
    ↓
Read Conversation History (last 10 messages)
    ↓
Send to OpenAI with Context
    ↓
Generate Smart Response
    ↓
Send Reply (appears human-like)
    ↓
Wait & Check Again
```

## Customization

### Change Response Style

Edit the `SYSTEM_PROMPT` in `instagram_dm_chatbot.py`:

```python
SYSTEM_PROMPT = """You are a helpful assistant that...
- Be professional and concise
- Match the tone of the conversation
"""
```

### Adjust Timing

Change delay times:

```python
random_delay(min_seconds=1, max_seconds=3)  # Adjust min/max
```

### Change Check Interval

```python
time.sleep(60)  # Check every 60 seconds (adjust as needed)
```

## Troubleshooting

**"OPENAI_API_KEY not found"**
- Make sure `.env` file exists in the same directory
- Verify the API key is correct
- Restart the script

**Messages not being read**
- Instagram's DOM structure changes frequently
- Check browser developer tools to find the correct selectors
- Update the XPath selectors in the code

**Rate limiting from Instagram**
- Increase delays between messages
- Don't respond to too many conversations at once
- Add more randomization to appear human-like

## Risks & Disclaimers

⚠️ Use responsibly:
- Instagram may detect and ban automated accounts
- Only automate responses you would genuinely send
- Don't spam or harass users
- Comply with Instagram's Terms of Service
- Consider using on a test account first

## Files

- `instagram_dm_chatbot.py` - Main chatbot script
- `.env` - Configuration (API keys)
- `.env.example` - Example configuration

## License

For educational purposes only.
