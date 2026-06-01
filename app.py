import os
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BirdNET Server — Natura")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST"], allow_headers=["*"])

# Chargement lazy — au premier appel, pas au démarrage
_analyzer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        from birdnetlib.analyzer import Analyzer
        _analyzer = Analyzer()
    return _analyzer

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze")
async def analyze(
    audio: UploadFile = File(...),
    lat: float = Form(None),
    lon: float = Form(None),
    week: int = Form(-1),
    min_conf: float = Form(0.1),
):
    from birdnetlib import Recording
    suffix = os.path.splitext(audio.filename or ".wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        recording = Recording(get_analyzer(), tmp_path,
            lat=lat or 0, lon=lon or 0, week_48=week, min_conf=min_conf)
        recording.analyze()
        detections = sorted([{
            "scientific_name": d["scientific_name"],
            "common_name": d["common_name"],
            "confidence": round(d["confidence"], 4),
            "start_time": d["start_time"],
            "end_time": d["end_time"],
        } for d in recording.detections], key=lambda x: -x["confidence"])
        return {"detections": detections, "total": len(detections)}
    finally:
        os.unlink(tmp_path)
