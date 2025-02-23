from dataclasses import dataclass
from Common.sharedImports import *

@dataclass
class Fish:
    x: float
    y: float
    direction: float
    group_name: str
    lifetime: float
    current_frame: int
    animation_time: float
    speed: float
    name: str
    frames: List[pygame.Surface]