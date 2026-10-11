import sys
import random
import math
import heapq
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QProgressBar, QLabel, QComboBox, QCheckBox, QGridLayout, QDialog, QMessageBox)
from PySide6.QtCore import QTimer, Qt, QVariantAnimation, QEasingCurve, QPoint, Signal
from PySide6.QtGui import QFont, QColor, QPainter

# --- Data Definitions (Removed 'evolved' key) ---
PETS = {
    "Dog": {"happy": "🐶", "sad": "🥺", "sleep": "😴", "speed": 1.0, "flying": False},
    "Cat": {"happy": "🐱", "sad": "😿", "sleep": "💤", "speed": 1.2, "flying": False},
    "Rabbit": {"happy": "🐰", "sad": "🐰", "sleep": "💤", "speed": 1.5, "flying": False},
    "Panda": {"happy": "🐼", "sad": "🐼", "sleep": "💤", "speed": 0.8, "flying": False},
    "Bird": {"happy": "🐦", "sad": "🐦", "sleep": "💤", "speed": 2.0, "flying": True},
    "Turtle": {"happy": "🐢", "sad": "🐢", "sleep": "💤", "speed": 0.4, "flying": False},
    "Fox": {"happy": "🦊", "sad": "🦊", "sleep": "💤", "speed": 1.3, "flying": False},
    "Dragon": {"happy": "🐉", "sad": "🐉", "sleep": "💤", "speed": 1.1, "flying": True},
    "Unicorn": {"happy": "🦄", "sad": "🥺", "sleep": "💤", "speed": 1.6, "flying": True}
}

ENVIRONMENTS = {
    "Living Room": {"bg": "#f0e68c", "props": [("🛋️", 10, 130, 2), ("🪴", 270, 140, 1), ("📺", 130, 110, 1), ("🧸", 200, 150, 1)]},
    "Garden": {"bg": "#87ceeb", "props": [("🌳", 10, 100, 2), ("🌻", 270, 140, 1), ("🍄", 150, 150, 1), ("⛲", 220, 110, 2)]},
    "Beach": {"bg": "#ffe4b5", "props": [("🌴", 250, 90, 0), ("🏖️", 10, 140, 0), ("🐚", 150, 150, 0), ("⛵", 270, 30, 0), ("🦀", 120, 150, 1)]},
    "Space": {"bg": "#0b0f1f", "props": [("🚀", 30, 20, 2), ("🪐", 240, 40, 2), ("⭐", 100, 70, 0), ("✨", 200, 110, 0), ("👽", 50, 150, 1)]},
    "Forest": {"bg": "#228b22", "props": [("🌲", 10, 90, 2), ("🌲", 270, 100, 2), ("🌲", 130, 80, 2), ("🦌", 200, 150, 1), ("🍄", 100, 150, 1)]}
}

PREY_TYPES = ["🐭", "🦗", "🐛", "🐟", "🦎"]

GRID_SIZE = 20
ENV_WIDTH = 340
ENV_HEIGHT = 220
COLS = ENV_WIDTH // GRID_SIZE
ROWS = ENV_HEIGHT // GRID_SIZE

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class PoopLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            self.deleteLater()
        super().mousePressEvent(event)

