# Conversational BI Assistant (Free, Local)

## Requirements
- Python 3.10+
- Ollama installed (https://ollama.com/download)
- Northwind SQLite database at: db/northwind.db

## Setup
1. Create venv and install:
   - pip install -r requirements.txt
2. Pull model:
   - ollama pull qwen2.5:7b-instruct
3. Create .env (see .env.example)
4. Run:
   - streamlit run app/Home.py