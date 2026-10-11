import pygame
import sys
import math
import random
import io
import wave
import struct
import heapq

# --- Setup ---
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

WIDTH, HEIGHT = 800, 600
WORLD_WIDTH = 3200
GROUND_Y = 500
GRID_SIZE = 40
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Virtual Pet Evolution Sim V9 - Weather & Polish")
clock = pygame.time.Clock()

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
RED = (235, 80, 80)
GREEN = (80, 200, 100)
BLUE = (80, 150, 255)
YELLOW = (255, 200, 50)
PURPLE = (180, 100, 220)
BROWN = (139, 90, 43)
CYAN = (0, 255, 255)
GOLD = (255, 215, 0)
PINK = (255, 105, 180)

font_title = pygame.font.SysFont("Arial", 64, bold=True)
font_large = pygame.font.SysFont("Arial", 28, bold=True)
font_med = pygame.font.SysFont("Arial", 20)
font_small = pygame.font.SysFont("Arial", 16)

# --- Procedural Sound Generation ---
def generate_sound(frequency, duration_ms, volume=0.5, waveform='sine'):
    sample_rate = 44100
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    wave_data = []
    for i in range(num_samples):
        t = float(i) / sample_rate
        if waveform == 'sine':
            val = int(volume * 32767.0 * math.sin(2.0 * math.pi * frequency * t))
        elif waveform == 'square':
            val = int(volume * 32767.0 * (1.0 if math.sin(2.0 * math.pi * frequency * t) > 0 else -1.0))
        wave_data.append(struct.pack('h', val))
    wav_file = io.BytesIO()
    with wave.open(wav_file, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(wave_data))
    wav_file.seek(0)
    return pygame.mixer.Sound(wav_file)

SFX_EAT = generate_sound(500, 150, 0.4, 'square')
SFX_BOUNCE = generate_sound(800, 200, 0.5, 'sine')
SFX_SLEEP = generate_sound(200, 400, 0.3, 'sine')
SFX_EVOLVE = generate_sound(600, 600, 0.6, 'sine')
SFX_GAMEOVER = generate_sound(150, 1000, 0.6, 'square')
SFX_JUMP = generate_sound(400, 100, 0.3, 'sine')
SFX_CLEAN = generate_sound(1200, 100, 0.3, 'sine')
SFX_HURT = generate_sound(150, 300, 0.5, 'square')
SFX_CRYSTAL = generate_sound(1000, 200, 0.4, 'sine')
SFX_HAZARD = generate_sound(300, 200, 0.3, 'square')
SFX_PET = generate_sound(700, 100, 0.4, 'sine')
SFX_WIN = generate_sound(800, 1000, 0.6, 'sine')
SFX_RAIN = generate_sound(100, 2000, 0.2, 'square')

# --- Camera ---
class Camera:
    def __init__(self):
        self.x = 0
        self.shake_intensity = 0

    def update(self, target_x, dt):
        desired_x = target_x - WIDTH // 2
        desired_x = max(0, min(desired_x, WORLD_WIDTH - WIDTH))
        self.x += (desired_x - self.x) * min(1.0, dt * 6.0)

    def add_shake(self, amount):
        self.shake_intensity = min(15, self.shake_intensity + amount)

    def get_offset(self):
        if self.shake_intensity > 0:
            sx = random.randint(-int(self.shake_intensity), int(self.shake_intensity))
            sy = random.randint(-int(self.shake_intensity), int(self.shake_intensity))
            self.shake_intensity *= 0.9
            if self.shake_intensity < 0.5: self.shake_intensity = 0
            return sx, sy
        return 0, 0

# --- D*-Lite Algorithm ---
class DStarLite:
    def __init__(self, grid, start, goal):
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0])
        self.start = start
        self.goal = goal
        self.k_m = 0
        self.g = {}
        self.rhs = {}
        self.U = []
        self.init_algo()

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def calculate_key(self, s):
        g_rhs = min(self.g.get(s, float('inf')), self.rhs.get(s, float('inf')))
        return (g_rhs + self.heuristic(self.start, s) + self.k_m, g_rhs)

    def get_neighbors(self, node):
        neighbors = []
        x, y = node
        for dx in [-1, 1]:
            nx, ny = x + dx, y
            if 0 <= nx < self.cols and 0 <= ny < self.rows:
                if self.grid[ny][nx]: neighbors.append((nx, ny))
        for dy in [-2, -1, 1, 2]:
            for dx in [-1, 0, 1]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.cols and 0 <= ny < self.rows:
                    if self.grid[ny][nx]:
                        if dy < 0 and y > 0 and self.grid[y-1][x]: continue 
                        neighbors.append((nx, ny))
        return neighbors

    def cost(self, u, v):
        if not self.grid[v[1]][v[0]]: return float('inf')
        return 1

    def update_vertex(self, u):
        if u != self.goal:
            self.rhs[u] = min(self.cost(u, s) + self.g.get(s, float('inf')) for s in self.get_neighbors(u))
        self.U = [(k, s) for k, s in self.U if s != u]
        heapq.heapify(self.U)
        if self.g.get(u, float('inf')) != self.rhs.get(u, float('inf')):
            heapq.heappush(self.U, (self.calculate_key(u), u))

    def init_algo(self):
        self.rhs[self.goal] = 0
        heapq.heappush(self.U, (self.calculate_key(self.goal), self.goal))
        self.compute_shortest_path()

    def compute_shortest_path(self):
        max_iters = 1000 
        while self.U and (self.U[0][0] < self.calculate_key(self.start) or self.rhs.get(self.start, float('inf')) != self.g.get(self.start, float('inf'))):
            if max_iters <= 0: break
            max_iters -= 1
            k_old, u = heapq.heappop(self.U)
            if k_old < self.calculate_key(u):
                heapq.heappush(self.U, (self.calculate_key(u), u))
            elif self.g.get(u, float('inf')) > self.rhs.get(u, float('inf')):
                self.g[u] = self.rhs[u]
                for s in self.get_neighbors(u): self.update_vertex(s)
            else:
                self.g[u] = float('inf')
                self.update_vertex(u)
                for s in self.get_neighbors(u): self.update_vertex(s)

    def update_start(self, new_start):
        self.k_m += self.heuristic(self.start, new_start)
        self.start = new_start

    def update_grid(self, new_grid, changed_nodes):
        self.grid = new_grid
        for node in changed_nodes: self.update_vertex(node)
        self.compute_shortest_path()

    def get_path(self):
        if self.rhs.get(self.start, float('inf')) == float('inf'): return [] 
        path = []
        current = self.start
        max_path = 100
        while current != self.goal and max_path > 0:
            max_path -= 1
            neighbors = self.get_neighbors(current)
            if not neighbors: break
            next_node = min(neighbors, key=lambda n: self.cost(current, n) + self.g.get(n, float('inf')))
            if self.cost(current, next_node) == float('inf'): break
            path.append(next_node)
            current = next_node
        return path

