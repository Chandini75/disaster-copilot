from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import requests, json, math, base64, tempfile, os

app = FastAPI()
reports = []
teams = []
next_report_id = 1
next_team_id = 1
whisper_model = None


class Report(BaseModel):
    text: str = ""
    lat: float
    lng: float
    image: Optional[str] = None
    audio: Optional[str] = None

class Team(BaseModel):
    name: str
    lat: float
    lng: float
    capacity: int


def distance_m(lat1, lng1, lat2, lng2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def transcribe(audio_data_url):
    """Turn a voice message into text, fully offline."""
    global whisper_model
    try:
        from faster_whisper import WhisperModel
        if whisper_model is None:
            whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
        b64 = audio_data_url.split(",", 1)[1]
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as f:
            f.write(base64.b64decode(b64))
            path = f.name
        try:
            segments, info = whisper_model.transcribe(path)
            return " ".join(s.text.strip() for s in segments).strip()
        finally:
            os.remove(path)
    except Exception as e:
        print("Transcription failed:", e)
        return ""


PROMPT = """You extract data from disaster reports. If a photo is attached, use it too.
The report may be in any language (for example Tamil or Hindi). Always answer in English.
Return ONLY JSON with keys:
problem_type (flood, medical, trapped, road_blocked, fire, other),
urgency (integer 1-5, 5 is most urgent),
people_affected (integer, 0 if unknown),
summary (max 12 words).
Report: """


def extract(text, image=None):
    if not text.strip() and not image:
        return {"problem_type": "other", "urgency": 3, "people_affected": 0,
                "summary": "Voice message only - listen to the audio"}
    msg = {"role": "user", "content": PROMPT + text}
    if image:
        msg["images"] = [image]
    r = requests.post("http://localhost:11434/api/chat", json={
        "model": "gemma3:4b",
        "messages": [msg],
        "format": "json",
        "stream": False,
    })
    return json.loads(r.json()["message"]["content"])


@app.post("/report")
def add_report(rep: Report):
    global next_report_id
    transcript = transcribe(rep.audio) if rep.audio else ""
    full_text = rep.text
    if transcript:
        full_text = (rep.text + "\nVoice message: " + transcript).strip()

    data = extract(full_text, rep.image)
    urg = min(max(to_int(data.get("urgency"), 1), 1), 5)
    ppl = max(to_int(data.get("people_affected"), 0), 0)
    ptype = data.get("problem_type") or "other"

    new_texts = []
    if rep.text:
        new_texts.append(rep.text)
    if transcript:
        new_texts.append("🎤 " + transcript)

    # merge with an existing report about the same problem within 300 m
    for old in reports:
        if (old["status"] != "resolved" and old["problem_type"] == ptype
                and distance_m(old["lat"], old["lng"], rep.lat, rep.lng) < 300):
            old["count"] += 1
            old["urgency"] = max(old["urgency"], urg)
            old["people_affected"] = max(old["people_affected"], ppl)
            old["score"] = old["urgency"] * max(old["people_affected"], 1) + old["count"]
            old["texts"].extend(new_texts)
            if rep.image and not old.get("image"):
                old["image"] = rep.image
            if rep.audio and not old.get("audio"):
                old["audio"] = rep.audio
            return old

    report = {
        "id": next_report_id,
        "problem_type": ptype,
        "urgency": urg,
        "people_affected": ppl,
        "summary": data.get("summary") or "No summary",
        "lat": rep.lat,
        "lng": rep.lng,
        "texts": new_texts,
        "image": rep.image,
        "audio": rep.audio,
        "count": 1,
        "score": urg * max(ppl, 1),
        "status": "new",
        "team_id": None,
    }
    next_report_id += 1
    reports.append(report)
    return report


@app.get("/reports")
def get_reports():
    active = [r for r in reports if r["status"] != "resolved"]
    return sorted(active, key=lambda r: r["score"], reverse=True)


@app.post("/team")
def add_team(t: Team):
    global next_team_id
    team = {"id": next_team_id, "name": t.name, "lat": t.lat, "lng": t.lng,
            "capacity": t.capacity, "report_id": None}
    next_team_id += 1
    teams.append(team)
    return team


@app.get("/teams")
def get_teams():
    return teams


@app.post("/dispatch")
def dispatch():
    free = [t for t in teams if t["report_id"] is None]
    waiting = sorted([r for r in reports if r["status"] == "new"],
                     key=lambda r: r["score"], reverse=True)
    assigned = 0
    for r in waiting:
        if not free:
            break
        need = max(r["people_affected"], 1)
        fits = [t for t in free if t["capacity"] >= need]
        pool = fits if fits else free
        best = min(pool, key=lambda t: distance_m(t["lat"], t["lng"], r["lat"], r["lng"]))
        r["status"] = "assigned"
        r["team_id"] = best["id"]
        r["distance_m"] = round(distance_m(best["lat"], best["lng"], r["lat"], r["lng"]))
        r["backup_needed"] = not fits
        best["report_id"] = r["id"]
        free.remove(best)
        assigned += 1
    return {"assigned": assigned}


@app.post("/resolve/{report_id}")
def resolve(report_id: int):
    for r in reports:
        if r["id"] == report_id:
            r["status"] = "resolved"
    for t in teams:
        if t["report_id"] == report_id:
            t["report_id"] = None
    return {"ok": True}


@app.post("/reset")
def reset():
    reports.clear()
    for t in teams:
        t["report_id"] = None
    return {"ok": True}


@app.post("/team/{team_id}/remove")
def remove_team(team_id: int):
    for t in teams:
        if t["id"] == team_id:
            if t["report_id"] is not None:
                for r in reports:
                    if r["id"] == t["report_id"]:
                        r["status"] = "new"
                        r["team_id"] = None
            teams.remove(t)
            break
    return {"ok": True}


@app.post("/teams/clear")
def clear_teams():
    teams.clear()
    for r in reports:
        if r["status"] == "assigned":
            r["status"] = "new"
            r["team_id"] = None
    return {"ok": True}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
