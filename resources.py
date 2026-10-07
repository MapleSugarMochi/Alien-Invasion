"""从程序目录读取精灵图集和声音；缓存显示数据，不修改游戏规则。"""
import pygame

from settings import ROOT


class Resources:
    # 图集由 imagegen 制作；这些矩形依据实际生成的 1280 方图核对。
    regions = {
        "player": ((0, 0, 320, 320), (64, 64)),
        "scout": ((320, 0, 320, 320), (48, 48)),
        "shooter": ((640, 0, 304, 320), (64, 64)),
        "heavy": ((944, 0, 336, 320), (96, 96)),
        "boss": ((0, 320, 744, 320), (256, 160)),
        "meteor_small": ((752, 336, 208, 304), (64, 64)),
        "meteor_large": ((968, 320, 312, 320), (96, 96)),
        "health": ((0, 640, 320, 320), (48, 48)),
        "missile": ((320, 640, 320, 320), (48, 48)),
        "arc": ((640, 640, 320, 320), (48, 48)),
        "support": ((960, 640, 320, 320), (48, 48)),
        "crosshair": ((0, 960, 320, 320), (32, 32)),
        "lock": ((320, 960, 320, 320), (48, 48)),
        "explosion": ((640, 960, 320, 320), (80, 80)),
        "pulse": ((960, 960, 320, 320), (12, 18)),
    }
    sound_names = ("bullet", "missile", "explosion", "arc", "pickup", "hurt", "lock", "support", "phase")

    def __init__(self):
        path = ROOT / "assets/images/sprite-atlas.png"
        if not path.is_file():
            raise FileNotFoundError(f"缺少必需精灵图集：{path}")
        atlas = pygame.image.load(str(path))
        if atlas.get_width() != atlas.get_height() or atlas.get_width() < 512:
            raise ValueError(f"精灵图集必须为不小于 512 的正方形：{path}")
        # 生成工具实际输出 1254×1254；按 1280 参考布局映射，仅在运行时缩放。
        atlas = pygame.transform.smoothscale(atlas, (1280, 1280))
        self.images = {name: pygame.transform.smoothscale(atlas.subsurface(rect), size)
                       for name, (rect, size) in self.regions.items()}
        self.rotations = {}
        self.sounds = {}
        self.audio_available = pygame.mixer.get_init() is not None
        self.sfx_volume, self.music_volume = .45, .35
        self.music_file = None
        self.warnings = []
        for name in self.sound_names:
            sound_path = ROOT / f"assets/audio/sfx/{name}.wav"
            if not sound_path.is_file():
                raise FileNotFoundError(f"缺少必需音效：{sound_path}")
            if self.audio_available:
                self.sounds[name] = pygame.mixer.Sound(str(sound_path))
        if self.audio_available:
            pygame.mixer.set_num_channels(len(self.sound_names))
            # 每类独占一个通道，连发只替换同类声音，不无限叠加。
            self.channels = {name: pygame.mixer.Channel(i) for i, name in enumerate(self.sound_names)}
            music = ROOT / "assets/audio/music/bgm.ogg"
            if music.is_file():
                try:
                    pygame.mixer.music.load(str(music))
                    pygame.mixer.music.play(-1)
                    self.music_file = music
                except pygame.error as error:
                    self.warnings.append(f"BGM 无法加载，继续无音乐运行：{error}")

    def sprite(self, name, angle=0):
        # 只缓存整数角度，不让转向逐帧产生无界缓存。
        key = (name, round(angle) % 360)
        if key not in self.rotations:
            self.rotations[key] = pygame.transform.rotate(self.images[name], key[1])
        return self.rotations[key]

    def play(self, name):
        if self.audio_available and name in self.sounds:
            self.channels[name].set_volume(self.sfx_volume)
            self.channels[name].play(self.sounds[name])

    def set_volumes(self, sfx, music):
        self.sfx_volume, self.music_volume = sfx, music
        if self.audio_available:
            pygame.mixer.music.set_volume(music)