# --- Helper Classes ---
class Particle:
    def __init__(self, x, y, color, size=6, life_decay=8, gravity=0.2):
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-6, -1)
        self.life = 255
        self.size = size
        self.life_decay = life_decay
        self.gravity = gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= self.life_decay

    def draw(self, surface, cam_x):
        if self.life > 0:
            pygame.draw.circle(surface, self.color, (int(self.x - cam_x), int(self.y)), int(self.size * (self.life/255)))

class WeatherParticle:
    def __init__(self, weather_type):
        self.weather_type = weather_type
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(-50, 0)
        self.vx = -2 if weather_type == "rain" else random.uniform(-0.5, 0.5)
        self.vy = 12 if weather_type == "rain" else random.uniform(1, 3)
        self.length = random.randint(10, 20) if weather_type == "rain" else 0

    def update(self, cam_x):
        self.x += self.vx
        self.y += self.vy
        # Rain wraps around screen relative to camera
        if self.y > HEIGHT:
            self.y = random.uniform(-50, 0)
            self.x = random.uniform(0, WIDTH)
        if self.x < 0: self.x = WIDTH
        if self.x > WIDTH: self.x = 0

    def draw(self, surface):
        if self.weather_type == "rain":
            pygame.draw.line(surface, (100, 150, 255), (self.x, self.y), (self.x + self.vx, self.y + self.length), 2)
        else:
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), 2)

class FloatingText:
    def __init__(self, text, x, y, color):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.life = 255

    def update(self):
        self.y -= 1.5
        self.life -= 4

    def draw(self, surface, cam_x):
        if self.life > 0:
            text_surf = font_med.render(self.text, True, self.color)
            text_surf.set_alpha(self.life)
            surface.blit(text_surf, (self.x - cam_x, self.y))

class FoodItem:
    def __init__(self, x, y, path, is_golden=False):
        self.x = x
        self.y = y
        self.vy = 0
        self.path = path
        self.on_ground = False
        self.life = 15.0
        self.is_golden = is_golden
        self.rect = pygame.Rect(x - 12, y - 12, 24, 24)

    def update(self, dt, platforms):
        if not self.on_ground:
            self.vy += 500 * dt
            self.y += self.vy * dt
            if self.y >= GROUND_Y:
                self.y = GROUND_Y
                self.on_ground = True
            else:
                for p in platforms:
                    if self.x > p.rect.left and self.x < p.rect.right:
                        if self.y >= p.rect.y and self.y - self.vy * dt <= p.rect.y:
                            self.y = p.rect.y
                            self.on_ground = True
                            break
        else:
            self.life -= dt
        self.rect.topleft = (self.x - 12, self.y - 12)

    def draw(self, surface, cam_x):
        color = YELLOW if self.is_golden else (RED if self.path == 'good' else (150, 50, 50) if self.path == 'bad' else PURPLE)
        pygame.draw.circle(surface, color, (int(self.x - cam_x), int(self.y - 15)), 12)
        pygame.draw.line(surface, GREEN, (int(self.x - cam_x), int(self.y - 25)), (int(self.x - cam_x + 5), int(self.y - 30)), 3)

class BouncyMushroom:
    def __init__(self, x):
        self.x = x
        self.y = GROUND_Y
        self.rect = pygame.Rect(x - 40, GROUND_Y - 30, 80, 30)
    def draw(self, surface, cam_x):
        pygame.draw.rect(surface, (200, 200, 150), (self.x - 15 - cam_x, self.y - 30, 30, 30))
        pygame.draw.ellipse(surface, RED, (self.x - 40 - cam_x, self.y - 50, 80, 40))
        pygame.draw.ellipse(surface, BLACK, (self.x - 40 - cam_x, self.y - 50, 80, 40), 3)
        pygame.draw.circle(surface, WHITE, (self.x - 15 - cam_x, self.y - 35), 5)
        pygame.draw.circle(surface, WHITE, (self.x + 10 - cam_x, self.y - 40), 4)

class Platform:
    def __init__(self, x, y, w):
        self.rect = pygame.Rect(x, y, w, 20)
    def draw(self, surface, cam_x):
        pygame.draw.rect(surface, (150, 100, 50), (self.rect.x - cam_x, self.rect.y, self.rect.w, self.rect.h))
        pygame.draw.rect(surface, BLACK, (self.rect.x - cam_x, self.rect.y, self.rect.w, self.rect.h), 2)

class Hazard:
    def __init__(self, x):
        self.x = x
        self.y = GROUND_Y
        self.rect = pygame.Rect(x - 25, GROUND_Y - 20, 50, 20)
        self.active = True
    def draw(self, surface, cam_x):
        if not self.active: return
        pygame.draw.rect(surface, (50, 100, 30), (self.x - 5 - cam_x, self.y - 20, 10, 20))
        for i in range(3):
            tx = self.x - 20 + (i*20)
            pygame.draw.polygon(surface, DARK_GRAY, [(tx - cam_x, self.y), (tx + 10 - cam_x, self.y - 20), (tx + 20 - cam_x, self.y)])
            pygame.draw.polygon(surface, BLACK, [(tx - cam_x, self.y), (tx + 10 - cam_x, self.y - 20), (tx + 20 - cam_x, self.y)], 2)

class Crystal:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.base_y = y
        self.rect = pygame.Rect(x - 15, y - 15, 30, 30)
        self.collected = False
    def update(self, dt):
        self.y = self.base_y + math.sin(pygame.time.get_ticks() / 300) * 5
        self.rect.topleft = (self.x - 15, self.y - 15)
    def draw(self, surface, cam_x):
        if not self.collected:
            glow_size = 20 + math.sin(pygame.time.get_ticks() / 200) * 5
            pygame.draw.circle(surface, (200, 255, 255), (int(self.x - cam_x), int(self.y)), int(glow_size))
            pygame.draw.polygon(surface, (100, 255, 255), [(self.x - cam_x, self.y - 15), (self.x + 10 - cam_x, self.y), (self.x - cam_x, self.y + 15), (self.x - 10 - cam_x, self.y)])

class Poop:
    def __init__(self, x):
        self.x = x
        self.y = GROUND_Y
        self.rect = pygame.Rect(x - 15, GROUND_Y - 15, 30, 15)
    def draw(self, surface, cam_x):
        pygame.draw.ellipse(surface, BROWN, (self.x - 15 - cam_x, self.y - 15, 30, 15))
        pygame.draw.ellipse(surface, BLACK, (self.x - 15 - cam_x, self.y - 15, 30, 15), 2)

class Shrine:
    def __init__(self, x):
        self.x = x
        self.y = GROUND_Y
        self.rect = pygame.Rect(x - 40, GROUND_Y - 100, 80, 100)
    def draw(self, surface, cam_x):
        pygame.draw.rect(surface, GRAY, (self.x - 30 - cam_x, self.y - 30, 60, 30))
        pygame.draw.rect(surface, BLACK, (self.x - 30 - cam_x, self.y - 30, 60, 30), 2)
        orb_y = self.y - 60 + math.sin(pygame.time.get_ticks() / 400) * 10
        pygame.draw.circle(surface, CYAN, (int(self.x - cam_x), int(orb_y)), 20)
        pygame.draw.circle(surface, WHITE, (int(self.x - cam_x), int(orb_y)), 10)

