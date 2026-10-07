"""可重复的原创合成音效制作；运行游戏不依赖此工具。"""
from array import array
import math
from pathlib import Path
import random
import wave

OUTPUT = Path(__file__).resolve().parents[1] / "assets/audio/sfx"
RATE = 44100
SPECS = {"bullet": (.05, 1100), "missile": (.18, 180), "explosion": (.35, 70),
         "arc": (.12, 1600), "pickup": (.15, 620), "hurt": (.15, 100),
         "lock": (.10, 900), "support": (.4, 90), "phase": (.5, 360)}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(701)
    for name, (duration, frequency) in SPECS.items():
        samples = array("h")
        for index in range(round(RATE * duration)):
            t = index / RATE
            progress = t / duration
            envelope = min(1, t / .003) * (1 - progress) ** 1.7
            sweep = 1.6 * t / duration if name in ("pickup", "lock") else -.45 * t / duration
            tone = math.sin(2 * math.pi * frequency * (t + sweep * t / 2))
            noise = rng.uniform(-1, 1)
            blend = .8 if name in ("explosion", "support", "arc") else .12
            sample = .32 * envelope * ((1 - blend) * tone + blend * noise)
            samples.append(round(max(-.95, min(.95, sample)) * 32767))
        with wave.open(str(OUTPUT / f"{name}.wav"), "wb") as output:
            output.setparams((1, 2, RATE, len(samples), "NONE", "not compressed"))
            output.writeframes(samples.tobytes())
        print(f"{name}: {duration}s, 44100Hz mono PCM16")


if __name__ == "__main__":
    main()
