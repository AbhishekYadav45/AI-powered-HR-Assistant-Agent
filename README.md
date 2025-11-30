# AI Oracle HR Assistant (AI Decision Version)

## Overview
This project lets HR users query Oracle DB using natural language. 
It uses OpenAI to translate text into SQL, fetches results, generates dynamic reports, 
and then uses OpenAI to interpret instructions for sending emails.

## Features
- Natural language to Oracle SQL via OpenAI
- AI interprets follow-up instructions to decide recipients
- Preview decision in UI before sending
- Manual confirmation required

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Update `config.py` with your Oracle DB, OpenAI, and email credentials.
3. Run the app:
   ```bash
   python app.py
   ```