class PreyLabel(QLabel):
    def __init__(self, env_widget):
        super().__init__(env_widget)
        self.env = env_widget
        self.setText(random.choice(PREY_TYPES))
        self.setFont(QFont("Arial", 20))
        
        while True:
            x = random.randint(1, COLS-2) * GRID_SIZE
            y = random.randint(8, ROWS-2) * GRID_SIZE
            if (x // GRID_SIZE, y // GRID_SIZE) not in self.env.grid_obstacles:
                break
        self.move(x, y)
        self.show()
        self.raise_()
        
        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self.flee)
        self.move_timer.start(600)

    def flee(self):
        pet_x = self.env.pet_label.x()
        pet_y = self.env.pet_label.y()
        dist = math.hypot(self.x() - pet_x, self.y() - pet_y)
        
        if dist < 80:
            dx = self.x() - pet_x
            dy = self.y() - pet_y
            try:
                norm = math.hypot(dx, dy)
                flee_x = int(self.x() + (dx/norm) * 40 + random.uniform(-20, 20))
                flee_y = int(self.y() + (dy/norm) * 40 + random.uniform(-20, 20))
            except ZeroDivisionError:
                flee_x = self.x()
                flee_y = self.y()
                
            flee_x = max(10, min(ENV_WIDTH - 30, flee_x))
            flee_y = max(10, min(ENV_HEIGHT - 30, flee_y))
            
            if (flee_x // GRID_SIZE, flee_y // GRID_SIZE) not in self.env.grid_obstacles:
                self.move(flee_x, flee_y)
        else:
            if random.random() < 0.3:
                hop_x = max(10, min(ENV_WIDTH - 30, self.x() + random.randint(-20, 20)))
                hop_y = max(10, min(ENV_HEIGHT - 30, self.y() + random.randint(-20, 20)))
                if (hop_x // GRID_SIZE, hop_y // GRID_SIZE) not in self.env.grid_obstacles:
                    self.move(hop_x, hop_y)

class ShopDialog(QDialog):
    def __init__(self, coins, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🛒 Pet Shop")
        self.setFixedSize(250, 200)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")
        self.selected_item = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"You have {coins} 🪙"))
        
        items = [
            ("Golden Apple 🍎", "Fully restores hunger.", 15),
            ("Ball of Yarn 🧶", "Huge happiness boost.", 10),
            ("Medicine 💊", "Cures sickness.", 20)
        ]
        
        btn_style = """
            QPushButton { background-color: #4CAF50; border: none; color: white; 
                          padding: 8px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #555; color: #888; }
        """
        
        for name, desc, cost in items:
            btn = QPushButton(f"{name} ({cost}🪙)\n{desc}")
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked, n=name, c=cost: self.buy(n, c, coins))
            layout.addWidget(btn)

    def buy(self, name, cost, coins):
        if coins >= cost:
            self.selected_item = name
            self.accept()
        else:
            QMessageBox.warning(self, "Broke!", "Not enough coins!")

class EnvironmentWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(ENV_WIDTH, ENV_HEIGHT)
        self.current_pet_type = "Dog"
        self.current_env = "Living Room"
        
        self.is_sleeping = False
        self.is_sad = False
        self.is_hungry = False
        self.is_dirty = False
        self.is_sick = False
        self.busy = False
        self.pet_size = 30
        
        self.thought_label = QLabel("", self)
        self.thought_label.setFont(QFont("Arial", 12))
        self.thought_label.hide()
        
        self.pet_label = ClickableLabel(PETS[self.current_pet_type]["happy"])
        self.pet_label.setParent(self)
        self.pet_label.setFont(QFont("Arial", self.pet_size))
        self.pet_label.move(140, 120)
        self.pet_label.clicked.connect(self.on_pet_clicked)
        
        self.active_item = None
        self.active_prey = None
        self.poops = []
        self.prop_labels = []
        self.grid_obstacles = set()
        
        self.move_anim = None
        self.current_path = []
        self.show_grid = False
        
        self.time_of_day = 0.0 # 0.0 to 100.0
        
        self.wander_timer = QTimer(self)
        self.wander_timer.timeout.connect(self.decide_action)
        self.wander_timer.start(3000)
        
        self.load_environment("Living Room")

    def load_environment(self, env_name):
        self.current_env = env_name
        env_data = ENVIRONMENTS[env_name]
        self.setStyleSheet(f"background-color: {env_data['bg']}; border-radius: 10px; border: 2px solid #555;")
        
        for prop in self.prop_labels:
            prop.deleteLater()
        self.prop_labels.clear()
        self.grid_obstacles.clear()
        
        for emoji, x, y, block_radius in env_data["props"]:
            prop_label = QLabel(emoji, self)
            prop_label.setFont(QFont("Arial", 30))
            prop_label.move(x, y)
            prop_label.show()
            self.prop_labels.append(prop_label)
            
            if block_radius > 0:
                center_cx = (x + 15) // GRID_SIZE
                center_cy = (y + 15) // GRID_SIZE
                for dx in range(-block_radius, block_radius + 1):
                    for dy in range(-block_radius, block_radius + 1):
                        self.grid_obstacles.add((center_cx + dx, center_cy + dy))
            
        self.pet_label.raise_()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.show_grid:
            painter = QPainter(self)
            painter.setPen(QColor(255, 255, 255, 50))
            for x in range(0, ENV_WIDTH, GRID_SIZE):
                painter.drawLine(x, 0, x, ENV_HEIGHT)
            for y in range(0, ENV_HEIGHT, GRID_SIZE):
                painter.drawLine(0, y, ENV_WIDTH, y)
            painter.setBrush(QColor(255, 0, 0, 100))
            for obs in self.grid_obstacles:
                painter.drawRect(obs[0]*GRID_SIZE, obs[1]*GRID_SIZE, GRID_SIZE, GRID_SIZE)
                
        if self.time_of_day > 60:
            painter = QPainter(self)
            darkness = min(0.6, (self.time_of_day - 60) / 60.0)
            painter.fillRect(0, 0, ENV_WIDTH, ENV_HEIGHT, QColor(0, 0, 50, int(255 * darkness)))

    def advance_time(self):
        self.time_of_day = (self.time_of_day + 0.5) % 100
        self.update()

    def toggle_grid(self, state):
        self.show_grid = state == Qt.Checked
        self.update()

    def set_pet_type(self, pet_type):
        self.current_pet_type = pet_type
        self.update_pet_mood()

    def update_pet_size(self, level):
        self.pet_size = 30 + min(level, 9) * 2
        self.pet_label.setFont(QFont("Arial", self.pet_size))

    def update_pet_mood(self):
        pet_data = PETS[self.current_pet_type]
        
        if self.is_sleeping:
            self.pet_label.setText(pet_data["sleep"])
        elif self.is_sick:
            self.pet_label.setText("🤢")
        elif self.is_sad:
            self.pet_label.setText(pet_data["sad"])
        else:
            self.pet_label.setText(pet_data["happy"])
        self.update_thought_bubble()

    def update_thought_bubble(self, text=None):
        if self.is_sleeping or self.busy:
            self.thought_label.hide()
            return
        if text:
            self.thought_label.setText(f"💭{text}")
            self.thought_label.adjustSize()
            self.thought_label.show()
        elif self.is_sick:
            self.thought_label.setText("💭💊")
            self.thought_label.adjustSize()
            self.thought_label.show()
        elif self.is_dirty:
            self.thought_label.setText("💭🛁")
            self.thought_label.adjustSize()
            self.thought_label.show()
        elif self.is_hungry:
            self.thought_label.setText("💭🍽️")
            self.thought_label.adjustSize()
            self.thought_label.show()
        elif self.is_sad:
            self.thought_label.setText("💭💔")
            self.thought_label.adjustSize()
            self.thought_label.show()
        else:
            self.thought_label.hide()

    def find_path(self, start_pos, target_pos):
        is_flying = PETS[self.current_pet_type]["flying"]
        start_cx, start_cy = start_pos[0] // GRID_SIZE, start_pos[1] // GRID_SIZE
        target_cx, target_cy = target_pos[0] // GRID_SIZE, target_pos[1] // GRID_SIZE

        if is_flying:
            return [(target_pos[0], target_pos[1])]

        open_set = []
        heapq.heappush(open_set, (0, start_cx, start_cy))
        came_from = {}
        g_score = {(start_cx, start_cy): 0}
        
        def heuristic(x, y):
            return abs(x - target_cx) + abs(y - target_cy)

        while open_set:
            _, cx, cy = heapq.heappop(open_set)
            if cx == target_cx and cy == target_cy:
                path = []
                current = (cx, cy)
                while current in came_from:
                    path.append((current[0] * GRID_SIZE + 10, current[1] * GRID_SIZE + 10))
                    current = came_from[current]
                path.reverse()
                return path

            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < COLS and 0 <= ny < ROWS:
                    if (nx, ny) in self.grid_obstacles:
                        continue
                    tentative_g = g_score[(cx, cy)] + 1
                    if tentative_g < g_score.get((nx, ny), float('inf')):
                        came_from[(nx, ny)] = (cx, cy)
                        g_score[(nx, ny)] = tentative_g
                        f = tentative_g + heuristic(nx, ny)
                        heapq.heappush(open_set, (f, nx, ny))
        return []

    def execute_path(self, target_pos, on_complete_callback=None):
        start_pos = (self.pet_label.x(), self.pet_label.y())
        path = [start_pos] + self.find_path(start_pos, target_pos)
        
        if len(path) <= 1:
            if on_complete_callback: on_complete_callback()
            return

        speed = PETS[self.current_pet_type]["speed"]
        if self.is_sad: speed *= 0.5
        if self.is_sick: speed *= 0.3 
        
        total_dist = 0
        for i in range(len(path)-1):
            total_dist += math.hypot(path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])
        
        if self.active_prey and on_complete_callback == self.check_prey_caught:
            speed *= 1.2
            
        duration = int((total_dist / 20) * 300 / speed) 

        if self.move_anim:
            self.move_anim.stop()

        self.move_anim = QVariantAnimation(self)
        self.move_anim.setDuration(max(duration, 50))
        self.move_anim.setStartValue(0.0)
        self.move_anim.setEndValue(1.0)
        self.move_anim.setEasingCurve(QEasingCurve.Linear)
        
        def update_position(progress):
            target_dist = progress * total_dist
            current_dist = 0
            for i in range(len(path)-1):
                seg_dist = math.hypot(path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])
                if current_dist + seg_dist >= target_dist:
                    seg_progress = (target_dist - current_dist) / seg_dist
                    x = path[i][0] + (path[i+1][0] - path[i][0]) * seg_progress
                    y = path[i][1] + (path[i+1][1] - path[i][1]) * seg_progress
                    if not PETS[self.current_pet_type]["flying"]:
                        y -= abs(math.sin(progress * math.pi * len(path))) * 4
                    self.pet_label.move(int(x), int(y))
                    self.sync_thought_bubble(self.pet_label.pos())
                    if path[i+1][0] < path[i][0]:
                        self.pet_label.setStyleSheet("transform: scaleX(-1);")
                    else:
                        self.pet_label.setStyleSheet("")
                    break
                current_dist += seg_dist

        self.move_anim.valueChanged.connect(update_position)
        if on_complete_callback:
            self.move_anim.finished.connect(on_complete_callback)
        self.move_anim.start()

    def decide_action(self):
        if self.is_sleeping or self.busy or self.active_item:
            return

        if self.active_prey:
            self.update_thought_bubble("🎯")
            self.hunt_prey()
            return

        if self.is_hungry and random.random() < 0.5:
            self.spawn_prey(auto_triggered=True)
            return
            
        if self.is_hungry and random.random() < 0.8:
            self.spawn_item("🍲", auto_triggered=True)
            return
            
        if self.is_sad and random.random() < 0.5:
            self.spawn_item("🎾", auto_triggered=True)
            return

        if random.random() < 0.2 and self.prop_labels:
            self.update_thought_bubble("👃")
            QTimer.singleShot(1500, self.update_thought_bubble)
            return

        target_x = random.randint(1, COLS-2) * GRID_SIZE
        target_y = random.randint(8, ROWS-2) * GRID_SIZE
        self.execute_path((target_x, target_y))

    def spawn_prey(self, auto_triggered=False):
        if self.active_prey or self.busy:
            return False
            
        self.busy = True
        self.thought_label.hide()
        self.active_prey = PreyLabel(self)
        self.active_prey.raise_()
        self.pet_label.raise_()
        self.wander_timer.stop()
        
        self.parent().status_label.setText("Status: Hunting Prey!")
        self.parent().status_label.setStyleSheet("color: #FF9800;")
        self.hunt_prey()
        return True

    def hunt_prey(self):
        if not self.active_prey:
            self.busy = False
            self.wander_timer.start(2000)
            return
        target = (self.active_prey.x(), self.active_prey.y())
        self.execute_path(target, self.check_prey_caught)

    def check_prey_caught(self):
        if not self.active_prey:
            return
        dist = math.hypot(self.pet_label.x() - self.active_prey.x(), self.pet_label.y() - self.active_prey.y())
        if dist < 25:
            self.catch_prey()
        else:
            self.hunt_prey()

    def catch_prey(self):
        if self.active_prey:
            effect = QLabel("💥", self)
            effect.setFont(QFont("Arial", 25))
            effect.move(self.active_prey.x(), self.active_prey.y())
            effect.show()
            effect.raise_()
            anim = QVariantAnimation(effect)
            anim.setDuration(500)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            start_y = effect.y()
            def fade(progress):
                effect.move(effect.x(), int(start_y - 30 * progress))
            anim.valueChanged.connect(fade)
            anim.finished.connect(effect.deleteLater)
            anim.start()
            
            self.active_prey.deleteLater()
            self.active_prey = None
            self.busy = False
            self.wander_timer.start(2000)
            self.update_thought_bubble()
            self.parent().caught_prey()

    def spawn_item(self, item_emoji, auto_triggered=False):
        if self.active_item or self.busy:
            return False
            
        self.busy = True
        self.thought_label.hide()
        self.active_item = QLabel(item_emoji, self)
        self.active_item.setFont(QFont("Arial", 20))
        
        while True:
            item_x = random.randint(1, COLS-2) * GRID_SIZE
            item_y = random.randint(8, ROWS-2) * GRID_SIZE
            if (item_x // GRID_SIZE, item_y // GRID_SIZE) not in self.grid_obstacles:
                break
                
        self.active_item.move(item_x, item_y)
        self.active_item.show()
        self.active_item.raise_()
        self.pet_label.raise_()
        self.wander_timer.stop()
        self.execute_path((item_x + 10, item_y + 10), self.consume_item)
        return True

    def consume_item(self):
        if self.active_item:
            start_pos = self.pet_label.pos()
            self.move_anim = QVariantAnimation(self)
            self.move_anim.setDuration(400)
            self.move_anim.setStartValue(0.0)
            self.move_anim.setEndValue(1.0)
            def hop(progress):
                y = start_pos.y() - 30 * math.sin(progress * math.pi)
                self.pet_label.move(start_pos.x(), int(y))
            self.move_anim.valueChanged.connect(hop)
            self.move_anim.start()
            QTimer.singleShot(400, self.finish_consume)

    def finish_consume(self):
        if self.active_item:
            self.active_item.deleteLater()
            self.active_item = None
        self.busy = False
        self.wander_timer.start(2000)
        self.update_thought_bubble()

    def spawn_poop(self):
        if len(self.poops) >= 3: return
        poop_x = random.randint(1, COLS-2) * GRID_SIZE
        poop_y = random.randint(8, ROWS-2) * GRID_SIZE
        if (poop_x // GRID_SIZE, poop_y // GRID_SIZE) in self.grid_obstacles:
            return
        poop = PoopLabel("💩", self)
        poop.setFont(QFont("Arial", 20))
        poop.move(poop_x, poop_y)
        poop.show()
        poop.raise_()
        poop.clicked.connect(lambda: self.clean_poop(poop))
        self.poops.append(poop)
        self.grid_obstacles.add((poop_x // GRID_SIZE, poop_y // GRID_SIZE))
        self.pet_label.raise_()

    def clean_poop(self, poop):
        if poop in self.poops:
            self.poops.remove(poop)
            self.grid_obstacles.discard((poop.x() // GRID_SIZE, poop.y() // GRID_SIZE))
        poop.deleteLater()
        self.parent().cleaned_poop()

    def on_pet_clicked(self):
        heart = QLabel("❤️ +XP", self)
        heart.setFont(QFont("Arial", 12))
        heart.move(self.pet_label.x() + 10, self.pet_label.y() - 10)
        heart.show()
        heart.raise_()
        anim = QVariantAnimation(self)
        anim.setDuration(1000)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        start_y = heart.y()
        def float_up(progress):
            heart.move(heart.x(), int(start_y - 50 * progress))
        anim.valueChanged.connect(float_up)
        anim.start()
        anim.finished.connect(lambda: heart.deleteLater())
        self.parent().pet_petted()

    def sync_thought_bubble(self, pos):
        self.thought_label.move(pos.x() + 25, pos.y() - 15)


class VirtualPetApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Pet Simulator 8.1 - Economy & Survival")
        self.setFixedSize(400, 760)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")

        self.hunger = 100.0
        self.happiness = 100.0
        self.energy = 100.0
        self.cleanliness = 100.0
        self.is_sleeping = False
        self.is_sick = False
        
        self.level = 1
        self.xp = 0
        self.xp_needed = 100
        self.coins = 20

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        top_stats = QHBoxLayout()
        self.lvl_label = QLabel("Lvl 1 🐣")
        self.lvl_label.setFont(QFont("Arial", 12, QFont.Bold))
        top_stats.addWidget(self.lvl_label)
        self.xp_bar = QProgressBar()
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setStyleSheet("""
            QProgressBar { background-color: #444; border-radius: 5px; height: 10px; }
            QProgressBar::chunk { background-color: #9C27B0; border-radius: 5px; }
        """)
        top_stats.addWidget(self.xp_bar)
        
        self.coin_label = QLabel("🪙 20")
        self.coin_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.coin_label.setStyleSheet("color: #FFD700;")
        top_stats.addWidget(self.coin_label)
        layout.addLayout(top_stats)

        top_controls = QHBoxLayout()
        self.pet_selector = QComboBox()
        self.pet_selector.addItems(PETS.keys())
        self.pet_selector.currentTextChanged.connect(self.change_pet)
        top_controls.addWidget(QLabel("Pet:"))
        top_controls.addWidget(self.pet_selector)

        self.env_selector = QComboBox()
        self.env_selector.addItems(ENVIRONMENTS.keys())
        self.env_selector.currentTextChanged.connect(self.change_env)
        top_controls.addWidget(QLabel("Env:"))
        top_controls.addWidget(self.env_selector)
        layout.addLayout(top_controls)

        self.env_widget = EnvironmentWidget()
        layout.addWidget(self.env_widget, alignment=Qt.AlignCenter)

        self.grid_check = QCheckBox("Show Pathfinding Grid")
        self.grid_check.stateChanged.connect(self.env_widget.toggle_grid)
        layout.addWidget(self.grid_check)

        self.status_label = QLabel("Status: Happy")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.status_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(self.status_label)

        self.hunger_bar = self.create_stat_bar("Hunger", "#FF5722")
        layout.addWidget(self.hunger_bar['widget'])
        self.happy_bar = self.create_stat_bar("Happiness", "#FFEB3B")
        layout.addWidget(self.happy_bar['widget'])
        self.energy_bar = self.create_stat_bar("Energy", "#03A9F4")
        layout.addWidget(self.energy_bar['widget'])
        self.clean_bar = self.create_stat_bar("Cleanliness", "#009688")
        layout.addWidget(self.clean_bar['widget'])

        button_grid = QGridLayout()
        btn_style = """
            QPushButton { background-color: #4CAF50; border: none; color: white; 
                          padding: 12px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #555; color: #888; }
        """
        shop_btn_style = """
            QPushButton { background-color: #FF9800; border: none; color: white; 
                          padding: 12px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #e68a00; }
            QPushButton:disabled { background-color: #555; color: #888; }
        """
        
        self.feed_btn = QPushButton("🍖 Feed")
        self.feed_btn.clicked.connect(self.feed)
        self.feed_btn.setStyleSheet(btn_style)
        button_grid.addWidget(self.feed_btn, 0, 0)

        self.play_btn = QPushButton("🎾 Play")
        self.play_btn.clicked.connect(self.play)
        self.play_btn.setStyleSheet(btn_style)
        button_grid.addWidget(self.play_btn, 0, 1)

        self.hunt_btn = QPushButton("🏹 Hunt")
        self.hunt_btn.clicked.connect(self.hunt)
        self.hunt_btn.setStyleSheet(btn_style)
        button_grid.addWidget(self.hunt_btn, 1, 0)

        self.sleep_btn = QPushButton("💤 Sleep")
        self.sleep_btn.clicked.connect(self.toggle_sleep)
        self.sleep_btn.setStyleSheet(btn_style)
        button_grid.addWidget(self.sleep_btn, 1, 1)
        
        self.shop_btn = QPushButton("🛒 Shop")
        self.shop_btn.clicked.connect(self.open_shop)
        self.shop_btn.setStyleSheet(shop_btn_style)
        button_grid.addWidget(self.shop_btn, 2, 0, 1, 2)

        layout.addLayout(button_grid)

        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self.update_stats)
        self.decay_timer.start(2000)

        self.poop_timer = QTimer(self)
        self.poop_timer.timeout.connect(self.try_spawn_poop)
        self.poop_timer.start(8000)
        
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.env_widget.advance_time)
        self.time_timer.start(200)

        self.update_ui()

    def create_stat_bar(self, name, color):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(name)
        label.setFont(QFont("Arial", 10))
        layout.addWidget(label)
        bar = QProgressBar()
        bar.setValue(100)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #444; border-radius: 5px; height: 8px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 5px; }}
        """)
        layout.addWidget(bar)
        return {'widget': container, 'bar': bar}

    def change_pet(self, pet_type):
        self.env_widget.set_pet_type(pet_type)
        self.update_ui()

    def change_env(self, env_name):
        self.env_widget.load_environment(env_name)

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_needed:
            self.xp -= self.xp_needed
            self.level += 1
            self.coins += 20 
            self.xp_needed = int(self.xp_needed * 1.5)
            self.env_widget.update_pet_size(self.level)
            
            self.status_label.setText(f"STATUS: LEVEL UP! (Lvl {self.level})")
            self.status_label.setStyleSheet("color: #9C27B0;")
                
            celeb = QLabel("🎉", self.env_widget)
            celeb.setFont(QFont("Arial", 40))
            celeb.move(self.env_widget.pet_label.x(), self.env_widget.pet_label.y() - 20)
            celeb.show()
            anim = QVariantAnimation(celeb)
            anim.setDuration(1500)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            start_y = celeb.y()
            def animate_celeb(progress):
                celeb.move(celeb.x(), int(start_y - 80 * progress))
            anim.valueChanged.connect(animate_celeb)
            anim.finished.connect(celeb.deleteLater)
            anim.start()
            
            QTimer.singleShot(2000, self.update_ui)
        self.update_ui()

    def open_shop(self):
        shop = ShopDialog(self.coins, self)
        if shop.exec_() == QDialog.Accepted:
            item = shop.selected_item
            if item == "Golden Apple 🍎":
                self.coins -= 15
                self.spawn_shop_item("🍎")
            elif item == "Ball of Yarn 🧶":
                self.coins -= 10
                self.spawn_shop_item("🧶")
            elif item == "Medicine 💊":
                self.coins -= 20
                self.is_sick = False
                self.env_widget.is_sick = False
                self.status_label.setText("Status: Cured!")
                self.status_label.setStyleSheet("color: #4CAF50;")
                QTimer.singleShot(1500, self.update_ui)
            self.update_ui()

    def spawn_shop_item(self, emoji):
        if self.is_sleeping: return
        if self.env_widget.spawn_item(emoji):
            self.status_label.setText("Status: Going for shop item...")
            self.update_ui()

    def pet_petted(self):
        self.happiness = min(100.0, self.happiness + 5.0)
        self.gain_xp(5)
        self.status_label.setText("Status: Loved it!")
        QTimer.singleShot(1500, self.update_ui)

    def cleaned_poop(self):
        self.cleanliness = min(100.0, self.cleanliness + 25.0)
        self.happiness = min(100.0, self.happiness + 10.0)
        self.gain_xp(15)
        self.status_label.setText("Status: All clean!")
        QTimer.singleShot(1500, self.update_ui)

    def caught_prey(self):
        self.hunger = min(100.0, self.hunger + 35.0)
        self.happiness = min(100.0, self.happiness + 15.0)
        self.energy = max(0.0, self.energy - 5.0)
        self.coins += 5 
        self.gain_xp(25)
        self.status_label.setText("Status: Caught it! (+5🪙)")
        self.status_label.setStyleSheet("color: #FF9800;")
        QTimer.singleShot(1500, self.update_ui)

    def feed(self):
        if self.is_sleeping: return
        if self.env_widget.spawn_item("🍲"):
            self.status_label.setText("Status: Pathing to food...")
            self.hunger = min(100.0, self.hunger + 20.0)
            self.happiness = min(100.0, self.happiness + 5.0)
            self.gain_xp(10)
            self.update_ui()

    def play(self):
        if self.is_sleeping: return
        if self.energy < 10:
            self.status_label.setText("Too tired to play!")
            return
        if self.env_widget.spawn_item("🎾"):
            self.status_label.setText("Status: Pathing to toy!")
            self.happiness = min(100.0, self.happiness + 20.0)
            self.energy = max(0.0, self.energy - 15.0)
            self.hunger = max(0.0, self.hunger - 5.0)
            self.gain_xp(15)
            self.update_ui()

    def hunt(self):
        if self.is_sleeping: return
        if self.env_widget.spawn_prey():
            self.update_ui()

    def try_spawn_poop(self):
        if not self.is_sleeping and self.cleanliness < 60:
            if random.random() < 0.4:
                self.env_widget.spawn_poop()
                self.cleanliness = max(0.0, self.cleanliness - 15.0)
                self.update_ui()

    def toggle_sleep(self):
        self.is_sleeping = not self.is_sleeping
        self.feed_btn.setEnabled(not self.is_sleeping)
        self.play_btn.setEnabled(not self.is_sleeping)
        self.hunt_btn.setEnabled(not self.is_sleeping)
        self.env_widget.is_sleeping = self.is_sleeping 
        
        if self.is_sleeping:
            self.status_label.setText("Status: Going to sleep...")
            if self.env_widget.move_anim:
                self.env_widget.move_anim.stop()
        else:
            self.status_label.setText("Status: Waking up...")
            
        self.update_ui()

    def update_stats(self):
        if self.cleanliness < 10 and not self.is_sick and not self.is_sleeping:
            self.is_sick = True
            self.env_widget.is_sick = True
            self.status_label.setText("Status: Got sick! 🤢")
            self.status_label.setStyleSheet("color: #8BC34A;")
            QTimer.singleShot(2000, self.update_ui)
        elif self.cleanliness > 50 and self.is_sick:
            self.is_sick = False
            self.env_widget.is_sick = False

        hunger_decay = 2.0
        happy_decay = 1.5
        energy_decay = 1.0
        
        if self.is_sick:
            hunger_decay *= 3
            happy_decay *= 3

        if self.is_sleeping:
            self.energy = min(100.0, self.energy + 10.0)
            self.hunger = max(0.0, self.hunger - 1.0)
            self.happiness = max(0.0, self.happiness - 0.5)
            
            if self.energy >= 100.0 and self.env_widget.time_of_day < 40:
                self.toggle_sleep()
        else:
            self.hunger = max(0.0, self.hunger - hunger_decay)
            self.happiness = max(0.0, self.happiness - happy_decay)
            self.energy = max(0.0, self.energy - energy_decay)
            
            poop_penalty = 2.0 if len(self.env_widget.poops) > 0 else 1.0
            self.cleanliness = max(0.0, self.cleanliness - poop_penalty)
            
            if self.cleanliness < 20:
                self.happiness = max(0.0, self.happiness - 2.0)
            
            if self.env_widget.time_of_day > 80 and self.energy < 50:
                self.env_widget.update_thought_bubble("🥱")
                QTimer.singleShot(1000, self.toggle_sleep)
                
        if self.energy <= 0 and not self.is_sleeping:
            self.toggle_sleep()
            
        self.update_ui()

    def update_ui(self):
        self.hunger_bar['bar'].setValue(int(self.hunger))
        self.happy_bar['bar'].setValue(int(self.happiness))
        self.energy_bar['bar'].setValue(int(self.energy))
        self.clean_bar['bar'].setValue(int(self.cleanliness))
        
        self.lvl_label.setText(f"Lvl {self.level} 🐣")
        self.xp_bar.setValue(int((self.xp / self.xp_needed) * 100))
        self.coin_label.setText(f"🪙 {self.coins}")

        is_sad = self.happiness < 30 or self.energy < 30
        is_hungry = self.hunger < 30
        is_dirty = self.cleanliness < 30
        
        self.env_widget.is_sad = is_sad
        self.env_widget.is_hungry = is_hungry
        self.env_widget.is_dirty = is_dirty

        current_status = self.status_label.text()
        invalid_keywords = ["LEVEL UP", "Pathing", "Loved", "clean", "sleep", "tired", "Hunting", "Caught", "sick", "Cured", "shop"]
        if "STATUS" not in current_status.upper() and "Status:" in current_status and not any(x in current_status for x in invalid_keywords):
            if self.is_sleeping:
                self.status_label.setText("Status: Zzz...")
                self.status_label.setStyleSheet("color: #03A9F4;")
            elif is_sad or is_hungry or is_dirty or self.is_sick:
                self.status_label.setText("Status: Needs attention!")
                self.status_label.setStyleSheet("color: #FF5722;")
            else:
                self.status_label.setText("Status: Happy!")
                self.status_label.setStyleSheet("color: #4CAF50;")

        self.env_widget.update_pet_mood()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VirtualPetApp()
    window.show()
    sys.exit(app.exec())