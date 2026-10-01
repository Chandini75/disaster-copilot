from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import requests, json

app = FastAPI()
reports = []

class Report(BaseModel):
    text: str
    lat: float
    lng: float
    image: Optional[str] = None

PROMPT = """You extract data from disaster reports. If a photo is attached, use it too.
Return ONLY JSON with keys:
problem_type (flood, medical, trapped, road_blocked, fire, other),
urgency (integer 1-5, 5 is most urgent),
people_affected (integer, 0 if unknown),
summary (max 12 words).
Report: """

def extract(text, image=None):
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
    data = extract(rep.text, rep.image)
    data.update(lat=rep.lat, lng=rep.lng, text=rep.text)
    urg = int(data.get("urgency") or 1)
    ppl = int(data.get("people_affected") or 1)
    data["score"] = urg * max(ppl, 1)
    reports.append(data)
    return data

@app.get("/reports")
def get_reports():
    return sorted(reports, key=lambda r: r["score"], reverse=True)

app.mount("/", StaticFiles(directory="static", html=True), name="static")