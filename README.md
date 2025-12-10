# Voice + Manual Calculator (Flask)

This small project runs a local Flask web app that provides a manual calculator UI and voice input using the browser's Web Speech API.

Features
- Manual calculator keypad and expression input
- Voice input (browser-side) using Web Speech API
- Text-to-speech result (browser-side)
- Safe arithmetic evaluation on the server

Requirements
- Python 3.8+
- `pip` to install dependencies

Quick start (PowerShell)

```powershell
cd C:\Users\Admin\Desktop\web
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:8501 in your browser (Chrome or Edge recommended for speech recognition).

Notes
- Speech recognition uses the browser's built-in API; it does not send audio to the server.
- The server evaluates arithmetic expressions safely using AST parsing. Do not expose this service publicly without additional safeguards.

Next steps (optional)
- Add history of operations
- Add more natural language parsing and error messages
- Persist logs or add authentication if you plan to deploy
<img width="1811" height="850" alt="image" src="https://github.com/user-attachments/assets/96e69585-bf2e-4681-831a-e9a484f251db" />
