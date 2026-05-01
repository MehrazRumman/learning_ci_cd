import pygame
import random
import math
import sys
from dataclasses import dataclass, field
from typing import List

# ── Init ──────────────────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

W, H = 900, 700
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("✦ NEON BLASTER ✦")
clock = pygame.time.Clock()

# ── Palette ───────────────────────────────────────────────────────────────────
BLACK   = (0,   0,   0)
BG      = (4,   4,  18)
CYAN    = (0, 255, 255)
MAGENTA = (255,  0, 200)
YELLOW  = (255, 230,  0)
GREEN   = (0,  255, 100)
WHITE   = (255, 255, 255)
ORANGE  = (255, 140,   0)
RED     = (255,  50,  50)
PURPLE  = (160,  40, 255)
DIM     = (20,  20,  50)

# ── Fonts ─────────────────────────────────────────────────────────────────────
try:
    FONT_BIG   = pygame.font.SysFont("couriernew", 52, bold=True)
    FONT_MED   = pygame.font.SysFont("couriernew", 28, bold=True)
    FONT_SMALL = pygame.font.SysFont("couriernew", 18)
except:
    FONT_BIG   = pygame.font.SysFont(None, 52)
    FONT_MED   = pygame.font.SysFont(None, 28)
    FONT_SMALL = pygame.font.SysFont(None, 18)

# ── Sound generator ───────────────────────────────────────────────────────────
def make_sound(freq, duration_ms, wave="sine", volume=0.3):
    sr = 44100
    frames = int(sr * duration_ms / 1000)
    buf = bytearray(frames * 2)
    for i in range(frames):
        t = i / sr
        fade = min(1.0, (frames - i) / (frames * 0.3))
        if wave == "sine":
            v = math.sin(2 * math.pi * freq * t)
        elif wave == "square":
            v = 1 if math.sin(2 * math.pi * freq * t) > 0 else -1
        elif wave == "noise":
            v = random.uniform(-1, 1)
        sample = int(v * fade * volume * 32767)
        sample = max(-32768, min(32767, sample))
        buf[i*2]   = sample & 0xFF
        buf[i*2+1] = (sample >> 8) & 0xFF
    sound = pygame.sndarray.make_sound(
        __import__("numpy").frombuffer(bytes(buf), dtype=__import__("numpy").int16)
    )
    return sound

try:
    import numpy as np
    SND_SHOOT   = make_sound(880,  80,  "sine",   0.15)
    SND_EXPLODE = make_sound(120,  300, "noise",  0.25)
    SND_HIT     = make_sound(440,  150, "square", 0.2)
    SND_LEVEL   = make_sound(660,  500, "sine",   0.3)
    SND_DIE     = make_sound(80,   600, "noise",  0.3)
    SOUND_ON = True
except:
    SOUND_ON = False
    class DummySound:
        def play(self): pass
    SND_SHOOT = SND_EXPLODE = SND_HIT = SND_LEVEL = SND_DIE = DummySound()

def play(snd):
    if SOUND_ON:
        snd.play()

# ── Helpers ───────────────────────────────────────────────────────────────────
def glow_circle(surf, color, pos, radius, alpha=60):
    glow = pygame.Surface((radius*4, radius*4), pygame.SRCALPHA)
    for r in range(radius*2, 0, -1):
        a = int(alpha * (1 - r/(radius*2)))
        pygame.draw.circle(glow, (*color, a), (radius*2, radius*2), r)
    surf.blit(glow, (pos[0]-radius*2, pos[1]-radius*2))

