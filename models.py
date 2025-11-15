# models.py

from dataclasses import dataclass

@dataclass
class Seminar:
    id: int
    date: str
    time: str
    speaker_id: int
    topic: str