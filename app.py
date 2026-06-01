"""
Serveur BirdNET pour Natura App.
Déployé sur Railway.app — wraps birdnetlib (Cornell BirdNET-Analyzer).
"""
import os
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer

app = FastAPI(title="BirdNET Server — Natura")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Chargement du modèle au démarrage (une seule fois)
print("Chargement du modèle BirdNET…")
analyzer = Analyzer()
print("Modèle BirdNET prêt.")


@app.get("/health")
def health():
    return {"status": "ok", "model": "BirdNET-Analyzer"}


@app.post("/analyze")
async def analyze(
    audio: UploadFile = File(...),
    lat: float = Form(None),
    lon: float = Form(None),
    week: int = Form(-1),
    min_conf: float = Form(0.1),
    locale: str = Form("fr"),
):
    # Sauvegarder le fichier audio temporairement
    suffix = os.path.splitext(audio.filename or ".wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        recording = Recording(
            analyzer,
            tmp_path,
            lat=lat if lat is not None else 0,
            lon=lon if lon is not None else 0,
            week_48=week,
            min_conf=min_conf,
        )
        recording.analyze()

        detections = [
            {
                "scientific_name": d["scientific_name"],
                "common_name": d["common_name"],
                "confidence": round(d["confidence"], 4),
                "start_time": d["start_time"],
                "end_time": d["end_time"],
            }
            for d in recording.detections
        ]

        # Tri par confiance décroissante
        detections.sort(key=lambda x: x["confidence"], reverse=True)

        return {"detections": detections, "total": len(detections)}

    finally:
        os.unlink(tmp_path)
