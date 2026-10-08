"""从程序目录读取独立透明精灵、背景和声音；缓存显示数据。"""
import pygame

from settings import ROOT
from art import icon


class Resources:
    # 独立文件不依赖生成图集的网格精度；目标尺寸为外接框，不拉伸船体。
    sprite_sizes = {"player": (64, 64), "scout": (48, 48), "shooter": (64, 64),
                    "heavy": (96, 96), "boss": (384, 192),
                    "meteor_small": (64, 64), "meteor_large": (96, 96)}
    icon_sizes = {"health": 48, "missile": 48, "arc": 48, "support": 48,
                  "crosshair": 32, "lock": 48, "explosion": 80, "pulse": 18}
    sound_names = ("bullet", "missile", "explosion", "arc", "pickup", "hurt", "lock", "support", "phase")

    def __init__(self):
        self.images = {}
        for name, size in self.sprite_sizes.items():
            path = ROOT / f"assets/images/craft/{name}.png"
            if not path.is_file():
                raise FileNotFoundError(f"缺少必需精灵：{path}")
            source = pygame.image.load(str(path))
            # 母舰生成稿忠实沿用参考图的朝下舰首；加载时统一成朝上原始朝向。
            if name == "boss":
                source = pygame.transform.rotate(source, 180)
            if not source.get_flags() & pygame.SRCALPHA:
                raise ValueError(f"精灵必须含透明通道：{path}")
            bounds = source.get_bounding_rect(min_alpha=8)
            if not bounds.width or not bounds.height:
                raise ValueError(f"精灵不能为空：{path}")
            source = source.subsurface(bounds)
            factor = min((size[0] - 4) / bounds.width, (size[1] - 4) / bounds.height)
            fitted = pygame.transform.smoothscale(source,
                       (max(1, round(bounds.width * factor)), max(1, round(bounds.height * factor))))
            canvas = pygame.Surface(size, pygame.SRCALPHA)
            canvas.blit(fitted, fitted.get_rect(center=canvas.get_rect().center))
            self.images[name] = canvas
        self.images.update({name: icon(name, size) for name, size in self.icon_sizes.items()})
        path = ROOT / "assets/images/space.png"
        if not path.is_file():
            raise FileNotFoundError(f"缺少必需星空背景：{path}")
        self.background = pygame.image.load(str(path))
        self.scaled_images = {}
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

    def scaled(self, name, size):
        key = (name, size)
        if key not in self.scaled_images:
            self.scaled_images[key] = pygame.transform.smoothscale(self.images[name], size)
        return self.scaled_images[key]

    def play(self, name):
        if self.audio_available and name in self.sounds:
            self.channels[name].set_volume(self.sfx_volume)
            self.channels[name].play(self.sounds[name])

    def set_volumes(self, sfx, music):
        self.sfx_volume, self.music_volume = sfx, music
        if self.audio_available:
            pygame.mixer.music.set_volume(music)
