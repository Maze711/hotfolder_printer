from dataclasses import dataclass


@dataclass
class Placement:
    x: int
    y: int
    width: int
    height: int
    mode: str


@dataclass
class DetectedRegion:
    x: int
    y: int
    width: int
    height: int
    pixels: int
