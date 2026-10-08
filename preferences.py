"""玩家偏好与键位；仅正式入口加载磁盘，测试和检查工具默认隔离。"""
from collections import Counter
from dataclasses import dataclass, field
import json

import pygame

from localization import DEFAULT_LANGUAGE, TEXT
from settings import ROOT

PREFERENCES_PATH = ROOT / "user_settings.json"
DEFAULT_BINDINGS = {
    "move_up": pygame.K_w,
    "move_down": pygame.K_s,
    "move_left": pygame.K_a,
    "move_right": pygame.K_d,
    "missile": pygame.K_q,
    "arc": pygame.K_e,
    "support": pygame.K_x,
    "pause": pygame.K_ESCAPE,
}


def key_name(key):
    name = pygame.key.name(key)
    return name.upper() if len(name) == 1 or name.startswith("f") and name[1:].isdigit() else name.title()


def valid_key(key):
    try:
        return type(key) is int and key > 0 and bool(pygame.key.name(key))
    except (ValueError, OverflowError):
        return False


@dataclass
class Preferences:
    language: str = DEFAULT_LANGUAGE
    sfx_volume: float = .45
    music_volume: float = .35
    bindings: dict = field(default_factory=lambda: DEFAULT_BINDINGS.copy())
    path: object = None

    @classmethod
    def load(cls, path=PREFERENCES_PATH):
        result = cls(path=path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError):
            return result
        if not isinstance(data, dict):
            return result
        if isinstance(data.get("language"), str) and data["language"] in TEXT:
            result.language = data["language"]
        for name in ("sfx_volume", "music_volume"):
            value = data.get(name)
            if type(value) in (int, float) and 0 <= value <= 1:
                setattr(result, name, value)
        bindings = data.get("bindings")
        if isinstance(bindings, dict):
            for action in DEFAULT_BINDINGS:
                if valid_key(bindings.get(action)):
                    result.bindings[action] = bindings[action]
        return result

    def save(self):
        if self.path is None:
            return True
        data = {"language": self.language, "sfx_volume": self.sfx_volume,
                "music_volume": self.music_volume, "bindings": self.bindings}
        temporary = self.path.with_suffix(".json.tmp")
        try:
            temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            return False
        return True

    def reset_keys(self):
        # 原地更新，让输入状态引用的键位表始终有效。
        self.bindings.clear()
        self.bindings.update(DEFAULT_BINDINGS)

    def conflicts(self):
        counts = Counter(self.bindings.values())
        return {action for action, key in self.bindings.items() if counts[key] > 1}