def draw_text_glow(surf, text, font, color, pos, glow_color=None, center=True):
    gc = glow_color or color
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,1),(-1,1),(1,-1)]:
        s = font.render(text, True, tuple(max(0,c//3) for c in gc))
        r = s.get_rect(center=pos) if center else s.get_rect(topleft=pos)
        r.x += dx; r.y += dy
        surf.blit(s, r)
    s = font.render(text, True, color)
    r = s.get_rect(center=pos) if center else s.get_rect(topleft=pos)
    surf.blit(s, r)

# ── Starfield ─────────────────────────────────────────────────────────────────
class Star:
    def __init__(self):
        self.reset(random.randint(0, H))
    def reset(self, y=0):
        self.x = random.randint(0, W)
        self.y = y
        self.speed = random.uniform(0.3, 2.5)
        self.r = random.choice([1, 1, 1, 2])
        self.bright = random.randint(80, 200)
    def update(self):
        self.y += self.speed
        if self.y > H: self.reset()
    def draw(self, surf):
        c = (self.bright,)*3
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.r)

stars = [Star() for _ in range(180)]

# ── Particles ─────────────────────────────────────────────────────────────────
@dataclass
class Particle:
    x: float; y: float
    vx: float; vy: float
    color: tuple
    life: float = 1.0
    decay: float = 0.03
    size: float = 3.0

particles: List[Particle] = []

def spawn_explosion(x, y, color, n=18, speed=4):
    for _ in range(n):
        angle = random.uniform(0, math.tau)
        spd   = random.uniform(0.5, speed)
        particles.append(Particle(
            x, y,
            math.cos(angle)*spd, math.sin(angle)*spd,
            color,
            life=1.0,
            decay=random.uniform(0.02, 0.05),
            size=random.uniform(1.5, 4)
        ))

def update_particles():
    dead = []
    for p in particles:
        p.x += p.vx; p.y += p.vy
        p.vy += 0.04
        p.life -= p.decay
        if p.life <= 0: dead.append(p)
    for p in dead: particles.remove(p)

def draw_particles(surf):
    for p in particles:
        a = int(p.life * 255)
        c = tuple(min(255, int(ch)) for ch in p.color)
        s = max(1, int(p.size * p.life))
        pygame.draw.circle(surf, c, (int(p.x), int(p.y)), s)

# ── Bullet ────────────────────────────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y, angle=0, color=CYAN, speed=14, enemy=False):
        self.x = x; self.y = y
        self.vx = math.sin(angle) * speed
        self.vy = -math.cos(angle) * speed
        self.color = color
        self.enemy = enemy
        self.alive = True
        self.trail = []

    def update(self):
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > 6: self.trail.pop(0)
        self.x += self.vx; self.y += self.vy
        if not (-10 < self.x < W+10 and -10 < self.y < H+10):
            self.alive = False

    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            a = int(255 * (i / len(self.trail)) * 0.5)
            s = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, a), (2, 2), 2)
            surf.blit(s, (tx-2, ty-2))
        glow_circle(surf, self.color, (int(self.x), int(self.y)), 6, 80)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), 3)

