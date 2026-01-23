#!/bin/bash
# Setup script for Instagram DM Chatbot

echo "Instagram DM Chatbot Setup"
echo "=========================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your OpenAI API key"
    echo "   Get it from: https://platform.openai.com/api/keys"
    echo ""
    echo "Then run again:"
    echo "   python3 instagram_dm_chatbot.py"
else
    echo "✓ .env file exists"
fi

# Check if dependencies are installed
echo ""
echo "Checking dependencies..."
python3 -c "import selenium; print('✓ selenium installed')" 2>/dev/null || echo "✗ selenium not installed"
python3 -c "import openai; print('✓ openai installed')" 2>/dev/null || echo "✗ openai not installed"
python3 -c "import dotenv; print('✓ python-dotenv installed')" 2>/dev/null || echo "✗ python-dotenv not installed"

echo ""
echo "Ready! Run the chatbot with:"
echo "   python3 instagram_dm_chatbot.py"
