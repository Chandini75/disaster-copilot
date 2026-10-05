# Disaster Response Copilot

An offline-first AI command center for disaster response. Volunteers send messy field reports (text, photo, voice), a local AI turns them into structured data, and the rescue team sees a live map, a ranked priority list, and automatic team assignments. It runs on one laptop with the Wi-Fi off.

## The problem
In floods and cyclones, rescue teams get scattered reports from many people, often when the network is down. Nobody sees the full picture, so help can go to the wrong place first.

## What it does
**Volunteer page** (`/volunteer.html`)
- Send a text report, a photo, a voice message, or any mix of the three.
- Set the location by tapping the map or using GPS.

**Rescue command center** (`/`)
- Live map and priority list of all reports, including photos, voice players and the transcribed words.
- Add rescue teams (name, capacity, location) by clicking the map.
- One click on **Dispatch teams** assigns teams to reports. Most urgent reports are served first, each by the nearest free team that has enough capacity. If no free team is big enough, the nearest one is sent and the report is flagged "backup needed".
- Mark reports resolved to free their team.

**AI pipeline (all local, no internet needed)**
1. Voice messages are turned into text by a local speech model (faster-whisper).
2. A local open-weight model (Gemma 3 4B, running through Ollama) reads the text and photo and extracts the problem type, urgency (1 to 5), number of people affected and a short summary. Reports can be in other languages, and the summary is written in English.
3. Reports about the same problem within 300 meters are merged into one entry, with the highest urgency and people count.

## Built with
- Python and FastAPI (backend)
- Ollama with Gemma 3 4B (open-weight language and vision model)
- faster-whisper, "small" model (offline speech-to-text)
- Leaflet (map, bundled locally)
- Plain HTML and JavaScript (frontend)

## How to run
1. Install [Python 3.10+](https://www.python.org) and [Ollama](https://ollama.com).
2. Download the AI model:
```
   ollama pull gemma3:4b
```
3. Get the code and install the tools:
```
   git clone https://github.com/Chandini75/disaster-copilot.git
   cd disaster-copilot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
```
4. Download the speech model once, while you are online (about 460 MB):
```
   python3 -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
```
5. Start the app (keep Ollama running):
```
   uvicorn main:app --reload
```
6. Open the two pages:
   - Command center: http://localhost:8000
   - Volunteer page: http://localhost:8000/volunteer.html

After steps 2 and 4, the whole pipeline works with the internet turned off. The first voice report after a restart is slow while the speech model loads.

## Quick demo
1. On the command center, click **Add rescue team** and click the map. Add two or three teams.
2. On the volunteer page, send a few reports from different spots (try a voice message with the text box empty).
3. Watch them appear on the command center, then click **Dispatch teams**.

## Changing the models
The language model name is set in `main.py` (`gemma3:4b`). Any Ollama model can be used, but image reading needs a model that supports images. The speech model size is set where `WhisperModel("small", ...)` is created.

## Limitations
- Reports and teams are stored in memory and are cleared when the server restarts.
- Small local models can make mistakes, so a human should check urgent cases.
- Dispatch is a simple greedy rule (urgency first, then nearest free team), not an optimal assignment.
- Map pictures come from OpenStreetMap and are cached by the browser, so open your area once online before going offline. Pins and the priority list work without them.
- Voice recording works on the laptop. Browsers block microphone access on plain `http` pages from other devices, so voice from phones was not set up. Text reports from phones on the same Wi-Fi worked in testing.
- Anyone who can reach the server can use it. There is no login, so only run it on a network you trust.

## Contributing
Ideas that would help: optimal team assignment, saving data to disk, better handling of unreliable AI answers, more languages, and an accuracy benchmark with test reports. Issues and pull requests are welcome.

## License
MIT. The AI models have their own licenses, so check the Gemma and Whisper terms before reusing them.