# ── Player ────────────────────────────────────────────────────────────────────
class Player:
    SHAPE = [( 0,-22),(14,14),( 0, 7),(-14,14)]
    THRUSTER = [(0,7),(6,14),(0,20),(-6,14)]

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = W//2; self.y = H - 100
        self.angle = 0
        self.vx = 0; self.vy = 0
        self.hp = 3
        self.max_hp = 3
        self.invuln = 0
        self.shoot_cd = 0
        self.shield = 0
        self.power = 1  # 1=single, 2=double, 3=triple
        self.power_timer = 0
        self.score_multi = 1
        self.alive = True

    def rotated_shape(self, shape):
        cos_a = math.cos(math.radians(self.angle))
        sin_a = math.sin(math.radians(self.angle))
        pts = []
        for (px, py) in shape:
            rx = px * cos_a - py * sin_a + self.x
            ry = px * sin_a + py * cos_a + self.y
            pts.append((rx, ry))
        return pts

    def shoot(self, bullets):
        if self.shoot_cd > 0: return
        self.shoot_cd = 10 if self.power >= 2 else 14
        a = math.radians(self.angle)
        if self.power == 1:
            bullets.append(Bullet(self.x, self.y, a, CYAN))
            play(SND_SHOOT)
        elif self.power == 2:
            for offset in [-0.15, 0.15]:
                bullets.append(Bullet(self.x, self.y, a+offset, CYAN))
            play(SND_SHOOT)
        else:
            for offset in [-0.2, 0, 0.2]:
                bullets.append(Bullet(self.x, self.y, a+offset, MAGENTA))
            play(SND_SHOOT)
            self.shoot_cd = 8

    def update(self, keys):
        if not self.alive: return
        if self.invuln > 0: self.invuln -= 1
        if self.shoot_cd > 0: self.shoot_cd -= 1
        if self.power_timer > 0:
            self.power_timer -= 1
            if self.power_timer == 0: self.power = 1

        thrust = 0.35
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.angle -= 4
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.angle += 4
        if keys[pygame.K_UP]    or keys[pygame.K_w]:
            self.vx += math.sin(math.radians(self.angle)) * thrust
            self.vy -= math.cos(math.radians(self.angle)) * thrust
            # thruster particles
            tx, ty = self.rotated_shape([(0, 14)])[0]
            for _ in range(2):
                particles.append(Particle(
                    tx + random.uniform(-3,3), ty + random.uniform(-3,3),
                    math.sin(math.radians(self.angle+180))*random.uniform(1,3)+self.vx*0.3,
                    -math.cos(math.radians(self.angle+180))*random.uniform(1,3)+self.vy*0.3,
                    random.choice([ORANGE, YELLOW, (255,100,0)]),
                    life=0.7, decay=0.06, size=random.uniform(2,5)
                ))

        self.vx *= 0.97; self.vy *= 0.97
        self.x = (self.x + self.vx) % W
        self.y = (self.y + self.vy) % H

    def draw(self, surf):
        if not self.alive: return
        if self.invuln > 0 and (self.invuln // 4) % 2 == 0: return

        pts = self.rotated_shape(self.SHAPE)
        color = MAGENTA if self.power == 3 else (GREEN if self.power == 2 else CYAN)

        # glow
        glow_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(3):
            offset_pts = [(p[0], p[1]) for p in pts]
            pygame.draw.polygon(glow_surf, (*color, 20), offset_pts)
        surf.blit(glow_surf, (0, 0))

        pygame.draw.polygon(surf, color, pts, 2)
        pygame.draw.polygon(surf, WHITE, pts, 1)

        # shield ring
        if self.shield > 0:
            pygame.draw.circle(surf, (*GREEN, 120), (int(self.x), int(self.y)), 28, 2)
            glow_circle(surf, GREEN, (int(self.x), int(self.y)), 28, 40)

    def hit(self):
        if self.invuln > 0: return False
        if self.shield > 0:
            self.shield -= 1
            spawn_explosion(self.x, self.y, GREEN, 10, 3)
            play(SND_HIT)
            return False
        self.hp -= 1
        self.invuln = 90
        spawn_explosion(self.x, self.y, ORANGE, 20, 5)
        play(SND_HIT)
        if self.hp <= 0:
            self.alive = False
            spawn_explosion(self.x, self.y, RED, 50, 8)
            play(SND_DIE)
        return True

    def radius(self): return 14

# ── Asteroid ──────────────────────────────────────────────────────────────────
class Asteroid:
    COLORS = [ORANGE, (255,100,50), YELLOW, (200,200,50), MAGENTA]

    def __init__(self, x=None, y=None, size=3, vx=None, vy=None):
        self.size = size
        self.hp = size
        self.max_hp = size
        r_map = {3: 38, 2: 22, 1: 12}
        self.r = r_map[size]
        self.color = random.choice(self.COLORS)
        if x is None:
            side = random.randint(0,3)
            if side == 0: self.x, self.y = random.randint(0,W), -50
            elif side == 1: self.x, self.y = W+50, random.randint(0,H)
            elif side == 2: self.x, self.y = random.randint(0,W), H+50
            else: self.x, self.y = -50, random.randint(0,H)
        else:
            self.x, self.y = x, y
        spd = random.uniform(0.8, 2.2) * (4-size)*0.4 + 0.6
        if vx is None:
            angle = math.atan2(H//2-self.y, W//2-self.x) + random.uniform(-0.8, 0.8)
            self.vx = math.cos(angle) * spd
            self.vy = math.sin(angle) * spd
        else:
            self.vx, self.vy = vx * 1.3 + random.uniform(-0.5,0.5), vy * 1.3 + random.uniform(-0.5,0.5)
        self.rot = 0
        self.rot_spd = random.uniform(-2, 2)
        self.shape = self._gen_shape()
        self.alive = True
        self.points = {3: 100, 2: 200, 1: 400}[size]

    def _gen_shape(self):
        pts = []
        n = random.randint(7, 11)
        for i in range(n):
            angle = (i / n) * math.tau
            r = self.r * random.uniform(0.75, 1.25)
            pts.append((math.cos(angle)*r, math.sin(angle)*r))
        return pts

    def rotated(self):
        cos_r = math.cos(math.radians(self.rot))
        sin_r = math.sin(math.radians(self.rot))
        return [(px*cos_r - py*sin_r + self.x, px*sin_r + py*cos_r + self.y)
                for px, py in self.shape]

    def update(self):
        self.x = (self.x + self.vx) % (W + 120)
        self.y = (self.y + self.vy) % (H + 120)
        if self.x < -60: self.x += W + 120
        if self.y < -60: self.y += H + 120
        self.rot += self.rot_spd

    def draw(self, surf):
        pts = self.rotated()
        # health-based color fade
        frac = self.hp / self.max_hp
        c = tuple(int(ch * (0.5 + 0.5 * frac)) for ch in self.color)
        glow_circle(surf, self.color, (int(self.x), int(self.y)), self.r, 25)
        pygame.draw.polygon(surf, c, pts, 0)
        pygame.draw.polygon(surf, WHITE, pts, 1)
        pygame.draw.polygon(surf, (*self.color, 180), pts, 2)

    def hit(self):
        self.hp -= 1
        spawn_explosion(self.x, self.y, self.color, 8, 3)
        if self.hp <= 0:
            self.alive = False
            spawn_explosion(self.x, self.y, self.color, 20, 5)
            play(SND_EXPLODE)
            return True
        play(SND_HIT)
        return False

    def split(self):
        if self.size > 1:
            return [Asteroid(self.x, self.y, self.size-1, self.vx, self.vy),
                    Asteroid(self.x, self.y, self.size-1, self.vx, self.vy)]
        return []

# ── Powerup ───────────────────────────────────────────────────────────────────
class Powerup:
    TYPES = ["triple", "shield", "health", "multi"]
    COLORS = {"triple": MAGENTA, "shield": GREEN, "health": RED, "multi": YELLOW}
    ICONS  = {"triple": "3x", "shield": "SH", "health": "♥", "multi": "2x"}

    def __init__(self, x, y):
        self.x = x; self.y = y
        self.type = random.choice(self.TYPES)
        self.color = self.COLORS[self.type]
        self.vy = random.uniform(0.5, 1.5)
        self.vx = random.uniform(-0.5, 0.5)
        self.alive = True
        self.life = 600
        self.t = 0

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.t += 1; self.life -= 1
        if self.life <= 0 or self.y > H+40: self.alive = False

    def draw(self, surf):
        pulse = abs(math.sin(self.t * 0.05))
        r = int(16 + pulse * 4)
        glow_circle(surf, self.color, (int(self.x), int(self.y)), r+8, 60)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r, 2)
        txt = FONT_SMALL.render(self.ICONS[self.type], True, self.color)
        surf.blit(txt, txt.get_rect(center=(int(self.x), int(self.y))))

    def radius(self): return 16

    def apply(self, player):
        if self.type == "triple":
            player.power = 3; player.power_timer = 600
        elif self.type == "shield":
            player.shield = 3
        elif self.type == "health":
            player.hp = min(player.max_hp, player.hp + 1)
        elif self.type == "multi":
            player.score_multi = 2; player.power_timer = 400

# ── Enemy ship ────────────────────────────────────────────────────────────────
class Enemy:
    def __init__(self):
        self.x = random.randint(50, W-50)
        self.y = -40
        self.hp = 4
        self.speed = random.uniform(1.2, 2.2)
        self.shoot_cd = random.randint(60, 120)
        self.angle = 0
        self.alive = True
        self.wobble = random.uniform(0, math.tau)

    def update(self, player_x, player_y, bullets):
        self.wobble += 0.04
        dx = player_x - self.x; dy = player_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.x += dx/dist * self.speed + math.sin(self.wobble)*1.5
            self.y += dy/dist * self.speed * 0.6 + 0.5
        self.angle = math.degrees(math.atan2(dx, -dy))
        self.shoot_cd -= 1
        if self.shoot_cd <= 0:
            self.shoot_cd = random.randint(80, 150)
            a = math.atan2(dy, dx) - math.pi/2
            bullets.append(Bullet(self.x, self.y, a, RED, speed=6, enemy=True))
        if self.y > H + 60: self.alive = False

    def draw(self, surf):
        # Diamond enemy ship
        glow_circle(surf, RED, (int(self.x), int(self.y)), 18, 40)
        pts = [(self.x, self.y-20),(self.x+16, self.y),(self.x, self.y+14),(self.x-16, self.y)]
        pygame.draw.polygon(surf, (180,20,20), pts)
        pygame.draw.polygon(surf, RED, pts, 2)
        # health bar
        bw = 30; bh = 4
        pygame.draw.rect(surf, DIM, (self.x-bw//2, self.y-28, bw, bh))
        pygame.draw.rect(surf, RED, (self.x-bw//2, self.y-28, int(bw*self.hp/4), bh))

    def hit(self):
        self.hp -= 1
        spawn_explosion(self.x, self.y, RED, 8, 3)
        if self.hp <= 0:
            self.alive = False
            spawn_explosion(self.x, self.y, RED, 25, 6)
            play(SND_EXPLODE)
            return True
        play(SND_HIT)
        return False

    def radius(self): return 18

# ── HUD ───────────────────────────────────────────────────────────────────────
def draw_hud(surf, player, score, level, wave_timer):
    # Score
    draw_text_glow(surf, f"SCORE  {score:06d}", FONT_MED, CYAN, (W//2, 28))

    # HP hearts
    for i in range(player.max_hp):
        c = RED if i < player.hp else DIM
        draw_text_glow(surf, "♥", FONT_MED, c, (30 + i*35, 28))

    # Level
    draw_text_glow(surf, f"LV {level}", FONT_MED, YELLOW, (W-70, 28))

    # Power indicator
    if player.power > 1:
        label = "TRIPLE" if player.power == 3 else "DOUBLE"
        c = MAGENTA if player.power == 3 else GREEN
        draw_text_glow(surf, label, FONT_SMALL, c, (W//2, 55))

    if player.score_multi > 1:
        draw_text_glow(surf, "x2 MULTI!", FONT_SMALL, YELLOW, (W//2, 72))

# ── Screen flash ──────────────────────────────────────────────────────────────
flash_frames = 0
flash_color   = WHITE

def screen_flash(color=WHITE, frames=8):
    global flash_frames, flash_color
    flash_frames = frames; flash_color = color

# ── Main game ─────────────────────────────────────────────────────────────────
def dist(ax, ay, bx, by):
    return math.hypot(ax-bx, ay-by)

def run_game():
    global flash_frames, flash_color
    player = Player()
    bullets: List[Bullet] = []
    asteroids: List[Asteroid] = []
    powerups: List[Powerup] = []
    enemies: List[Enemy] = []
    score = 0
    level = 1
    wave = 0
    wave_delay = 0
    enemy_timer = 0
    enemy_interval = 900
    combo = 0
    combo_timer = 0
    running = True
    game_over = False
    show_level = 0

    def spawn_wave():
        nonlocal wave
        wave += 1
        n = 3 + level + wave//2
        for _ in range(n):
            asteroids.append(Asteroid())

    spawn_wave()

    while running:
        dt = clock.tick(60)

        # ── Events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if game_over and event.key == pygame.K_r: return

        keys = pygame.key.get_pressed()

        # ── Update ────────────────────────────────────────────────────────────
        if not game_over:
            player.update(keys)
            if keys[pygame.K_SPACE] or keys[pygame.K_z]:
                player.shoot(bullets)

            for b in bullets: b.update()
            bullets = [b for b in bullets if b.alive]

            for a in asteroids: a.update()
            for p in powerups: p.update()
            powerups = [p for p in powerups if p.alive]

            # Enemy spawn
            enemy_timer += 1
            if enemy_timer >= enemy_interval:
                enemy_timer = 0
                enemy_interval = max(300, enemy_interval - 50)
                enemies.append(Enemy())

            enemy_bullets = [b for b in bullets if b.enemy]
            for e in enemies:
                e.update(player.x, player.y, bullets)
            enemies = [e for e in enemies if e.alive]

            # Combo decay
            combo_timer -= 1
            if combo_timer <= 0: combo = 0

            # ── Collision: player bullets → asteroids
            new_roids = []
            for b in [b for b in bullets if not b.enemy]:
                for a in asteroids:
                    if not a.alive: continue
                    if dist(b.x, b.y, a.x, a.y) < a.r + 4:
                        b.alive = False
                        destroyed = a.hit()
                        if destroyed:
                            combo += 1; combo_timer = 90
                            pts = int(a.points * player.score_multi * (1 + combo * 0.1))
                            score += pts
                            screen_flash(a.color, 4)
                            new_roids += a.split()
                            if random.random() < 0.18:
                                powerups.append(Powerup(a.x, a.y))
                        break
            asteroids += new_roids
            asteroids = [a for a in asteroids if a.alive]

            # ── Collision: player bullets → enemies
            for b in [b for b in bullets if not b.enemy]:
                for e in enemies:
                    if not e.alive: continue
                    if dist(b.x, b.y, e.x, e.y) < e.radius() + 4:
                        b.alive = False
                        if e.hit():
                            score += int(800 * player.score_multi)
                            screen_flash(RED, 5)
                            if random.random() < 0.4:
                                powerups.append(Powerup(e.x, e.y))
                        break

            # ── Collision: player → asteroids & enemies
            if player.alive:
                for a in asteroids:
                    if dist(player.x, player.y, a.x, a.y) < a.r + player.radius():
                        if player.hit():
                            screen_flash(ORANGE, 10)
                        break
                for e in enemies:
                    if dist(player.x, player.y, e.x, e.y) < e.radius() + player.radius():
                        if player.hit():
                            screen_flash(RED, 10)
                        break
                for b in [b for b in bullets if b.enemy]:
                    if dist(player.x, player.y, b.x, b.y) < player.radius() + 4:
                        b.alive = False
                        if player.hit():
                            screen_flash(ORANGE, 8)
                        break

                # ── Powerup pickup
                for p in powerups:
                    if dist(player.x, player.y, p.x, p.y) < p.radius() + player.radius():
                        p.apply(player); p.alive = False
                        spawn_explosion(p.x, p.y, p.color, 15, 3)
                        screen_flash(p.color, 6)

            # ── Wave clear
            if not asteroids and not wave_delay:
                wave_delay = 120
            if wave_delay > 0:
                wave_delay -= 1
                if wave_delay == 0:
                    level += 1
                    show_level = 120
                    play(SND_LEVEL)
                    spawn_wave()
                    player.hp = min(player.max_hp, player.hp + 1)

            if show_level > 0: show_level -= 1

            # Game over
            if not player.alive:
                game_over = True

        update_particles()

        # ── Draw ──────────────────────────────────────────────────────────────
        screen.fill(BG)

        # Grid lines (subtle)
        for x in range(0, W, 80):
            pygame.draw.line(screen, (10,10,30), (x,0), (x,H))
        for y in range(0, H, 80):
            pygame.draw.line(screen, (10,10,30), (0,y), (W,y))

        for s in stars: s.update(); s.draw(screen)

        for a in asteroids: a.draw(screen)
        for e in enemies: e.draw(screen)
        for b in bullets: b.draw(screen)
        for p in powerups: p.draw(screen)
        draw_particles(screen)
        player.draw(screen)

        draw_hud(screen, player, score, level, wave_delay)

        # Combo
        if combo >= 2:
            draw_text_glow(screen, f"COMBO x{combo}!", FONT_MED, YELLOW,
                           (W//2, H//2 - 60))

        # Level up banner
        if show_level > 0:
            alpha = min(255, show_level * 6)
            draw_text_glow(screen, f"— LEVEL {level} —", FONT_BIG, CYAN, (W//2, H//2))

        # Flash overlay
        if flash_frames > 0:
            flash_frames -= 1
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((*flash_color, int(flash_frames * 18)))
            screen.blit(s, (0,0))

        # Game over screen
        if game_over:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 10, 180))
            screen.blit(ov, (0, 0))
            draw_text_glow(screen, "GAME OVER", FONT_BIG, RED, (W//2, H//2 - 60))
            draw_text_glow(screen, f"FINAL SCORE: {score}", FONT_MED, YELLOW, (W//2, H//2))
            draw_text_glow(screen, f"LEVEL REACHED: {level}", FONT_MED, CYAN, (W//2, H//2 + 44))
            draw_text_glow(screen, "[ R ] to restart   [ ESC ] to quit", FONT_SMALL, WHITE, (W//2, H//2 + 100))

        pygame.display.flip()

    pygame.quit()

# ── Title screen ──────────────────────────────────────────────────────────────
def title_screen():
    t = 0
    local_stars = [Star() for _ in range(200)]
    while True:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                return

        screen.fill(BG)
        for x in range(0, W, 80): pygame.draw.line(screen, (10,10,30), (x,0), (x,H))
        for y in range(0, H, 80): pygame.draw.line(screen, (10,10,30), (0,y), (W,y))
        for s in local_stars: s.update(); s.draw(screen)

        pulse = abs(math.sin(t * 0.04))

        # Title
        draw_text_glow(screen, "✦ NEON BLASTER ✦", FONT_BIG, CYAN, (W//2, H//2 - 120))

        # Tagline
        draw_text_glow(screen, "Survive the void.", FONT_MED,
                       tuple(int(c*(0.5+0.5*pulse)) for c in MAGENTA), (W//2, H//2 - 50))

        # Controls
        controls = [
            ("W / ↑", "Thrust"),
            ("A/D / ←/→", "Rotate"),
            ("SPACE / Z", "Shoot"),
        ]
        y0 = H//2 + 10
        for key, action in controls:
            draw_text_glow(screen, f"{key:>12}  {action}", FONT_SMALL, WHITE, (W//2, y0))
            y0 += 28

        # Powerups legend
        pups = [("3x", MAGENTA, "Triple shot"), ("SH", GREEN, "Shield"),
                ("♥", RED, "Health"), ("2x", YELLOW, "Score x2")]
        x0 = W//2 - 200
        draw_text_glow(screen, "POWERUPS:", FONT_SMALL, WHITE, (W//2, y0+10))
        for i, (icon, col, desc) in enumerate(pups):
            draw_text_glow(screen, f"{icon} {desc}", FONT_SMALL, col, (x0 + i*110, y0+36))

        if (t // 20) % 2 == 0:
            draw_text_glow(screen, "PRESS ANY KEY TO START", FONT_MED,
                           tuple(int(c*(0.6+0.4*pulse)) for c in YELLOW), (W//2, H - 70))

        pygame.display.flip()
        t += 1

# ── Entry ─────────────────────────────────────────────────────────────────────
while True:
    title_screen()
    run_game()
