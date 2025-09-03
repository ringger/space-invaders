#!/usr/bin/env python3
import curses
import time
import random
import json
import os
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class GameObject:
    x: int
    y: int
    char: str
    active: bool = True
    width: int = 1
    height: int = 1
    sprite: List[str] = None
    
    def __post_init__(self):
        if self.sprite is None:
            self.sprite = [self.char]


@dataclass
class Barrier:
    x: int
    y: int
    width: int
    height: int
    blocks: List[List[bool]]  # 2D array representing barrier structure
    
    def __post_init__(self):
        if not self.blocks:
            # Default barrier shape
            self.blocks = [
                [True, True, True, True, True, True, True],
                [True, True, True, True, True, True, True],
                [True, True, True, True, True, True, True],
                [True, True, False, False, False, True, True],
                [True, False, False, False, False, False, True]
            ]
            self.height = len(self.blocks)
            self.width = len(self.blocks[0])
    
    def hit(self, bullet_x: int, bullet_y: int) -> bool:
        """Check if bullet hits barrier and damage it. Returns True if hit."""
        rel_x = bullet_x - self.x
        rel_y = bullet_y - self.y
        
        if (0 <= rel_x < self.width and 0 <= rel_y < self.height):
            if self.blocks[rel_y][rel_x]:
                # Create damage pattern around hit point  
                barrier_config = self.game.config if hasattr(self, 'game') else None
                if barrier_config:
                    damage_direct = barrier_config['barriers']['damage_chance_direct']
                    damage_adjacent = barrier_config['barriers']['damage_chance_adjacent']
                    self.damage_area(rel_x, rel_y, damage_direct, damage_adjacent)
                else:
                    self.damage_area(rel_x, rel_y)
                return True
        return False
    
    def damage_area(self, hit_x: int, hit_y: int, damage_direct: float = 0.8, damage_adjacent: float = 0.4):
        """Create realistic damage pattern around hit point"""
        # Damage the hit point and surrounding area
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                damage_x = hit_x + dx
                damage_y = hit_y + dy
                if (0 <= damage_x < self.width and 0 <= damage_y < self.height):
                    # Higher chance to damage closer to impact
                    damage_chance = damage_direct if (dx == 0 and dy == 0) else damage_adjacent
                    if random.random() < damage_chance:
                        self.blocks[damage_y][damage_x] = False


