from dataclasses import dataclass
from Common.sharedImports import *

@dataclass
class Fish:
    x: float
    y: float
    direction: float
    genesis_pond: str
    lifetime: float
    current_frame: int
    animation_time: float
    speed: float
    id: str
    frames: List[pygame.Surface]