# --- Pet Class ---
class Pet:
    def __init__(self):
        self.stage = 0 
        self.age = 0
        self.evolution_time = 25
        self.care_score = 100
        self.hunger = 80
        self.happiness = 80
        self.energy = 80
        self.health = 100
        self.path = None 
        self.state = 'idle' 
        self.state_timer = 0
        self.blink_timer = random.uniform(2, 5)
        self.is_blinking = False
        self.is_dead = False
        self.digestion = 0
        self.invincible_timer = 0
        self.x = WIDTH // 2
        self.y = GROUND_Y
        self.prev_y = GROUND_Y
        self.vx = 0
        self.vy = 0
        self.facing = 1
        self.on_ground = True
        self.walk_anim = 0
        self.just_landed = False
        self.evolution_flash = 0

    def update(self, dt, keys, ai_input=None):
        if self.is_dead: return
        self.age += dt
        self.state_timer -= dt
        if self.invincible_timer > 0: self.invincible_timer -= dt
        if self.evolution_flash > 0: self.evolution_flash -= dt
        if self.state_timer <= 0 and self.state not in ['sleeping', 'hurt']:
            self.state = 'idle'

        self.blink_timer -= dt
        if self.blink_timer <= 0:
            self.is_blinking = not self.is_blinking
            self.blink_timer = 0.15 if self.is_blinking else random.uniform(2, 5)

        move_speed = 180
        if self.state not in ['sleeping', 'eating', 'hurt']:
            if ai_input:
                if ai_input == 'left':
                    self.vx = -move_speed
                    self.facing = -1
                    if self.on_ground: self.state = 'walking'
                elif ai_input == 'right':
                    self.vx = move_speed
                    self.facing = 1
                    if self.on_ground: self.state = 'walking'
                else:
                    self.vx *= 0.8
                    if abs(self.vx) < 10: self.vx = 0
            else:
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    self.vx = -move_speed
                    self.facing = -1
                    if self.on_ground: self.state = 'walking'
                elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    self.vx = move_speed
                    self.facing = 1
                    if self.on_ground: self.state = 'walking'
                else:
                    self.vx *= 0.8
                    if abs(self.vx) < 10: self.vx = 0

                if (keys[pygame.K_s] or keys[pygame.K_DOWN]) and self.on_ground:
                    self.state = 'sleeping'
                    SFX_SLEEP.play()
                else:
                    if self.state == 'sleeping': self.state = 'idle'

        self.prev_y = self.y
        if not self.on_ground: self.vy += 1200 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.x < 50: self.x = 50; self.vx = 0
        if self.x > WORLD_WIDTH - 50: self.x = WORLD_WIDTH - 50; self.vx = 0

        self.on_ground = False
        if self.y >= GROUND_Y:
            self.y = GROUND_Y
            self.vy = 0
            self.on_ground = True
        else:
            for p in platforms:
                if self.x > p.rect.left and self.x < p.rect.right:
                    if self.y >= p.rect.y and self.prev_y <= p.rect.y:
                        self.y = p.rect.y
                        self.vy = 0
                        self.on_ground = True
                        break

        if self.on_ground:
            if self.state == 'jumping': self.state = 'idle'
            if self.prev_y < self.y - 5: self.just_landed = True

        if self.state == 'walking': self.walk_anim += dt * 10

        if self.stage > 0:
            self.hunger = max(0, self.hunger - dt * 1.5)
            self.happiness = max(0, self.happiness - dt * 1.0)
            if self.state != 'sleeping':
                self.energy = max(0, self.energy - dt * 0.8)
            else:
                self.energy = min(100, self.energy + dt * 15)

            if self.hunger <= 0 or self.happiness <= 0 or self.energy <= 0:
                self.health = max(0, self.health - dt * 5)
            else:
                self.health = min(100, self.health + dt * 2)

            if self.health <= 0:
                self.is_dead = True
                SFX_GAMEOVER.play()

        self.care_score = (self.hunger + self.happiness + self.energy) / 3
        if self.stage < 3 and self.age >= self.evolution_time: self.evolve()

    def jump(self):
        if self.on_ground and self.state not in ['sleeping', 'eating', 'hurt'] and not self.is_dead:
            self.vy = -550
            self.on_ground = False
            self.state = 'jumping'
            SFX_JUMP.play()

    def bounce(self):
        self.vy = -900
        self.on_ground = False
        self.state = 'jumping'
        self.happiness = min(100, self.happiness + 10)
        SFX_BOUNCE.play()

    def take_damage(self, amount):
        if self.invincible_timer <= 0:
            self.health = max(0, self.health - amount)
            self.invincible_timer = 1.5
            self.state = 'hurt'
            self.state_timer = 0.5
            self.vy = -300
            self.vx = -200 * self.facing
            SFX_HURT.play()

    def eat_food(self, food):
        if food.is_golden:
            self.hunger = min(100, self.hunger + 50)
            self.happiness = min(100, self.happiness + 50)
            self.energy = min(100, self.energy + 50)
        else:
            self.hunger = min(100, self.hunger + 25)
            self.energy = min(100, self.energy + 10)
        self.state = 'eating'
        self.state_timer = 1.0
        self.digestion += 1
        SFX_EAT.play()

    def collect_crystal(self):
        self.age = min(self.evolution_time, self.age + 3)
        self.happiness = min(100, self.happiness + 5)
        SFX_CRYSTAL.play()

    def pet(self):
        self.happiness = min(100, self.happiness + 5)
        SFX_PET.play()

    def evolve(self):
        self.stage += 1
        self.age = 0 
        self.evolution_flash = 1.0
        SFX_EVOLVE.play()
        if self.stage == 1:
            self.path = 'good' if self.care_score > 60 else 'bad' if self.care_score < 30 else 'neutral'
            return
        if self.stage in [2, 3]:
            if self.care_score > 70: self.path = 'good'
            elif self.care_score < 30: self.path = 'bad'
            else: self.path = 'neutral'

    def get_draw_color(self):
        if self.path == 'good': return GREEN if self.stage == 1 else BLUE if self.stage == 2 else YELLOW
        if self.path == 'bad': return (139, 69, 19) if self.stage == 1 else DARK_GRAY else (50, 50, 50)
        return PURPLE if self.stage == 1 else (200, 150, 255) if self.stage == 2 else (255, 150, 200)

    def draw_shadow(self, surface, cam_x):
        # Find surface beneath pet
        base_y = GROUND_Y
        for p in platforms:
            if self.x > p.rect.left and self.x < p.rect.right and self.y < p.rect.y:
                base_y = p.rect.y
        
        dist = base_y - self.y
        scale = max(0.3, 1.0 - dist / 300)
        alpha = max(30, int(150 * scale))
        width = int(40 * scale)
        height = int(10 * scale)
        
        shadow_surf = pygame.Surface((width*2, height*2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), (0, 0, width*2, height*2))
        surface.blit(shadow_surf, (self.x - cam_x - width, base_y - height))

    def draw(self, surface, cam_x):
        size = 30 + (self.stage * 10) if self.stage > 0 else 40
        color = self.get_draw_color()
        
        stretch_y = 1.0
        squish_x = 1.0
        if not self.on_ground:
            stretch_y = 1.2
            squish_x = 0.8
        elif self.state == 'walking':
            squish_x = 1.0 + math.sin(self.walk_anim) * 0.1
            stretch_y = 1.0 - math.sin(self.walk_anim) * 0.1

        draw_size_x = int(size * squish_x)
        draw_size_y = int(size * stretch_y)

        pet_surf = pygame.Surface((size*4, size*4), pygame.SRCALPHA)
        cx, cy = size*2, size*2
        is_flashing = self.invincible_timer > 0 and int(pygame.time.get_ticks()/50)%2 == 0

        if self.stage == 0:
            pygame.draw.ellipse(pet_surf, (255, 200, 150), (cx-draw_size_x, cy-draw_size_y, draw_size_x*2, draw_size_y*2))
            pygame.draw.ellipse(pet_surf, BLACK, (cx-draw_size_x, cy-draw_size_y, draw_size_x*2, draw_size_y*2), 3)
        else:
            if not is_flashing:
                pygame.draw.ellipse(pet_surf, color, (cx-draw_size_x, cy-draw_size_y, draw_size_x*2, draw_size_y*2))
                shadow_color = tuple(max(0, c - 40) for c in color)
                highlight_color = tuple(min(255, c + 40) for c in color)
                pygame.draw.ellipse(pet_surf, shadow_color, (cx-draw_size_x, cy+draw_size_y//4, draw_size_x*2, draw_size_y//2))
                pygame.draw.ellipse(pet_surf, highlight_color, (cx-draw_size_x//2, cy-draw_size_y, draw_size_x, draw_size_y//2))
                pygame.draw.ellipse(pet_surf, BLACK, (cx-draw_size_x, cy-draw_size_y, draw_size_x*2, draw_size_y*2), 3)
            
            if self.path == 'good':
                if self.stage >= 2: 
                    pygame.draw.polygon(pet_surf, color, [(cx - draw_size_x, cy - draw_size_y//2), (cx - draw_size_x + 15, cy - draw_size_y - 25), (cx - draw_size_x//2, cy - draw_size_y)])
                    pygame.draw.polygon(pet_surf, color, [(cx + draw_size_x, cy - draw_size_y//2), (cx + draw_size_x - 15, cy - draw_size_y - 25), (cx + draw_size_x//2, cy - draw_size_y)])
                if self.stage == 3: 
                    wing_y_offset = math.sin(pygame.time.get_ticks() / 150) * 5
                    pygame.draw.ellipse(pet_surf, (200, 200, 255), (cx - draw_size_x - 40, cy - 20 + wing_y_offset, 50, 60))
                    pygame.draw.ellipse(pet_surf, (200, 200, 255), (cx + draw_size_x - 10, cy - 20 - wing_y_offset, 50, 60))
            elif self.path == 'bad':
                if self.stage >= 2: 
                    pygame.draw.polygon(pet_surf, DARK_GRAY, [(cx - 20, cy - draw_size_y + 10), (cx - 10, cy - draw_size_y - 30), (cx, cy - draw_size_y + 10)])
                    pygame.draw.polygon(pet_surf, DARK_GRAY, [(cx, cy - draw_size_y + 10), (cx + 10, cy - draw_size_y - 30), (cx + 20, cy - draw_size_y + 10)])
            else: 
                if self.stage >= 2: 
                    pygame.draw.line(pet_surf, BLACK, (cx - 15, cy - draw_size_y), (cx - 25, cy - draw_size_y - 30), 3)
                    pygame.draw.circle(pet_surf, YELLOW, (cx - 25, cy - draw_size_y - 30), 5)

            eye_offset = draw_size_x // 3
            eye_y = cy - draw_size_y // 4
            if self.is_blinking or self.state == 'sleeping':
                pygame.draw.line(pet_surf, BLACK, (cx - eye_offset - 5, eye_y), (cx - eye_offset + 5, eye_y), 3)
                pygame.draw.line(pet_surf, BLACK, (cx + eye_offset - 5, eye_y), (cx + eye_offset + 5, eye_y), 3)
            else:
                pygame.draw.circle(pet_surf, WHITE, (cx - eye_offset, eye_y), 9)
                pygame.draw.circle(pet_surf, WHITE, (cx + eye_offset, eye_y), 9)
                pupil_offset = 2 if self.vx > 0 else -2 if self.vx < 0 else 0
                pygame.draw.circle(pet_surf, BLACK, (cx - eye_offset + pupil_offset, eye_y), 5)
                pygame.draw.circle(pet_surf, BLACK, (cx + eye_offset + pupil_offset, eye_y), 5)

            if self.state == 'eating' or self.state == 'hurt':
                pygame.draw.ellipse(pet_surf, BLACK, (cx - 10, cy + 5, 20, 15))
            elif self.care_score > 50 or self.state == 'jumping':
                pygame.draw.arc(pet_surf, BLACK, (cx - 15, cy, 30, 30), 3.14, 2*3.14, 3) 
            else:
                pygame.draw.arc(pet_surf, BLACK, (cx - 15, cy + 10, 30, 30), 0, 3.14, 3) 

        if self.facing == -1:
            pet_surf = pygame.transform.flip(pet_surf, True, False)
        surface.blit(pet_surf, (self.x - cam_x - size*2, self.y - size*2))

        if self.state == 'sleeping':
            z_x = self.x - cam_x + size
            z_y = self.y - size*2
            z_offset = math.sin(pygame.time.get_ticks() / 300) * 5
            text = font_med.render("Zzz", True, BLUE)
            surface.blit(text, (z_x, z_y + z_offset))

        if self.evolution_flash > 0:
            flash_radius = (1.0 - self.evolution_flash) * 150
            flash_alpha = int(self.evolution_flash * 255)
            flash_surf = pygame.Surface((flash_radius*2, flash_radius*2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 255, flash_alpha), (int(flash_radius), int(flash_radius)), int(flash_radius), 5)
            pygame.draw.circle(flash_surf, (255, 255, 255, flash_alpha//2), (int(flash_radius), int(flash_radius)), int(flash_radius*0.8), 2)
            surface.blit(flash_surf, (self.x - cam_x - flash_radius, self.y - 40 - flash_radius))

# --- AI Controller ---
class AIController:
    def __init__(self, pet):
        self.pet = pet
        self.state = 'wander'
        self.path = []
        self.dstar = None
        self.target_pos = None
        self.stuck_timer = 0
        self.repath_timer = 0
        self.wander_target = None
        self.last_grid_pos = None

    def update(self, dt, world_grid, foods, mushrooms, platforms, hazards_changed, shrine):
        if self.pet.state in ['eating', 'hurt', 'sleeping']:
            return None, []

        if self.pet.stage == 3 and self.pet.care_score > 80:
            self.state = 'seek_shrine'
            self.target_pos = (shrine.x, shrine.y - 20)
        elif self.pet.hunger < 60 and foods:
            self.state = 'seek_food'
            nearest = min(foods, key=lambda f: abs(f.x - self.pet.x))
            self.target_pos = (nearest.x, nearest.y)
        elif self.pet.energy < 30:
            self.state = 'seek_sleep'
            if self.pet.on_ground:
                self.pet.state = 'sleeping'
                SFX_SLEEP.play()
            return None, []
        elif self.pet.happiness < 50 and mushrooms:
            self.state = 'seek_play'
            nearest = min(mushrooms, key=lambda m: abs(m.x - self.pet.x))
            self.target_pos = (nearest.x, nearest.y - 30)
        else:
            self.state = 'wander'
            if not self.wander_target or abs(self.pet.x - self.wander_target[0]) < 50:
                self.wander_target = (random.randint(100, WORLD_WIDTH - 150), GROUND_Y)
            self.target_pos = self.wander_target

        start_node = (int(self.pet.x / GRID_SIZE), int((self.pet.y - 20) / GRID_SIZE))
        end_node = (int(self.target_pos[0] / GRID_SIZE), int((self.target_pos[1] - 20) / GRID_SIZE))
        
        if not (0 <= end_node[0] < len(world_grid[0]) and 0 <= end_node[1] < len(world_grid)): return None, []

        if not self.dstar or self.dstar.goal != end_node:
            self.dstar = DStarLite(world_grid, start_node, end_node)
            self.last_grid_pos = start_node
        else:
            if hazards_changed:
                changed_nodes = []
                for hz in hazards:
                     for x in range(hz.rect.left // GRID_SIZE, hz.rect.right // GRID_SIZE + 1):
                         changed_nodes.append((x, hz.rect.y // GRID_SIZE))
                self.dstar.grid = world_grid
                for node in changed_nodes:
                    self.dstar.update_vertex(node)
                self.dstar.compute_shortest_path()
            
            if start_node != self.last_grid_pos:
                self.dstar.update_start(start_node)
                self.last_grid_pos = start_node

        self.path = self.dstar.get_path()

        move_input = None
        if self.path:
            # Smooth pathing: look ahead to path[1] if we are close to path[0]
            target_node = self.path[0]
            if len(self.path) > 1:
                tx0, ty0 = self.path[0]
                world_tx0 = tx0 * GRID_SIZE + GRID_SIZE // 2
                if abs(self.pet.x - world_tx0) < 20:
                    target_node = self.path[1] # Look ahead!

            tx, ty = target_node
            world_tx = tx * GRID_SIZE + GRID_SIZE // 2
            world_ty = ty * GRID_SIZE + 20

            if abs(self.pet.x - world_tx) > 5:
                if self.pet.x < world_tx: move_input = 'right'
                else: move_input = 'left'
            
            if world_ty < self.pet.y - 10 and self.pet.on_ground:
                self.pet.jump()
                self.stuck_timer = 0
            elif self.pet.on_ground and move_input:
                self.stuck_timer = 0
            else:
                self.stuck_timer += dt
                if self.stuck_timer > 2.0:
                    self.pet.jump()
                    self.stuck_timer = 0

        return move_input, self.path

# --- World Generation & Caching ---
sky_cache = {}
def get_sky_surf(theme):
    key = (theme['sky_top'], theme['sky_bot'])
    if key not in sky_cache:
        surf = pygame.Surface((WIDTH, GROUND_Y))
        for y in range(GROUND_Y):
            color = [
                int(theme['sky_top'][0] + (theme['sky_bot'][0] - theme['sky_top'][0]) * (y / GROUND_Y)),
                int(theme['sky_top'][1] + (theme['sky_bot'][1] - theme['sky_top'][1]) * (y / GROUND_Y)),
                int(theme['sky_top'][2] + (theme['sky_bot'][2] - theme['sky_top'][2]) * (y / GROUND_Y))
            ]
            pygame.draw.line(surf, color, (0, y), (WIDTH, y))
        sky_cache[key] = surf
    return sky_cache[key]

def get_theme(stage, path):
    if stage == 0: return {'sky_top': (135, 206, 235), 'sky_bot': (200, 230, 255), 'ground': (100, 200, 100), 'type': 'meadow'}
    if path == 'good':
        if stage == 1: return {'sky_top': (135, 206, 235), 'sky_bot': (200, 230, 255), 'ground': (100, 200, 100), 'type': 'meadow'}
        if stage == 2: return {'sky_top': (100, 180, 255), 'sky_bot': (150, 200, 255), 'ground': (80, 180, 80), 'type': 'forest'}
        if stage == 3: return {'sky_top': (50, 150, 255), 'sky_bot': (150, 200, 255), 'ground': (200, 200, 255), 'type': 'sky'}
    elif path == 'bad':
        if stage == 1: return {'sky_top': (100, 100, 100), 'sky_bot': (150, 150, 150), 'ground': (80, 80, 80), 'type': 'alley'}
        if stage == 2: return {'sky_top': (60, 80, 60), 'sky_bot': (100, 120, 100), 'ground': (90, 100, 50), 'type': 'swamp'}
        if stage == 3: return {'sky_top': (40, 20, 20), 'sky_bot': (100, 40, 40), 'ground': (80, 30, 30), 'type': 'volcano'}
    else:
        if stage == 1: return {'sky_top': (200, 200, 255), 'sky_bot': (230, 230, 255), 'ground': (150, 120, 80), 'type': 'room'}
        if stage == 2: return {'sky_top': (150, 200, 255), 'sky_bot': (200, 220, 255), 'ground': (150, 150, 150), 'type': 'park'}
        if stage == 3: return {'sky_top': (50, 50, 80), 'sky_bot': (80, 80, 120), 'ground': (40, 40, 60), 'type': 'city'}

def draw_environment(surface, cam_x, theme, time_of_day):
    day_factor = math.sin(time_of_day * math.pi * 2) * 0.5 + 0.5
    night_factor = 1.0 - day_factor
    surface.blit(get_sky_surf(theme), (0, 0))

    sun_x = (time_of_day % 1.0) * WIDTH
    sun_y = GROUND_Y - 300 - math.sin((time_of_day % 1.0) * math.pi) * 150
    moon_x = ((time_of_day + 0.5) % 1.0) * WIDTH
    moon_y = GROUND_Y - 300 - math.sin(((time_of_day + 0.5) % 1.0) * math.pi) * 150

    if day_factor > 0.1: pygame.draw.circle(surface, YELLOW, (int(sun_x), int(sun_y)), 30)
    if night_factor > 0.1: pygame.draw.circle(surface, (200, 200, 200), (int(moon_x), int(moon_y)), 25)

    if night_factor > 0:
        night_surf = pygame.Surface((WIDTH, GROUND_Y), pygame.SRCALPHA)
        night_surf.fill((0, 0, 30, int(150 * night_factor)))
        surface.blit(night_surf, (0, 0))

    t_type = theme['type']
    bg_offset = -cam_x * 0.3
    mg_offset = -cam_x * 0.6

    if t_type == 'meadow':
        for i in range(20):
            tx = i * 120 - 50 + int(mg_offset) % 120
            pygame.draw.rect(surface, (100, 50, 0), (tx, GROUND_Y-30, 10, 30))
            pygame.draw.circle(surface, (50, 150, 50), (tx+5, GROUND_Y-30), 20)
    elif t_type == 'forest':
        for i in range(15):
            tx = i * 180 - 50 + int(mg_offset) % 180
            pygame.draw.polygon(surface, (30, 100, 30), [(tx, GROUND_Y), (tx+40, GROUND_Y-120), (tx+80, GROUND_Y)])
    elif t_type == 'alley':
         for i in range(18):
            tx = i * 130 - 50 + int(mg_offset) % 130
            pygame.draw.rect(surface, (50, 50, 50), (tx, GROUND_Y-40, 30, 40))
    elif t_type == 'swamp':
        for i in range(15):
            tx = i * 160 - 50 + int(mg_offset) % 160
            pygame.draw.line(surface, (50, 40, 30), (tx, GROUND_Y), (tx-20, GROUND_Y-80), 5)
    elif t_type == 'volcano':
        for i in range(12):
            tx = i * 200 - 50 + int(mg_offset) % 200
            pygame.draw.polygon(surface, (80, 30, 30), [(tx, GROUND_Y), (tx+100, GROUND_Y-150), (tx+200, GROUND_Y)])
    elif t_type == 'room':
        for i in range(12):
            tx = i * 200 - 50 + int(mg_offset) % 200
            pygame.draw.rect(surface, (200, 100, 200), (tx, GROUND_Y-40, 60, 40))
    elif t_type == 'park':
        for i in range(15):
            tx = i * 160 - 50 + int(mg_offset) % 160
            pygame.draw.rect(surface, (100, 100, 100), (tx, GROUND_Y-60, 10, 60))
    elif t_type == 'city':
        for i in range(15):
            tx = i * 180 - 50 + int(mg_offset) % 180
            pygame.draw.rect(surface, (70, 70, 90), (tx, GROUND_Y-120, 80, 120))

    pygame.draw.rect(surface, theme['ground'], (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(surface, BLACK, (0, GROUND_Y), (WIDTH, GROUND_Y), 3)

def draw_stat_bar(surface, x, y, stat, color, label):
    pygame.draw.rect(surface, GRAY, (x, y, 150, 18), border_radius=4)
    pygame.draw.rect(surface, color, (x, y, 1.5 * stat, 18), border_radius=4)
    pygame.draw.rect(surface, BLACK, (x, y, 150, 18), 2, border_radius=4)
    label_surf = font_small.render(label, True, BLACK)
    surface.blit(label_surf, (x, y - 18))

def draw_minimap(surface, pet, foods, crystals, shrine, cam_x):
    mm_width, mm_height = 200, 40
    mm_x, mm_y = WIDTH - mm_width - 20, 20
    pygame.draw.rect(surface, (0, 0, 0, 150), (mm_x, mm_y, mm_width, mm_height))
    pygame.draw.rect(surface, WHITE, (mm_x, mm_y, mm_width, mm_height), 2)

    scale = mm_width / WORLD_WIDTH
    sx = mm_x + int(shrine.x * scale)
    pygame.draw.circle(surface, CYAN, (sx, mm_y + mm_height // 2), 4)

    for c in crystals:
        if not c.collected:
            cx = mm_x + int(c.x * scale)
            pygame.draw.circle(surface, (100, 255, 255), (cx, mm_y + mm_height // 2), 2)

    for f in foods:
        fx = mm_x + int(f.x * scale)
        pygame.draw.circle(surface, RED, (fx, mm_y + mm_height // 2), 2)

    px = mm_x + int(pet.x * scale)
    pygame.draw.circle(surface, pet.get_draw_color() if pet.path else WHITE, (px, mm_y + mm_height // 2), 3)

    cam_left = mm_x + int(cam_x * scale)
    cam_right = mm_x + int((cam_x + WIDTH) * scale)
    pygame.draw.line(surface, YELLOW, (cam_left, mm_y), (cam_left, mm_y + mm_height), 1)
    pygame.draw.line(surface, YELLOW, (cam_right, mm_y), (cam_right, mm_y + mm_height), 1)

def draw_vignette(surface):
    vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(5):
        alpha = 10 + i * 10
        pygame.draw.rect(vignette, (0, 0, 0, alpha), (i*10, i*10, WIDTH - i*20, HEIGHT - i*20), 10)
    surface.blit(vignette, (0, 0))

# --- Main Game Loop ---
def main():
    global platforms, hazards
    pet = Pet()
    camera = Camera()
    ai = AIController(pet)
    particles = []
    texts = []
    foods = []
    poops = []
    weather_particles = []
    
    platforms = [Platform(300, 400, 120), Platform(600, 300, 120), Platform(1200, 380, 120), Platform(1500, 250, 120), Platform(2200, 400, 120), Platform(2600, 300, 120)]
    mushrooms = [BouncyMushroom(500), BouncyMushroom(1000), BouncyMushroom(1800), BouncyMushroom(2500)]
    hazards = [Hazard(800), Hazard(1400), Hazard(2000), Hazard(2800)]
    crystals = [Crystal(650, 250), Crystal(1550, 200), Crystal(2650, 250)]
    shrine = Shrine(3100)
    
    food_spawn_timer = 5.0
    hazard_toggle_timer = 8.0 
    weather_timer = random.uniform(15.0, 30.0)
    current_weather = None
    game_time = 0.0
    ai_mode = False
    
    running = True
    game_state = "MENU" # MENU, PLAYING, PAUSED, GAME_OVER, WIN
    world_surf = pygame.Surface((WIDTH, HEIGHT))

    cols = WORLD_WIDTH // GRID_SIZE
    rows = HEIGHT // GRID_SIZE
    world_grid = [[False for _ in range(cols)] for _ in range(rows)]
    ground_row = GROUND_Y // GRID_SIZE
    for x in range(cols): world_grid[ground_row][x] = True
    for p in platforms:
        prow = p.rect.y // GRID_SIZE
        for x in range(p.rect.left // GRID_SIZE, p.rect.right // GRID_SIZE + 1):
            if 0 <= x < cols: world_grid[prow][x] = True
    for hz in hazards:
        hrow = hz.rect.y // GRID_SIZE
        for x in range(hz.rect.left // GRID_SIZE, hz.rect.right // GRID_SIZE + 1):
            if 0 <= x < cols: world_grid[hrow][x] = False

    while running:
        dt = clock.tick(60) / 1000.0
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if game_state == "MENU":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    game_state = "PLAYING"
                    
            elif game_state == "PLAYING":
                game_time += dt * 0.05
                if event.type == pygame.MOUSEBUTTONDOWN:
                    shake_x, shake_y = camera.get_offset()
                    mx = mouse_pos[0] - shake_x
                    my = mouse_pos[1] - shake_y
                    world_mouse_x = mx + camera.x
                    for p in poops[:]:
                        if p.rect.collidepoint(world_mouse_x, my):
                            poops.remove(p)
                            texts.append(FloatingText("Cleaned!", p.x - camera.x, p.y - 40, BLUE))
                            for _ in range(10): particles.append(Particle(p.x, p.y, BROWN))
                            SFX_CLEAN.play()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        pet = Pet()
                        ai = AIController(pet)
                        particles.clear()
                        texts.clear()
                        foods.clear()
                        poops.clear()
                        game_time = 0.0
                    if event.key in [pygame.K_SPACE, pygame.K_w, pygame.K_UP] and not ai_mode:
                        pet.jump()
                    if event.key == pygame.K_f:
                        ai_mode = not ai_mode
                        pet.vx = 0
                        texts.append(FloatingText("AI Mode: ON" if ai_mode else "AI Mode: OFF", pet.x - camera.x, pet.y - 80, CYAN))
                    if event.key == pygame.K_e:
                        pet.pet()
                        texts.append(FloatingText("<3", pet.x - camera.x + random.randint(-20, 20), pet.y - 60, PINK))
                        for _ in range(5): particles.append(Particle(pet.x, pet.y - 40, PINK, size=4, life_decay=10, gravity=-0.1))
                    if event.key in [pygame.K_p, pygame.K_ESCAPE]:
                        game_state = "PAUSED"

            elif game_state == "PAUSED":
                if event.type == pygame.KEYDOWN and event.key in [pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN]:
                    game_state = "PLAYING"
                    
            elif game_state in ["GAME_OVER", "WIN"]:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    pet = Pet()
                    ai = AIController(pet)
                    particles.clear()
                    texts.clear()
                    foods.clear()
                    poops.clear()
                    game_time = 0.0
                    game_state = "PLAYING"

        # --- Update Logic ---
        if game_state == "PLAYING":
            hazard_toggle_timer -= dt
            hazards_changed = False
            if hazard_toggle_timer <= 0:
                hazard_toggle_timer = random.uniform(5.0, 10.0)
                hz = random.choice(hazards)
                hz.active = not hz.active
                hazards_changed = True
                texts.append(FloatingText("Hazard Changed!", hz.x - camera.x, GROUND_Y - 60, DARK_GRAY))
                SFX_HAZARD.play()

            if hazards_changed:
                for x in range(cols): world_grid[ground_row][x] = True
                for hz in hazards:
                    hrow = hz.rect.y // GRID_SIZE
                    for x in range(hz.rect.left // GRID_SIZE, hz.rect.right // GRID_SIZE + 1):
                        if 0 <= x < cols: world_grid[hrow][x] = hz.active

            # Weather Logic
            weather_timer -= dt
            if weather_timer <= 0:
                if current_weather:
                    current_weather = None
                    weather_timer = random.uniform(15.0, 30.0)
                else:
                    current_weather = "rain" if random.random() > 0.3 else "snow"
                    weather_timer = random.uniform(10.0, 20.0)
                    if current_weather == "rain":
                        SFX_RAIN.play(-1)
                    else:
                        SFX_RAIN.stop()
            
            if current_weather == "rain":
                # Rain particle spawning
                if len(weather_particles) < 100:
                    weather_particles.append(WeatherParticle("rain"))
                # Happiness drain if not under shelter
                is_sheltered = False
                for p in platforms:
                    if pet.x > p.rect.left and pet.x < p.rect.right and pet.y > p.rect.y + 20:
                        is_sheltered = True
                        break
                if not is_sheltered:
                    pet.happiness = max(0, pet.happiness - dt * 2.0)

            elif current_weather == "snow":
                if len(weather_particles) < 50:
                    weather_particles.append(WeatherParticle("snow"))
            
            if not current_weather:
                SFX_RAIN.stop()

            ai_input = None
            current_path = []
            if ai_mode:
                ai_input, current_path = ai.update(dt, world_grid, foods, mushrooms, platforms, hazards_changed, shrine)
                
            pet.update(dt, keys, ai_input)
            camera.update(pet.x, dt)
            
            if pet.just_landed:
                pet.just_landed = False
                for _ in range(5): particles.append(Particle(pet.x, pet.y, (200, 200, 200), size=4, life_decay=15))
                camera.add_shake(2)

            if pet.state == 'walking' and random.random() < 0.2:
                particles.append(Particle(pet.x, pet.y, (200, 200, 200), size=3, life_decay=20, gravity=0.1))

            food_spawn_timer -= dt
            if food_spawn_timer <= 0 and len(foods) < 4:
                food_spawn_timer = random.uniform(6.0, 10.0)
                fx = pet.x + random.randint(-400, 400)
                fx = max(100, min(WORLD_WIDTH - 200, fx))
                is_golden = random.random() < 0.1
                foods.append(FoodItem(fx, 100, pet.path, is_golden))

            for f in foods[:]:
                f.update(dt, platforms)
                p_rect = pygame.Rect(pet.x - 30, pet.y - 50, 60, 50)
                if p_rect.colliderect(f.rect):
                    pet.eat_food(f)
                    foods.remove(f)
                    txt = "+50 STATS!" if f.is_golden else "+25 Hunger"
                    col = YELLOW if f.is_golden else RED
                    texts.append(FloatingText(txt, f.x - camera.x, f.y - 40, col))
                    for _ in range(15): particles.append(Particle(f.x, f.y, col))
                    camera.add_shake(3)
                elif f.life <= 0:
                    foods.remove(f)

            if pet.digestion >= 2:
                pet.digestion = 0
                poops.append(Poop(pet.x + random.randint(-20, 20)))
            
            if len(poops) > 0:
                pet.happiness = max(0, pet.happiness - dt * 3 * len(poops))

            for c in crystals:
                c.update(dt)
                p_rect = pygame.Rect(pet.x - 20, pet.y - 40, 40, 40)
                if not c.collected and p_rect.colliderect(c.rect):
                    c.collected = True
                    texts.append(FloatingText("Crystal! +3s Evolution", c.x - camera.x, c.y - 40, (100, 255, 255)))
                    for _ in range(25): particles.append(Particle(c.x, c.y, (100, 255, 255)))
                    camera.add_shake(4)
                    pet.collect_crystal()

            p_rect = pygame.Rect(pet.x - 15, pet.y - 30, 30, 30)
            for hz in hazards:
                if hz.active and p_rect.colliderect(hz.rect) and pet.on_ground:
                    pet.take_damage(20)
                    camera.add_shake(8)
                    texts.append(FloatingText("-20 HP", pet.x - camera.x, pet.y - 60, RED))

            if pet.vy > 0:
                for m in mushrooms:
                    if p_rect.colliderect(m.rect) and pet.y < m.rect.centery:
                        pet.bounce()
                        texts.append(FloatingText("+10 Happy!", m.x - camera.x, m.y - 80, YELLOW))
                        for _ in range(15): particles.append(Particle(m.x, m.y, YELLOW))
                        camera.add_shake(3)

            if pet.stage == 3 and pet.care_score > 80:
                if p_rect.colliderect(shrine.rect):
                    game_state = "WIN"
                    SFX_WIN.play()
                    camera.add_shake(15)
                    for _ in range(100): particles.append(Particle(shrine.x, shrine.y - 60, GOLD))

            if pet.stage > 0 and pet.age < 0.1:
                for _ in range(40): particles.append(Particle(pet.x, pet.y - 40, pet.get_draw_color()))
                camera.add_shake(10)

            if pet.is_dead: game_state = "GAME_OVER"

        # Always update particles/texts weather
        for p in particles[:]: p.update()
        for p in [p for p in particles if p.life <= 0]: particles.remove(p)
        for t in texts[:]: t.update()
        for t in [t for t in texts if t.life <= 0]: texts.remove(t)
        for w in weather_particles: w.update(camera.x)
        weather_particles = [w for w in weather_particles if w.y < HEIGHT + 50]

        # --- DRAWING TO WORLD SURFACE ---
        theme = get_theme(pet.stage, pet.path)
        draw_environment(world_surf, camera.x, theme, game_time)

        for p in platforms: p.draw(world_surf, camera.x)
        shrine.draw(world_surf, camera.x)
        for m in mushrooms: m.draw(world_surf, camera.x)
        for hz in hazards: hz.draw(world_surf, camera.x)
        for c in crystals: c.draw(world_surf, camera.x)
        for f in foods: f.draw(world_surf, camera.x)
        for p in poops: p.draw(world_surf, camera.x)
        
        pet.draw_shadow(world_surf, camera.x)

        if ai_mode and 'current_path' in locals() and current_path:
            for i, node in enumerate(current_path):
                nx = node[0] * GRID_SIZE + GRID_SIZE // 2
                ny = node[1] * GRID_SIZE + 20
                pygame.draw.circle(world_surf, CYAN, (int(nx - camera.x), int(ny)), 5)
                pygame.draw.circle(world_surf, BLACK, (int(nx - camera.x), int(ny)), 5, 1)

        for p in particles: p.draw(world_surf, camera.x)
        pet.draw(world_surf, camera.x)
        for t in texts: t.draw(world_surf, camera.x)

        # Draw weather in front of pet
        for w in weather_particles: w.draw(world_surf)

        shake_x, shake_y = camera.get_offset()
        screen.fill(BLACK)
        screen.blit(world_surf, (shake_x, shake_y))

        # --- UI OVERLAY ---
        if game_state in ["PLAYING", "PAUSED", "GAME_OVER", "WIN"]:
            ui_panel = pygame.Surface((WIDTH, 140), pygame.SRCALPHA)
            ui_panel.fill((255, 255, 255, 200))
            screen.blit(ui_panel, (0, 0))
            pygame.draw.line(screen, BLACK, (0, 140), (WIDTH, 140), 2)

            stage_names = ["Egg", "Baby", "Teen", "Adult"]
            stage_text = font_large.render(f"Stage: {stage_names[pet.stage]}", True, BLACK)
            screen.blit(stage_text, (20, 20))
            
            path_text = font_med.render(f"Path: {pet.path if pet.path else 'Unknown'}", True, BLACK)
            screen.blit(path_text, (20, 55))
            
            time_to_evolve = max(0, pet.evolution_time - pet.age) if pet.stage < 3 else 0
            evolve_text = font_med.render(f"Next evolution in: {time_to_evolve:.1f}s", True, BLACK)
            screen.blit(evolve_text, (20, 80))
            
            controls_text = font_small.render("Move: A/D | Jump: SPACE | Sleep: S | Pet: E | AI: F | Pause: P", True, DARK_GRAY)
            screen.blit(controls_text, (20, 110))

            if ai_mode:
                ai_text = font_med.render(f"AI State: {ai.state.upper()}", True, CYAN)
                screen.blit(ai_text, (WIDTH - 250, 140 - 30))

            if current_weather:
                w_text = font_med.render(f"Weather: {current_weather.upper()}", True, BLUE if current_weather == "rain" else WHITE)
                screen.blit(w_text, (WIDTH - 250, 60))

            draw_stat_bar(screen, 300, 30, pet.hunger, RED, "Hunger")
            draw_stat_bar(screen, 300, 70, pet.happiness, YELLOW, "Happiness")
            draw_stat_bar(screen, 500, 30, pet.energy, BLUE, "Energy")
            draw_stat_bar(screen, 500, 70, pet.health, GREEN, "Health")

            draw_minimap(screen, pet, foods, crystals, shrine, camera.x)
            draw_vignette(screen)

        # --- MENU STATES ---
        if game_state == "MENU":
            screen.fill((30, 30, 50))
            title = font_title.render("VIRTUAL PET", True, WHITE)
            sub = font_large.render("EVOLUTION SIM", True, CYAN)
            prompt = font_med.render("Press ENTER to Start", True, YELLOW)
            
            screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 100))
            screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 - 40))
            screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 + 40))
            
            inst = font_small.render("Raise your pet, explore the world, and reach the True Evolution Shrine!", True, GRAY)
            screen.blit(inst, (WIDTH//2 - inst.get_width()//2, HEIGHT//2 + 100))

        elif game_state == "PAUSED":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            pause_text = font_title.render("PAUSED", True, WHITE)
            screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2 - 50))
            cont_text = font_med.render("Press P or ESC to Resume", True, YELLOW)
            screen.blit(cont_text, (WIDTH//2 - cont_text.get_width()//2, HEIGHT//2 + 20))

        elif game_state == "GAME_OVER":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 220))
            screen.blit(overlay, (0, 0))
            go_text = font_title.render("GAME OVER", True, RED)
            screen.blit(go_text, (WIDTH//2 - go_text.get_width()//2, HEIGHT//2 - 60))
            restart_text = font_med.render("Press ENTER to Restart", True, WHITE)
            screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 20))

        elif game_state == "WIN":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 0, 120))
            screen.blit(overlay, (0, 0))
            win_text = font_title.render("TRUE EVOLUTION!", True, GOLD)
            screen.blit(win_text, (WIDTH//2 - win_text.get_width()//2, HEIGHT//2 - 60))
            restart_text = font_med.render("Press ENTER to Play Again", True, BLACK)
            screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()