class SpaceInvaders:
    def __init__(self, stdscr):
        # Load configuration
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.min_width = self.config['display']['min_width']
        self.min_height = self.config['display']['min_height']
        
        # Initialize colors with bold/bright attributes
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Player
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # Invaders - Red
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Bullets / Invaders - Yellow
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)  # UI / Invaders - White
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # UFO
        curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Invaders - Cyan
        curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)   # Invaders - Blue
        
        # Game state
        self.running = True
        self.score = 0
        self.high_score = self.load_high_score()
        self.level = 1
        self.lives = self.config['player']['lives']
        self.player_death_timer = 0
        self.respawn_delay = self.config['player']['respawn_delay']
        
        # UFO bonus ship
        self.ufo = None
        self.ufo_timer = 0
        self.ufo_spawn_time = random.randint(
            self.config['ufo']['spawn_time_min'], 
            self.config['ufo']['spawn_time_max']
        )
        
        # Animation
        self.animation_counter = 0
        self.animation_speed = self.config['invaders']['animation']['base_animation_speed']
        
        # Color ripple effects
        self.ripple_waves = []  # List of active color ripples
        
        # Invader movement
        self.invader_direction = self.config['invaders']['movement']['initial_direction']
        self.invader_move_counter = 0
        self.invader_move_speed = self.config['invaders']['movement']['initial_move_speed']
        self.initial_invader_count = 0  # Will be set when invaders are created
        
        # Player ship sprite from config
        player_sprite = self.config['player']['sprite']
        self.player = GameObject(
            self.width // 2 - 1, 
            self.height - self.config['player']['starting_y_offset'], 
            "▲", 
            width=self.config['player']['width'], 
            height=self.config['player']['height'], 
            sprite=player_sprite
        )
        
        # Game objects
        self.player_bullets = []
        self.invader_bullets = []
        self.invader_bombs = []
        self.invaders = []
        self.barriers = []
        self.explosions = []
        
        self.setup_invaders()
        self.setup_barriers()
    
    def load_high_score(self):
        """Load high score from file"""
        high_score_file = 'highscore.txt'
        if os.path.exists(high_score_file):
            try:
                with open(high_score_file, 'r') as f:
                    return int(f.read().strip())
            except (ValueError, IOError):
                return 0
        return 0
    
    def save_high_score(self):
        """Save high score to file"""
        if self.score > self.high_score:
            self.high_score = self.score
            try:
                with open('highscore.txt', 'w') as f:
                    f.write(str(self.high_score))
            except IOError:
                pass  # Fail silently if we can't save
        
    def setup_invaders(self):
        """Create initial invader formation"""
        self.invaders = []
        
        # Different invader types with menacing wing-flapping sprites (frame 1 and frame 2)
        invader_sprites = [
            # Top row invaders (most points) - Massive wing sweeps
            [
                [
                    "▲ ▲█▲ ▲",
                    "▼▀▄▄▄▀▼",
                    "▀▼▼▼▼▼▀"
                ],
                [
                    "▼ ▼█▼ ▼",
                    "▲▄▀▀▀▄▲",
                    "▀▼▼▼▼▼▀"
                ]
            ],
            # Middle row invaders - Giant wing beats
            [
                [
                    "▲ ▄▄▄ ▲",
                    "▼▀▄▀▄▀▼",
                    "▀▼▲▼▲▼▀"
                ],
                [
                    "▼ ▀▀▀ ▼",
                    "▲▄▀▄▀▄▲",
                    "▀▼▲▼▲▼▀"
                ]
            ],
            # Bottom row invaders (least points) - Extreme wing motion
            [
                [
                    "▲ ▄█▄ ▲",
                    "▼▀███▀▼",
                    "▀▼▼▼▼▼▀"
                ],
                [
                    "▼ ▀█▀ ▼",
                    "▲▄███▄▲",
                    "▀▼▼▼▼▼▀"
                ]
            ]
        ]
        
        formation = self.config['invaders']['formation']
        rows = formation['rows']
        cols = formation['cols']
        sprite_width = formation['sprite_width']
        start_x = (self.width - cols * (sprite_width + formation['col_spacing'])) // 2
        # Invaders start lower each level for increased difficulty
        level_progression = self.config['gameplay']['level_progression_rows_per_level']
        start_y = formation['start_y'] + (self.level - 1) * level_progression
        
        for row in range(rows):
            sprite_type = min(row // 2, 2)  # Use different sprites for different rows
            for col in range(cols):
                x = start_x + col * (sprite_width + formation['col_spacing'])
                y = start_y + row * formation['row_spacing']
                if x > 0 and x + sprite_width < self.width - 1:
                    invader = GameObject(
                        x, y, "▼", 
                        width=formation['sprite_width'], 
                        height=formation['sprite_height'], 
                        sprite=invader_sprites[sprite_type][0]  # Start with first frame
                    )
                    # Store both animation frames
                    invader.sprite_frames = invader_sprites[sprite_type]
                    invader.current_frame = 0
                    # Give each invader its own color cycle timing
                    animation_config = self.config['invaders']['animation']
                    invader.color_timer = random.randint(
                        animation_config['color_timer_min'], 
                        animation_config['color_timer_max']
                    )
                    invader.color_speed = random.randint(
                        animation_config['color_speed_min'], 
                        animation_config['color_speed_max']
                    )
                    invader.current_color = random.choice(self.config['invaders']['animation']['color_palette'])
                    # Add position info for ripple effects
                    invader.grid_x = col
                    invader.grid_y = row
                    self.invaders.append(invader)
        
        # Store initial count for speed calculation
        self.initial_invader_count = len(self.invaders)
    
    def spawn_ufo(self):
        """Spawn a bonus UFO"""
        if self.ufo is None:
            ufo_config = self.config['ufo']
            ufo_sprite = ufo_config['sprite']
            
            # Randomly choose direction (left to right or right to left)
            direction = random.choice([-1, 1])
            start_x = self.width - 1 if direction == -1 else -ufo_config['width']
            
            self.ufo = GameObject(
                start_x, 
                ufo_config['y_position'],
                "◄►", 
                width=ufo_config['width'], 
                height=ufo_config['height'], 
                sprite=ufo_sprite
            )
            self.ufo.direction = direction
            self.ufo.points = random.choice(ufo_config['points'])
    
    def update_ufo(self):
        """Update UFO movement and spawning"""
        self.ufo_timer += 1
        
        # Check if it's time to spawn UFO
        if self.ufo is None and self.ufo_timer >= self.ufo_spawn_time:
            self.spawn_ufo()
            self.ufo_timer = 0
            self.ufo_spawn_time = random.randint(
                self.config['ufo']['spawn_time_min'],
                self.config['ufo']['spawn_time_max']
            )
        
        # Move UFO if it exists
        if self.ufo is not None:
            self.ufo.x += self.ufo.direction
            
            # Remove UFO if it goes off screen
            ufo_config = self.config['ufo']
            if (self.ufo.x < -ufo_config['offscreen_buffer_left'] or 
                self.ufo.x > self.width + ufo_config['offscreen_buffer_right']):
                self.ufo = None
    
    def setup_barriers(self):
        """Create protective barriers"""
        self.barriers = []
        barrier_config = self.config['barriers']
        
        # Position barriers between invaders and player
        barrier_y = self.height - barrier_config['y_offset']
        total_width = (barrier_config['count'] * barrier_config['width'] + 
                      (barrier_config['count'] - 1) * barrier_config['spacing'])
        start_x = (self.width - total_width) // 2
        
        for i in range(barrier_config['count']):
            barrier_x = start_x + i * (barrier_config['width'] + barrier_config['spacing'])
            if barrier_x > 0 and barrier_x + barrier_config['width'] < self.width - 1:
                barrier = Barrier(
                    x=barrier_x,
                    y=barrier_y,
                    width=barrier_config['width'],
                    height=barrier_config['height'],
                    blocks=[]  # Will use default shape
                )
                barrier.game = self  # Pass game instance for config access
                self.barriers.append(barrier)
    
    def handle_input(self):
        """Handle player input"""
        self.stdscr.nodelay(True)
        
        # Process all available input in the queue
        while True:
            key = self.stdscr.getch()
            if key == -1:  # No more input
                break
                
            if key == ord('q'):
                self.running = False
            elif key == curses.KEY_LEFT or key == ord('a'):
                # Move left (only if player is alive)
                margin_left = self.config['player']['movement_margin_left']
                if self.player.active and self.player.x > margin_left:
                    self.player.x -= 1
            elif key == curses.KEY_RIGHT or key == ord('d'):
                # Move right (only if player is alive)
                margin_right = self.config['player']['movement_margin_right']
                if self.player.active and self.player.x + self.player.width < self.width - margin_right:
                    self.player.x += 1
            elif key == ord(' '):
                # Fire bullet from center of ship (only if player is alive and not too many bullets on screen)
                if self.player.active and len(self.player_bullets) < self.config['player']['max_bullets']:
                    self.player_bullets.append(
                        GameObject(self.player.x + self.player.width // 2, self.player.y - 1, "│")
                    )
    
    def update_bullets(self):
        """Update bullet positions"""
        # Update player bullets
        for bullet in self.player_bullets[:]:
            bullet.y -= 1
            if bullet.y < 0:
                self.player_bullets.remove(bullet)
        
        # Update invader bullets
        for bullet in self.invader_bullets[:]:
            bullet.y += 1
            if bullet.y >= self.height - 1:
                self.invader_bullets.remove(bullet)
        
        # Update invader bombs
        bomb_config = self.config['weapons']['bombs']
        for bomb in self.invader_bombs[:]:
            bomb.y += 1
            if bomb.y >= self.height - 1:
                # Bomb hit ground - create explosion
                self.create_explosion(bomb.x, bomb.y - 1, bomb_config['explosion_radius_impact'])
                self.invader_bombs.remove(bomb)
        
        # Update explosions
        for explosion in self.explosions[:]:
            explosion['timer'] -= 1
            if explosion['timer'] <= 0:
                self.explosions.remove(explosion)
    
    def check_collisions(self):
        """Check for collisions between bullets and targets"""
        # Check player bullets hitting barriers
        for bullet in self.player_bullets[:]:
            for barrier in self.barriers:
                if barrier.hit(bullet.x, bullet.y):
                    self.player_bullets.remove(bullet)
                    break
        
        # Check invader bullets hitting barriers  
        for bullet in self.invader_bullets[:]:
            for barrier in self.barriers:
                if barrier.hit(bullet.x, bullet.y):
                    self.invader_bullets.remove(bullet)
                    break
        
        # Check invader bombs hitting barriers
        bomb_config = self.config['weapons']['bombs']
        for bomb in self.invader_bombs[:]:
            for barrier in self.barriers:
                if barrier.hit(bomb.x, bomb.y):
                    self.create_explosion(bomb.x, bomb.y, bomb_config['explosion_radius_impact'])
                    self.invader_bombs.remove(bomb)
                    break
        
        # Check player bullets hitting bombs
        bomb_config = self.config['weapons']['bombs']
        for bullet in self.player_bullets[:]:
            for bomb in self.invader_bombs[:]:
                if bullet.x == bomb.x and bullet.y == bomb.y:
                    self.player_bullets.remove(bullet)
                    self.create_explosion(bomb.x, bomb.y, bomb_config['explosion_radius_shot'])
                    self.invader_bombs.remove(bomb)
                    break
        
        # Check player bullets hitting UFO
        if self.ufo is not None:
            for bullet in self.player_bullets[:]:
                if (self.ufo.x <= bullet.x < self.ufo.x + self.ufo.width and
                    self.ufo.y <= bullet.y < self.ufo.y + self.ufo.height):
                    self.player_bullets.remove(bullet)
                    self.score += self.ufo.points
                    self.ufo = None  # Remove UFO
                    break
        
        # Check player bullets hitting invaders
        for bullet in self.player_bullets[:]:
            for invader in self.invaders[:]:
                # Check if bullet hits any part of the invader sprite
                if (invader.x <= bullet.x < invader.x + invader.width and
                    invader.y <= bullet.y < invader.y + invader.height):
                    self.player_bullets.remove(bullet)
                    
                    # Create invader death explosion
                    explosion_radius = self.config['invaders']['animation']['death_explosion_radius']
                    self.create_explosion(
                        invader.x + invader.width // 2,
                        invader.y + invader.height // 2,
                        explosion_radius
                    )
                    
                    # Award points based on invader row
                    score_config = self.config['gameplay']['score_per_invader']
                    if invader.grid_y <= 1:  # Top rows (0, 1)
                        points = score_config['top_rows']
                    elif invader.grid_y <= 3:  # Middle rows (2, 3)
                        points = score_config['middle_rows']
                    else:  # Bottom row (4)
                        points = score_config['bottom_rows']
                    
                    self.score += points
                    self.invaders.remove(invader)
                    break
        
        # Check invader bullets hitting player
        for bullet in self.invader_bullets[:]:
            # Check if bullet hits any part of the player sprite
            if (self.player.active and
                self.player.x <= bullet.x < self.player.x + self.player.width and
                self.player.y <= bullet.y < self.player.y + self.player.height):
                self.invader_bullets.remove(bullet)
                self.player_hit()
                break
        
        # Check bombs hitting player
        bomb_config = self.config['weapons']['bombs']
        for bomb in self.invader_bombs[:]:
            if (self.player.active and
                self.player.x <= bomb.x < self.player.x + self.player.width and
                self.player.y <= bomb.y < self.player.y + self.player.height):
                self.create_explosion(bomb.x, bomb.y, bomb_config['explosion_radius_impact'])
                self.invader_bombs.remove(bomb)
                self.player_hit()
                break
        
        # Check explosions hitting player
        for explosion in self.explosions:
            if self.player.active and explosion['timer'] > 0:
                dist = ((self.player.x - explosion['x']) ** 2 + 
                       (self.player.y - explosion['y']) ** 2) ** 0.5
                if dist <= explosion['radius']:
                    self.player_hit()
                    break
    
    def update_invaders(self):
        """Move invaders and occasionally fire"""
        self.invader_move_counter += 1
        self.animation_counter += 1
        
        # Update animation frames and individual color cycling
        if self.animation_counter >= self.animation_speed:
            self.animation_counter = 0
            for invader in self.invaders:
                if hasattr(invader, 'sprite_frames'):
                    invader.current_frame = 1 - invader.current_frame  # Toggle between 0 and 1
                    invader.sprite = invader.sprite_frames[invader.current_frame]
        
        # Randomly create ripple waves
        ripple_config = self.config['effects']['ripples']
        if random.random() < ripple_config['spawn_chance']:
            formation = self.config['invaders']['formation']
            center_x = random.randint(0, formation['cols'] - 1)
            center_y = random.randint(0, formation['rows'] - 1)
            new_color = random.choice(self.config['invaders']['animation']['color_palette'])
            self.ripple_waves.append({
                'center_x': center_x,
                'center_y': center_y,
                'radius': 0,
                'color': new_color,
                'speed': ripple_config['speed'],
                'max_radius': ripple_config['max_radius']
            })
        
        # Update ripple waves
        for ripple in self.ripple_waves[:]:
            ripple['radius'] += ripple['speed']
            if ripple['radius'] > ripple['max_radius']:
                self.ripple_waves.remove(ripple)
                continue
                
            # Apply ripple color to invaders within radius
            for invader in self.invaders:
                if hasattr(invader, 'grid_x') and hasattr(invader, 'grid_y'):
                    dist = ((invader.grid_x - ripple['center_x']) ** 2 + 
                           (invader.grid_y - ripple['center_y']) ** 2) ** 0.5
                    # Check if invader is at the current ripple edge
                    edge_threshold = self.config['effects']['ripples']['edge_threshold']
                    if abs(dist - ripple['radius']) < edge_threshold:
                        invader.current_color = ripple['color']
                        # Reset individual timer to prevent immediate color change
                        invader.color_timer = 0
        
        # Update individual invader color cycling (slower now due to ripples)
        color_multiplier = self.config['invaders']['animation']['color_cycle_speed_multiplier']
        color_palette = self.config['invaders']['animation']['color_palette']
        
        for invader in self.invaders:
            if hasattr(invader, 'color_timer'):
                invader.color_timer += 1
                if invader.color_timer >= invader.color_speed * color_multiplier:
                    invader.color_timer = 0
                    # Cycle through colors from palette
                    current_index = color_palette.index(invader.current_color)
                    next_index = (current_index + 1) % len(color_palette)
                    invader.current_color = color_palette[next_index]
        
        # Calculate dynamic speed based on remaining invaders
        current_invader_count = len(self.invaders)
        if current_invader_count > 0 and self.initial_invader_count > 0:
            # Speed increases as fewer invaders remain (speed multiplier gets higher)
            speed_multiplier = self.initial_invader_count / current_invader_count
            current_speed = max(0, int(self.invader_move_speed / speed_multiplier))
            # For extreme speed, take bigger steps
            movement_config = self.config['invaders']['movement']
            threshold = movement_config['step_size_threshold']
            max_step = movement_config['max_step_size']
            if current_speed == 0 and speed_multiplier > threshold:
                speed_divider = self.config['gameplay']['invader_speed_calculation_divider']
                self.step_size = min(max_step, int(speed_multiplier / speed_divider))
            else:
                self.step_size = 1
        else:
            current_speed = self.invader_move_speed
            self.step_size = 1
        
        # Move invaders in formation
        if self.invader_move_counter >= current_speed:
            self.invader_move_counter = 0
            
            # Flap wings on every movement step
            for invader in self.invaders:
                if hasattr(invader, 'sprite_frames'):
                    invader.current_frame = 1 - invader.current_frame  # Toggle between 0 and 1
                    invader.sprite = invader.sprite_frames[invader.current_frame]
            
            # Check if we need to drop down and change direction (account for step size)
            should_drop = False
            for invader in self.invaders:
                if (self.invader_direction == 1 and 
                    invader.x + invader.width + self.step_size >= self.width - 2):
                    should_drop = True
                    break
                elif (self.invader_direction == -1 and 
                      invader.x - self.step_size <= 2):
                    should_drop = True
                    break
            
            if should_drop:
                # Drop down and change direction
                for invader in self.invaders:
                    invader.y += 1
                self.invader_direction *= -1
                # Speed up slightly each time they drop
                movement_config = self.config['invaders']['movement']
                self.invader_move_speed = max(
                    movement_config['min_move_speed'], 
                    self.invader_move_speed - movement_config['speed_reduction_per_drop']
                )
            else:
                # Move horizontally with dynamic step size
                for invader in self.invaders:
                    invader.x += self.invader_direction * self.step_size
        
        # Occasionally fire bullets and bombs from center of invader
        weapons_config = self.config['invaders']['weapons']
        for invader in self.invaders:
            if random.random() < weapons_config['bullet_chance']:
                self.invader_bullets.append(
                    GameObject(
                        invader.x + invader.width // 2, 
                        invader.y + invader.height, 
                        self.config['weapons']['bullets']['invader_char']
                    )
                )
            elif random.random() < weapons_config['bomb_chance']:
                bomb = GameObject(
                    invader.x + invader.width // 2, 
                    invader.y + invader.height, 
                    self.config['weapons']['bombs']['char']
                )
                bomb.bomb_type = "heavy"  # Mark as bomb for visual distinction
                self.invader_bombs.append(bomb)
    
    def player_hit(self):
        """Handle player being hit"""
        self.player.active = False
        self.player_death_timer = self.respawn_delay
        self.lives -= 1
        
        # Create player death explosion
        explosion_radius = self.config['player']['death_explosion_radius']
        self.create_explosion(
            self.player.x + self.player.width // 2,
            self.player.y + self.player.height // 2,
            explosion_radius
        )
        
        # Clear player bullets when hit
        self.player_bullets.clear()
    
    def update_player(self):
        """Update player state including respawn timer"""
        if not self.player.active and self.player_death_timer > 0:
            self.player_death_timer -= 1
            if self.player_death_timer <= 0:
                if self.lives > 0:
                    # Respawn player
                    self.player.active = True
                    self.player.x = self.width // 2 - 1
                else:
                    # Game over
                    self.running = False
    
    def create_explosion(self, x, y, radius):
        """Create an explosion with blast radius"""
        bomb_config = self.config['weapons']['bombs']
        self.explosions.append({
            'x': x,
            'y': y,
            'radius': radius,
            'timer': bomb_config['explosion_duration'],
            'max_timer': bomb_config['explosion_duration']
        })
        
        # Damage barriers in blast radius
        for barrier in self.barriers:
            for row in range(barrier.height):
                for col in range(barrier.width):
                    if barrier.blocks[row][col]:
                        block_x = barrier.x + col
                        block_y = barrier.y + row
                        dist = ((block_x - x) ** 2 + (block_y - y) ** 2) ** 0.5
                        if dist <= radius:
                            barrier.blocks[row][col] = False
    
    def check_screen_size(self):
        """Check if screen was resized and update dimensions"""
        try:
            new_height, new_width = self.stdscr.getmaxyx()
            if new_height != self.height or new_width != self.width:
                self.height, self.width = new_height, new_width
                # Check minimum size
                if self.height < self.min_height or self.width < self.min_width:
                    return False
                # Reposition player if needed
                margin_left = self.config['player']['movement_margin_left']
                margin_right = self.config['player']['movement_margin_right']
                y_offset = self.config['gameplay']['screen_resize_player_y_offset']
                
                if self.player.x + self.player.width >= self.width:
                    self.player.x = max(margin_left, self.width - self.player.width - margin_right)
                if self.player.y >= self.height:
                    self.player.y = self.height - y_offset
                # Remove objects that are now off-screen
                self.player_bullets = [b for b in self.player_bullets 
                                     if 0 <= b.x < self.width and 0 <= b.y < self.height]
                self.invader_bullets = [b for b in self.invader_bullets 
                                      if 0 <= b.x < self.width and 0 <= b.y < self.height]
            return True
        except curses.error:
            return False
    
    def draw(self):
        """Draw all game objects"""
        # Check for screen resize
        if not self.check_screen_size():
            return  # Skip drawing if screen too small
            
        try:
            # Use erase() instead of clear() to reduce flickering
            self.stdscr.erase()
        
            # Draw borders (with extra bounds checking)
            for x in range(min(self.width - 1, self.width)):
                if x < self.width - 1:
                    self.stdscr.addch(0, x, "─", curses.color_pair(4))
                if x < self.width - 1 and self.height > 1:
                    self.stdscr.addch(self.height - 1, x, "─", curses.color_pair(4))
            
            for y in range(min(self.height - 1, self.height)):
                if y < self.height - 1:
                    self.stdscr.addch(y, 0, "│", curses.color_pair(4))
                if y < self.height - 1 and self.width > 1:
                    self.stdscr.addch(y, self.width - 1, "│", curses.color_pair(4))
            
            # Draw player sprite (with bounds checking)
            if self.player.active:
                for i, line in enumerate(self.player.sprite):
                    y = self.player.y + i
                    if 0 <= y < self.height - 1:
                        for j, char in enumerate(line):
                            x = self.player.x + j
                            if 0 <= x < self.width - 1 and char != ' ':
                                self.stdscr.addch(y, x, char, curses.color_pair(1))
            
            # Draw invader sprites (with bounds checking and individual colors)
            for invader in self.invaders:
                if invader.active:
                    # Use invader's current color with bold attribute for brightness
                    color = invader.current_color if hasattr(invader, 'current_color') else 2
                    for i, line in enumerate(invader.sprite):
                        y = invader.y + i
                        if 0 <= y < self.height - 1:
                            for j, char in enumerate(line):
                                x = invader.x + j
                                if 0 <= x < self.width - 1 and char != ' ':
                                    self.stdscr.addch(y, x, char, curses.color_pair(color) | curses.A_BOLD)
            
            # Draw barriers
            for barrier in self.barriers:
                for row in range(barrier.height):
                    for col in range(barrier.width):
                        if barrier.blocks[row][col]:
                            y = barrier.y + row
                            x = barrier.x + col
                            if 0 <= y < self.height - 1 and 0 <= x < self.width - 1:
                                self.stdscr.addch(y, x, "█", curses.color_pair(1))
            
            # Draw UFO if present
            if self.ufo is not None:
                for i, line in enumerate(self.ufo.sprite):
                    y = self.ufo.y + i
                    if 0 <= y < self.height - 1:
                        for j, char in enumerate(line):
                            x = self.ufo.x + j
                            if 0 <= x < self.width - 1 and char != ' ':
                                self.stdscr.addch(y, x, char, curses.color_pair(5))
            
            # Draw bullets (with bounds checking)
            for bullet in self.player_bullets:
                if (bullet.active and 0 <= bullet.y < self.height - 1 and 
                    0 <= bullet.x < self.width - 1):
                    self.stdscr.addch(bullet.y, bullet.x, bullet.char, curses.color_pair(3))
            
            for bullet in self.invader_bullets:
                if (bullet.active and 0 <= bullet.y < self.height - 1 and 
                    0 <= bullet.x < self.width - 1):
                    self.stdscr.addch(bullet.y, bullet.x, bullet.char, curses.color_pair(2))
            
            # Draw bombs
            for bomb in self.invader_bombs:
                if (bomb.active and 0 <= bomb.y < self.height - 1 and 
                    0 <= bomb.x < self.width - 1):
                    self.stdscr.addch(bomb.y, bomb.x, bomb.char, curses.color_pair(2) | curses.A_BOLD)
            
            # Draw explosions
            for explosion in self.explosions:
                if explosion['timer'] > 0:
                    # Draw explosion pattern
                    ex, ey = explosion['x'], explosion['y']
                    radius = explosion['radius']
                    # Use different chars based on explosion timer for animation
                    bomb_config = self.config['weapons']['bombs']
                    thresholds = self.config['effects']['explosions']['frame_thresholds']
                    explosion_chars = bomb_config['explosion_chars']
                    
                    if explosion['timer'] > thresholds[0]:
                        exp_char = explosion_chars[0]
                    elif explosion['timer'] > thresholds[1]:
                        exp_char = explosion_chars[1]
                    else:
                        exp_char = explosion_chars[2]
                    
                    # Draw explosion in circular pattern
                    for dx in range(-radius, radius + 1):
                        for dy in range(-radius, radius + 1):
                            if dx * dx + dy * dy <= radius * radius:
                                exp_x, exp_y = ex + dx, ey + dy
                                if (0 <= exp_x < self.width - 1 and 
                                    0 <= exp_y < self.height - 1):
                                    self.stdscr.addch(exp_y, exp_x, exp_char, curses.color_pair(3) | curses.A_BOLD)
            
            # Draw UI
            score_text = f"Score: {self.score}  High: {self.high_score}"
            level_text = f"Level: {self.level}"
            lives_text = f"Lives: {self.lives}"
            controls_text = "Controls: A/D or ←/→ to move, SPACE to shoot, Q to quit"
            
            self.stdscr.addstr(1, 2, score_text, curses.color_pair(4))
            self.stdscr.addstr(1, self.width // 2 - len(lives_text) // 2, lives_text, curses.color_pair(4))
            self.stdscr.addstr(1, self.width - len(level_text) - 2, level_text, curses.color_pair(4))
            
            if len(controls_text) < self.width - 4:
                self.stdscr.addstr(self.height - 2, 2, controls_text, curses.color_pair(4))
            
            # Use noutrefresh() followed by doupdate() for better performance
            self.stdscr.noutrefresh()
            curses.doupdate()
        except curses.error:
            # Skip drawing if there's a curses error (e.g., during resize)
            pass
    
    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_input()
            self.update_bullets()
            self.update_invaders()
            self.update_ufo()
            self.check_collisions()
            self.draw()
            
            # Check win condition
            if not self.invaders:
                self.level += 1
                self.setup_invaders()
                self.setup_barriers()  # Reset barriers for new level
                # Reset invader movement for new level
                self.invader_direction = 1
                movement_config = self.config['invaders']['movement']
                self.invader_move_speed = max(
                    movement_config['min_move_speed'], 
                    movement_config['initial_move_speed'] - self.level * movement_config['speed_reduction_per_drop']
                )
            
            # Check lose condition (invaders reach player level or barriers)
            for invader in self.invaders:
                # Check if invaders reached player
                if (invader.y + invader.height >= self.player.y and 
                    invader.x < self.player.x + self.player.width and 
                    invader.x + invader.width > self.player.x):
                    # Direct collision with player - game over
                    self.lives = 0
                    self.running = False
                    break
                elif invader.y >= self.player.y:
                    # Invaders reached bottom - game over regardless of lives
                    self.lives = 0
                    self.running = False
                    break
                
                # Check if invaders reached barriers
                for barrier in self.barriers:
                    if (invader.y + invader.height >= barrier.y and 
                        invader.x < barrier.x + barrier.width and 
                        invader.x + invader.width > barrier.x):
                        # Invaders reached barriers - game over
                        self.lives = 0
                        self.running = False
                        break
                
                if not self.running:  # Break outer loop if game ended
                    break
            
            # Update player (respawn logic)
            self.update_player()
            
            time.sleep(self.config['gameplay']['game_speed'])  # Control game speed
        
        # Save high score when game ends
        self.save_high_score()


def main(stdscr):
    # Setup curses
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)
    curses.start_color()
    
    # Enable additional settings to reduce flickering
    stdscr.leaveok(True)  # Don't update cursor position
    stdscr.immedok(False)  # Don't automatically refresh
    
    # Check terminal size
    height, width = stdscr.getmaxyx()
    if height < 20 or width < 40:
        stdscr.addstr(0, 0, "Terminal too small! Need at least 40x20")
        stdscr.getch()
        return
    
    # Create and run game
    game = SpaceInvaders(stdscr)
    game.run()
    
    # Game over screen
    stdscr.clear()
    game_over_text = "GAME OVER!"
    final_score_text = f"Final Score: {game.score}"
    restart_text = "Press any key to exit"
    
    stdscr.addstr(height // 2 - 1, (width - len(game_over_text)) // 2, game_over_text)
    stdscr.addstr(height // 2, (width - len(final_score_text)) // 2, final_score_text)
    stdscr.addstr(height // 2 + 1, (width - len(restart_text)) // 2, restart_text)
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)