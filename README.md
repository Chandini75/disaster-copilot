# Disaster Response Copilot

An offline-first AI copilot for disaster response. It turns messy field reports (text and photos) into a live priority map, and it works with no internet.

## The problem
In floods and cyclones, rescue teams get scattered reports from many people, often when the network is down. Nobody sees the full picture, so help can go to the wrong place first.

## What it does
- Volunteers submit a short report, an optional photo, and a location on the map.
- A local open-weight AI model (Gemma 3 4B, running through Ollama) extracts the problem type, urgency, number of people affected and a short summary.
- Reports appear as colored pins on a map and in one ranked priority list.
- Duplicate reports about the same problem within 300 meters are merged into one entry, with the highest urgency and people count.
- Everything runs on a laptop with Wi-Fi off.

## Built with
- Python and FastAPI (backend)
- Ollama with Gemma 3 4B (local open-weight model)
- Leaflet (map, bundled locally)
- Plain HTML and JavaScript (frontend)

## How to run
1. Install [Python 3.10+](https://www.python.org) and [Ollama](https://ollama.com).
2. Download the model:
```
   ollama pull gemma3:4b
```
3. Get the code and install the tools:
```
   git clone https://github.com/yourname/disaster-copilot.git
   cd disaster-copilot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
```
4. Start the app (keep Ollama running):
```
   uvicorn main:app --reload
```
5. Open http://localhost:8000, click the map to set a location, type a report, and submit.

## Changing the model
The model name is set in `main.py`. Any Ollama model can be used. Image reading needs a model that supports images.

## Limitations
- Reports are stored in memory and clear when the server restarts.
- Small local models can make mistakes, so a human should check urgent cases.
- Map pictures are cached by the browser, so open your area once online before going offline.

## License
MIT. The AI model has its own license, see the Gemma terms.