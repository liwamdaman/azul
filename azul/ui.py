import pygame
import sys
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
import math
import json
import copy
import os
from .models import TileColor, Player, Tile
from .game import AzulGame, Factory
from .ai import AIPlayer, GreedyAI, StrategicAI, RandomAI

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60

# Base tile size (will be scaled based on window size)
BASE_TILE_SIZE = 18

# Layout constants
FACTORY_SIZE = 80
FACTORY_START_X = 50
FACTORY_START_Y = 50
FACTORY_SPACING = 20

CENTER_X = 480
CENTER_Y = 50
CENTER_WIDTH = 150
CENTER_HEIGHT = 100

PLAYER_WIDTH = 450
PLAYER_HEIGHT = 250
PLAYER_MARGIN_BOTTOM = 120
PLAYER_SPACING = 50
PLAYER_START_X = 50

PATTERN_LINE_HEIGHT = 28
PATTERN_LINE_OFFSET_X = 10
PATTERN_LINE_OFFSET_Y = 40
PATTERN_LINE_WIDTH = 165

FLOOR_LINE_OFFSET_Y = 45

# Button layout constants
BUTTON_CENTER_X = WINDOW_WIDTH // 2 - 100
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50
BUTTON_HEIGHT_SMALL = 40

# Screen center constants
SCREEN_CENTER_X = WINDOW_WIDTH // 2
SCREEN_CENTER_Y = WINDOW_HEIGHT // 2

# Colors
COLORS = {
    'background': (240, 235, 220),
    'board': (139, 69, 19),
    'factory': (160, 82, 45),
    'center': (205, 133, 63),
    'pattern_line': (222, 184, 135),
    'wall': (245, 245, 220),
    'floor': (139, 69, 19),
    'button': (70, 130, 180),
    'button_hover': (100, 149, 237),
    'text': (0, 0, 0),
    'white': (255, 255, 255),
    'selected': (255, 215, 0),
}

# Tile colors
TILE_COLORS = {
    TileColor.BLUE: (30, 144, 255),
    TileColor.YELLOW: (255, 215, 0),
    TileColor.RED: (220, 20, 60),
    TileColor.BLACK: (47, 79, 79),
    TileColor.CYAN: (0, 206, 209),
    TileColor.FIRST_PLAYER: (255, 255, 255),
}

@dataclass
class UIElement:
    """Base class for UI elements."""
    x: int
    y: int
    width: int
    height: int
    
    def contains_point(self, x: int, y: int) -> bool:
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)

@dataclass
class Button(UIElement):
    """Clickable button."""
    text: str
    color: Tuple[int, int, int] = COLORS['button']
    text_color: Tuple[int, int, int] = COLORS['white']
    font_size: int = 24
    
    def draw(self, screen: pygame.Surface, font: pygame.font.Font, hovered: bool = False):
        color = COLORS['button_hover'] if hovered else self.color
        pygame.draw.rect(screen, color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, COLORS['text'], (self.x, self.y, self.width, self.height), 2)
        
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
        screen.blit(text_surface, text_rect)

class AzulUI:
    """Main UI class for the Azul game."""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Azul - Board Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 18)
        
        self.game: Optional[AzulGame] = None
        self.ai_players: Dict[int, AIPlayer] = {}
        self.selected_factory: Optional[int] = None
        self.selected_color: Optional[TileColor] = None
        self.selected_pattern_line: Optional[int] = None
        
        # AI turn visualization
        self.ai_turn_state = "idle"  # idle, thinking, selecting_source, selecting_color, executing
        self.ai_highlighted_factory: Optional[int] = None
        self.ai_highlighted_color: Optional[TileColor] = None
        self.ai_turn_timer = 0
        self.ai_step_duration = 500  # milliseconds per step (will be overridden by settings)
        
        # Round transition animations
        self.round_transition_state = "idle"  # idle, moving_tiles, scoring_rows, scoring_floor, clearing_floor, setup_next
        self.transition_timer = 0
        self.transition_step_duration = 1200  # milliseconds per animation step (slower)
        self.row_scoring_duration = 800  # milliseconds per row scoring
        self.moving_tiles = []  # List of tiles being animated
        self.score_animations = []  # List of score increment animations
        self.scoring_queue = []  # Queue of rows to score sequentially
        self.current_scoring_index = 0  # Current row being scored
        self.floor_penalty_animations = []  # List of floor penalty animations
        
        # Settings
        self.settings = self.load_settings()
        
        # Apply loaded settings to instance variables
        self.ai_step_duration = self.settings['ai_step_duration']
        
        # Wall pattern display options
        self.wall_pattern_mode = "outlines"  # "off", "subtle", "letters", "outlines"
        
        # UI state
        self.game_state = "menu"  # menu, setup, settings, playing, round_complete, game_over
        
        # End game bonus animation state
        self.end_game_animation_state = "idle"  # idle, calculating_bonuses, showing_results
        self.end_game_timer = 0
        self.end_game_bonus_animations = []  # List of bonus animations
        self.end_game_bonuses_calculated = False
        
        # Initialize AI players
        self.ai_players = {}
        
        # Initialize buttons
        self.buttons = []
        self.setup_buttons()
        
        # Undo functionality
        self.move_history: List[Dict] = []
        self.can_undo = False
        
        # Setup state
        self.player_configs = [
            {"type": "Human", "ai_type": "Random"},  # Player 1
            {"type": "AI", "ai_type": "Random"}      # Player 2
        ]
        self.setup_step = 0  # 0: player configuration
    
    def get_tile_size(self) -> int:
        """Calculate responsive tile size based on window dimensions."""
        # Scale tile size based on window size relative to base dimensions
        width_scale = WINDOW_WIDTH / 1200.0
        height_scale = WINDOW_HEIGHT / 800.0
        scale_factor = min(width_scale, height_scale)  # Use smaller scale to ensure everything fits
        
        # Apply scale factor to base tile size with reasonable bounds
        tile_size = int(BASE_TILE_SIZE * scale_factor)
        return max(12, min(tile_size, 24))  # Clamp between 12 and 24 pixels
    
        
    def load_settings(self) -> Dict:
        """Load settings from file or return defaults."""
        default_settings = {
            "ai_animations_enabled": True,
            "ai_step_duration": 500,
            "transition_animations_enabled": True
        }
        
        settings_file = "azul_settings.json"
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to handle missing keys
                    default_settings.update(loaded_settings)
        except (json.JSONDecodeError, IOError):
            pass  # Use defaults if file is corrupted or unreadable
        
        return default_settings
    
    def save_settings(self):
        """Save current settings to file."""
        try:
            with open("azul_settings.json", 'w') as f:
                json.dump(self.settings, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't save
    
    def save_game(self):
        """Save current game state to file."""
        if not self.game:
            return False
        
        try:
            game_state = {
                'players': [],
                'factories': [],
                'center': [],
                'bag': [tile.color.value for tile in self.game.bag],
                'discard_pile': [tile.color.value for tile in self.game.discard_pile],
                'current_player_idx': self.game.current_player_idx,
                'round_number': getattr(self.game, 'round_number', 1),
                'game_ended': self.game.game_over,
                'player_configs': self.player_configs
            }
            
            # Save player states
            for player in self.game.players:
                player_data = {
                    'name': player.name,
                    'score': player.score,
                    'pattern_lines': [[tile.color.value for tile in line.tiles] for line in player.pattern_lines],
                    'floor_line': [tile.color.value for tile in player.floor_line],
                    'wall_grid': [[tile.color.value if tile else None for tile in row] for row in player.wall.grid]
                }
                game_state['players'].append(player_data)
            
            # Save factory states
            for factory in self.game.factories:
                factory_data = [tile.color.value for tile in factory.tiles]
                game_state['factories'].append(factory_data)
            
            # Save center state
            game_state['center'] = [tile.color.value for tile in self.game.center.tiles]
            game_state['center_has_first_player'] = self.game.center.first_player_taken
            
            with open("azul_savegame.json", 'w') as f:
                json.dump(game_state, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save game: {e}")
            return False
    
    def load_game(self):
        """Load game state from file."""
        try:
            if not os.path.exists("azul_savegame.json"):
                return False
            
            with open("azul_savegame.json", 'r') as f:
                game_state = json.load(f)
            
            # Create new game with saved player configs
            self.player_configs = game_state.get('player_configs', self.player_configs)
            self.game = AzulGame(["Player 1", "Player 2"])
            
            # Restore players
            for i, player_data in enumerate(game_state['players']):
                player = self.game.players[i]
                player.name = player_data['name']
                player.score = player_data['score']
                
                # Restore pattern lines
                for j, line_data in enumerate(player_data['pattern_lines']):
                    player.pattern_lines[j].tiles = [Tile(TileColor(color)) for color in line_data]
                
                # Restore floor line
                player.floor_line = [Tile(TileColor(color)) for color in player_data['floor_line']]
                
                # Restore wall
                for row_idx, row_data in enumerate(player_data['wall_grid']):
                    for col_idx, tile_color in enumerate(row_data):
                        if tile_color is not None:
                            player.wall.grid[row_idx][col_idx] = Tile(TileColor(tile_color))
            
            # Restore factories
            for i, factory_data in enumerate(game_state['factories']):
                self.game.factories[i].tiles = [Tile(TileColor(color)) for color in factory_data]
            
            # Restore center
            self.game.center.tiles = [Tile(TileColor(color)) for color in game_state['center']]
            self.game.center.first_player_taken = game_state['center_has_first_player']
            
            # Restore bag and discard pile
            self.game.bag = [Tile(TileColor(color)) for color in game_state['bag']]
            self.game.discard_pile = [Tile(TileColor(color)) for color in game_state['discard_pile']]
            
            # Restore game state
            self.game.current_player_idx = game_state['current_player_idx']
            self.game.round_number = game_state.get('round_number', 1)
            self.game.game_over = game_state['game_ended']
            
            # Initialize AI players based on configs
            for i, config in enumerate(self.player_configs):
                if config["type"] == "AI":
                    ai_type = config["ai_type"]
                    if ai_type == "Random":
                        self.ai_players[i] = RandomAI(f"AI Player {i+1}")
                    elif ai_type == "Greedy":
                        self.ai_players[i] = GreedyAI(f"AI Player {i+1}")
                    elif ai_type == "Strategic":
                        self.ai_players[i] = StrategicAI(f"AI Player {i+1}")
            
            return True
        except Exception as e:
            print(f"Failed to load game: {e}")
            return False
    
    def setup_buttons(self):
        """Setup initial menu buttons."""
        self.buttons = [
            Button(BUTTON_CENTER_X, 280, BUTTON_WIDTH, BUTTON_HEIGHT, "Start Game"),
            Button(BUTTON_CENTER_X, 350, BUTTON_WIDTH, BUTTON_HEIGHT, "Load Game"),
            Button(BUTTON_CENTER_X, 420, BUTTON_WIDTH, BUTTON_HEIGHT, "Settings"),
            Button(BUTTON_CENTER_X, 490, BUTTON_WIDTH, BUTTON_HEIGHT, "Quit")
        ]
    
    def run(self):
        """Main game loop."""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state == "playing":
                            self.game_state = "menu"
                            self.setup_buttons()
            
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()
    
    def handle_click(self, pos: Tuple[int, int]):
        """Handle mouse clicks."""
        x, y = pos
        
        if self.game_state == "menu":
            self.handle_menu_click(x, y)
        elif self.game_state == "setup":
            self.handle_setup_click(x, y)
        elif self.game_state == "settings":
            self.handle_settings_click(x, y)
        elif self.game_state == "playing":
            self.handle_game_click(x, y)
        elif self.game_state == "round_complete":
            self.handle_round_complete_click(x, y)
    
    def handle_menu_click(self, x: int, y: int):
        """Handle menu clicks."""
        for button in self.buttons:
            if button.contains_point(x, y):
                if button.text == "Start Game":
                    self.game_state = "setup"
                    self.setup_game_setup_buttons()
                elif button.text == "Load Game":
                    if self.load_game():
                        self.game_state = "playing"
                        self.setup_game_buttons()
                elif button.text == "Settings":
                    self.game_state = "settings"
                    self.setup_settings_buttons()
                elif button.text == "Quit":
                    import sys
                    sys.exit()
    
    def handle_round_complete_click(self, x: int, y: int):
        """Handle round complete screen clicks."""
        for button in self.buttons:
            if button.contains_point(x, y):
                if button.text == "Start Next Round":
                    # Start the next round
                    self.game.current_player_idx = self.game.first_player_idx
                    self.game.setup_round()
                    self.game_state = "playing"
                    self.setup_game_buttons()  # Setup game control buttons
                elif button.text == "View Final Results":
                    self.start_end_game_animation()
                    self.buttons = []  # Clear buttons
                elif button.text == "Back to Menu":
                    self.game_state = "menu"
                    self.setup_buttons()
    
    def setup_round_complete_buttons(self):
        """Setup buttons for round complete state."""
        if self.game.game_over:
            button_text = "View Final Results"
        else:
            button_text = "Start Next Round"
        
        self.buttons = [
            Button(BUTTON_CENTER_X, WINDOW_HEIGHT - 150, BUTTON_WIDTH, BUTTON_HEIGHT, button_text),
            Button(BUTTON_CENTER_X, WINDOW_HEIGHT - 90, BUTTON_WIDTH, BUTTON_HEIGHT_SMALL, "Back to Menu")
        ]
    
    def setup_settings_buttons(self):
        """Setup settings screen buttons."""
        pattern_mode_text = {
            "off": "OFF",
            "subtle": "Subtle Colors", 
            "letters": "Color Letters",
            "outlines": "Color Outlines"
        }
        
        self.buttons = [
            Button(50, 200, 300, 40, f"AI Animations: {'ON' if self.settings['ai_animations_enabled'] else 'OFF'}"),
            Button(50, 260, 300, 40, f"Round Animations: {'ON' if self.settings['transition_animations_enabled'] else 'OFF'}"),
            Button(50, 320, 300, 40, f"AI Speed: {self.settings['ai_step_duration']}ms"),
            Button(50, 380, 300, 40, f"Wall Pattern: {pattern_mode_text[self.wall_pattern_mode]}"),
            Button(BUTTON_CENTER_X, 480, BUTTON_WIDTH, BUTTON_HEIGHT, "Back to Menu")
        ]
    
    def setup_game_setup_buttons(self):
        """Setup game setup screen buttons."""
        self.buttons = []
        
        # Player configuration buttons
        for i in range(2):
            player_num = i + 1
            y_base = 200 + i * 120
            
            # Human/AI toggle button
            player_type = self.player_configs[i]["type"]
            type_button = Button(100, y_base, 120, 40, f"P{player_num}: {player_type}")
            self.buttons.append(type_button)
            
            # AI type dropdown (only if AI)
            if player_type == "AI":
                ai_type = self.player_configs[i]["ai_type"]
                ai_button = Button(240, y_base, 150, 40, f"{ai_type}")
                self.buttons.append(ai_button)
        
        # Start game button
        self.buttons.append(Button(BUTTON_CENTER_X, 450, BUTTON_WIDTH, BUTTON_HEIGHT, "Start Game"))
        self.buttons.append(Button(BUTTON_CENTER_X, 520, BUTTON_WIDTH, BUTTON_HEIGHT_SMALL, "Back to Menu"))
    
    def setup_game_buttons(self):
        """Setup buttons for the playing state."""
        self.buttons = [
            Button(20, WINDOW_HEIGHT - 60, 80, 40, "Menu"),
            Button(120, WINDOW_HEIGHT - 60, 80, 40, "Restart"),
            Button(220, WINDOW_HEIGHT - 60, 80, 40, "Undo"),
            Button(320, WINDOW_HEIGHT - 60, 80, 40, "Save")
        ]
    
    def handle_setup_click(self, x: int, y: int):
        """Handle setup screen clicks."""
        for button in self.buttons:
            if button.contains_point(x, y):
                if button.text.startswith("P1:"):
                    self.player_configs[0]["type"] = "AI" if self.player_configs[0]["type"] == "Human" else "Human"
                    self.setup_game_setup_buttons()
                elif button.text.startswith("P2:"):
                    self.player_configs[1]["type"] = "AI" if self.player_configs[1]["type"] == "Human" else "Human"
                    self.setup_game_setup_buttons()
                # Handle AI type cycling buttons
                elif button.text in ["Random", "Greedy", "Strategic"]:
                    # Determine which player's AI type to cycle based on button position
                    button_y = button.y
                    ai_types = ["Random", "Greedy", "Strategic"]
                    
                    if 200 <= button_y < 320:  # Player 1 area
                        current_idx = ai_types.index(self.player_configs[0]["ai_type"])
                        next_idx = (current_idx + 1) % len(ai_types)
                        self.player_configs[0]["ai_type"] = ai_types[next_idx]
                    elif 320 <= button_y < 440:  # Player 2 area
                        current_idx = ai_types.index(self.player_configs[1]["ai_type"])
                        next_idx = (current_idx + 1) % len(ai_types)
                        self.player_configs[1]["ai_type"] = ai_types[next_idx]
                    self.setup_game_setup_buttons()
                elif button.text == "Start Game":
                    # Create game with configured players
                    player_names = []
                    self.ai_players = {}
                    
                    for i, config in enumerate(self.player_configs):
                        if config["type"] == "Human":
                            player_names.append(f"Player {i+1}")
                        else:
                            player_names.append(f"AI {i+1}")
                            # Setup AI player
                            if config["ai_type"] == "Random":
                                self.ai_players[i] = RandomAI(f"AI Player {i+1}")
                            elif config["ai_type"] == "Greedy":
                                self.ai_players[i] = GreedyAI(f"AI Player {i+1}")
                            elif config["ai_type"] == "Strategic":
                                self.ai_players[i] = StrategicAI(f"AI Player {i+1}")
                    
                    self.game = AzulGame(player_names)
                    self.game.setup_round()
                    self.game_state = "playing"
                    self.setup_game_buttons()
                elif button.text == "Back to Menu":
                    self.game_state = "menu"
                    self.setup_buttons()
    
    def handle_settings_click(self, x: int, y: int):
        """Handle settings screen clicks."""
        for button in self.buttons:
            if button.contains_point(x, y):
                if "AI Animations:" in button.text:
                    self.settings['ai_animations_enabled'] = not self.settings['ai_animations_enabled']
                    self.save_settings()
                    self.setup_settings_buttons()
                elif "Round Animations:" in button.text:
                    self.settings['transition_animations_enabled'] = not self.settings['transition_animations_enabled']
                    self.save_settings()
                    self.setup_settings_buttons()
                elif "AI Speed:" in button.text:
                    # Cycle through speed options
                    speeds = [500, 1000, 1500, 2000]
                    current_idx = speeds.index(self.settings['ai_step_duration']) if self.settings['ai_step_duration'] in speeds else 1
                    next_idx = (current_idx + 1) % len(speeds)
                    self.settings['ai_step_duration'] = speeds[next_idx]
                    self.ai_step_duration = speeds[next_idx]
                    self.save_settings()
                    self.setup_settings_buttons()
                elif "Wall Pattern:" in button.text:
                    # Cycle through wall pattern modes
                    modes = ["off", "subtle", "letters", "outlines"]
                    current_idx = modes.index(self.wall_pattern_mode)
                    next_idx = (current_idx + 1) % len(modes)
                    self.wall_pattern_mode = modes[next_idx]
                    self.setup_settings_buttons()
                elif button.text == "Back to Menu":
                    self.game_state = "menu"
                    self.setup_buttons()
    
    def handle_game_click(self, x: int, y: int):
        """Handle game screen clicks."""
        # Check button clicks first
        for button in self.buttons:
            if button.contains_point(x, y):
                if button.text == "Menu":
                    self.game_state = "menu"
                    self.setup_buttons()
                    return
                elif button.text == "Restart":
                    # Recreate game with current player configuration
                    player_names = []
                    self.ai_players = {}
                    
                    for i, config in enumerate(self.player_configs):
                        if config["type"] == "Human":
                            player_names.append(f"Player {i+1}")
                        else:
                            player_names.append(f"AI {i+1}")
                            # Setup AI player
                            if config["ai_type"] == "Random":
                                self.ai_players[i] = RandomAI(f"AI Player {i+1}")
                            elif config["ai_type"] == "Greedy":
                                self.ai_players[i] = GreedyAI(f"AI Player {i+1}")
                            elif config["ai_type"] == "Strategic":
                                self.ai_players[i] = StrategicAI(f"AI Player {i+1}")
                    
                    self.game = AzulGame(player_names)
                    self.game.setup_round()
                    self.move_history = []
                    self.can_undo = False
                    return
                elif button.text == "Undo":
                    if self.can_undo and self.move_history:
                        self.undo_last_move()
                    return
                elif button.text == "Save":
                    self.save_game()
                    return
        
        # Only handle game clicks if it's human player's turn
        if (self.game and 
            self.game.current_player_idx not in self.ai_players):
            self.handle_human_move(x, y)
    
    def handle_human_move(self, x: int, y: int):
        """Handle human player moves."""
        if not self.game:
            return
            
        # Check factory clicks
        factory_clicked = self.get_clicked_factory(x, y)
        if factory_clicked is not None:
            if self.selected_factory == factory_clicked:
                # Clicking same factory cycles through colors
                self.cycle_color()
            else:
                # New factory selected
                self.selected_factory = factory_clicked
                self.selected_color = self.get_first_available_color()
            return
        
        # Check center click
        if self.is_center_clicked(x, y):
            if self.selected_factory == -1:
                # Clicking same center cycles through colors
                self.cycle_color()
            else:
                # Center selected
                self.selected_factory = -1  # -1 represents center
                self.selected_color = self.get_first_available_color()
            return
        
        # Check pattern line selection if color is selected
        if self.selected_color is not None:
            pattern_line = self.get_clicked_pattern_line(x, y)
            if pattern_line is not None:
                self.execute_human_move(pattern_line)
    
    def execute_human_move(self, pattern_line: int):
        """Execute the human player's move."""
        if not self.game or self.selected_factory is None or self.selected_color is None:
            return
        
        # Save game state before move for undo functionality
        if self.game.current_player_idx not in self.ai_players:
            self.save_game_state()
        
        success = False
        if self.selected_factory == -1:  # Center
            success = self.game.take_tiles_from_center(self.selected_color, pattern_line)
        else:  # Factory
            success = self.game.take_tiles_from_factory(
                self.selected_factory, self.selected_color, pattern_line
            )
        
        if success:
            # Enable undo for human players
            if self.game.current_player_idx not in self.ai_players:
                self.can_undo = True
            
            self.selected_factory = None
            self.selected_color = None
            self.selected_pattern_line = None
            
            # Check if round is over
            if self.game.is_round_over():
                if self.settings['transition_animations_enabled']:
                    self.start_round_transition()
                else:
                    # Skip animations and score immediately
                    self.game.score_round()
                    # After scoring, pause for manual next round
                    if self.game.game_over:
                        self.start_end_game_animation()
                    else:
                        self.game_state = "round_complete"
                        self.setup_round_complete_buttons()
    
    def process_ai_turn(self):
        """Process AI player's turn with visual feedback."""
        if not self.game:
            return
            
        current_idx = self.game.current_player_idx
        if current_idx not in self.ai_players:
            return
        
        current_time = pygame.time.get_ticks()
        
        if self.ai_turn_state == "idle":
            # Start AI turn
            self.ai_turn_state = "thinking"
            self.ai_turn_timer = current_time
            
        elif self.ai_turn_state == "thinking":
            if current_time - self.ai_turn_timer >= self.ai_step_duration:
                # Get AI move and start highlighting
                ai_player = self.ai_players[current_idx]
                self.ai_move = ai_player.choose_move(self.game, current_idx)
                if self.ai_move:
                    self.ai_turn_state = "selecting_source"
                    self.ai_highlighted_factory = self.ai_move.source_index
                    self.ai_turn_timer = current_time
                else:
                    self.ai_turn_state = "idle"
                    
        elif self.ai_turn_state == "selecting_source":
            if current_time - self.ai_turn_timer >= self.ai_step_duration:
                # Highlight selected color
                self.ai_turn_state = "selecting_color"
                self.ai_highlighted_color = self.ai_move.color
                self.ai_turn_timer = current_time
                
        elif self.ai_turn_state == "selecting_color":
            if current_time - self.ai_turn_timer >= self.ai_step_duration:
                # Execute the move
                self.ai_turn_state = "executing"
                self.ai_turn_timer = current_time
                
        elif self.ai_turn_state == "executing":
            if current_time - self.ai_turn_timer >= self.ai_step_duration:
                # Actually execute the move
                success = self.game.execute_move(self.ai_move)
                
                # Reset AI visualization state
                self.ai_turn_state = "idle"
                self.ai_highlighted_factory = None
                self.ai_highlighted_color = None
                self.ai_move = None
                
                if success and self.game.is_round_over():
                    self.start_round_transition()
    
    def start_round_transition(self):
        """Start the round transition animation sequence."""
        if not self.game:
            return
        
        self.round_transition_state = "moving_tiles"
        self.transition_timer = pygame.time.get_ticks()
        self.moving_tiles = []
        self.score_animations = []
        
        # Prepare tile movement animations and scoring queue
        self.scoring_queue = []
        
        for player_idx, player in enumerate(self.game.players):
            for line_idx, pattern_line in enumerate(player.pattern_lines):
                if pattern_line.is_full():
                    # Calculate source and destination positions
                    src_pos = self.get_pattern_line_tile_pos(player_idx, line_idx, 0)
                    dest_pos = self.get_wall_tile_pos(player_idx, line_idx, pattern_line.tiles[0].color)
                    
                    if src_pos and dest_pos:
                        tile_data = {
                            'tile': pattern_line.tiles[0],
                            'start_pos': src_pos,
                            'end_pos': dest_pos,
                            'progress': 0.0,
                            'player_idx': player_idx,
                            'line_idx': line_idx,
                            'score_gain': 0,  # Will be calculated when tile is placed
                            'scored': False
                        }
                        
                        self.moving_tiles.append(tile_data)
                        self.scoring_queue.append(tile_data)
        
        # Sort scoring queue by player, then by row (top to bottom)
        self.scoring_queue.sort(key=lambda x: (x['player_idx'], x['line_idx']))
        self.current_scoring_index = 0
    
    def process_round_transition(self):
        """Process the round transition animation."""
        if not self.game or self.round_transition_state == "idle":
            return
        
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.transition_timer
        
        if self.round_transition_state == "moving_tiles":
            # Update tile movement progress
            progress = min(1.0, elapsed / self.transition_step_duration)
            
            for tile_anim in self.moving_tiles:
                tile_anim['progress'] = progress
            
            if progress >= 1.0:
                # Move to sequential row scoring phase
                self.round_transition_state = "scoring_rows"
                self.transition_timer = current_time
                self.current_scoring_index = 0
        
        elif self.round_transition_state == "scoring_rows":
            # Score one row at a time with delays
            if self.current_scoring_index < len(self.scoring_queue):
                # Check if enough time has passed to score the next row
                row_elapsed = elapsed - (self.current_scoring_index * self.row_scoring_duration)
                
                if row_elapsed >= self.row_scoring_duration:
                    # Score this row
                    tile_data = self.scoring_queue[self.current_scoring_index]
                    
                    if not tile_data['scored']:
                        tile_data['scored'] = True
                        
                        # Actually score this tile placement
                        player = self.game.players[tile_data['player_idx']]
                        line_idx = tile_data['line_idx']
                        pattern_line = player.pattern_lines[line_idx]
                        
                        if pattern_line.is_full():
                            # Calculate score AFTER placing the tile on the wall for proper adjacency
                            score_gain = self.game._calculate_wall_score(player, line_idx, pattern_line.tiles[0].color)
                            tile_data['score_gain'] = score_gain  # Update the tile_data with correct score
                            player.score += score_gain
                            # Place tile on wall
                            player.wall.place_tile(line_idx, pattern_line.tiles[0].color)
                            # Clear pattern line
                            pattern_line.tiles = []
                            
                            # Add visual score animation with correct score
                            player_pos = self.get_player_score_pos(tile_data['player_idx'])
                            if player_pos and score_gain > 0:
                                self.score_animations.append({
                                    'player_idx': tile_data['player_idx'],
                                    'score_gain': score_gain,
                                    'pos': player_pos,
                                    'progress': 0.0,
                                    'start_time': current_time
                                })
                    
                    self.current_scoring_index += 1
            else:
                # All rows scored, move to floor penalties
                self.round_transition_state = "scoring_floor"
                self.transition_timer = current_time
        
        elif self.round_transition_state == "scoring_floor":
            if elapsed >= self.row_scoring_duration:  # Same duration as row scoring
                # Add floor penalty animations and apply penalties
                for player_idx, player in enumerate(self.game.players):
                    if player.floor_line:
                        penalty = self.game._calculate_floor_penalty(len(player.floor_line))
                        if penalty > 0:
                            # Add visual penalty animation
                            player_pos = self.get_player_score_pos(player_idx)
                            if player_pos:
                                self.score_animations.append({
                                    'player_idx': player_idx,
                                    'score_gain': -penalty,
                                    'pos': (player_pos[0], player_pos[1] + 25),  # Slightly below score
                                    'progress': 0.0,
                                    'start_time': current_time,
                                    'is_penalty': True
                                })
                            
                            # Apply penalty to score
                            player.score = max(0, player.score - penalty)
                
                # Move to floor clearing
                self.round_transition_state = "clearing_floor"
                self.transition_timer = current_time
        
        elif self.round_transition_state == "clearing_floor":
            if elapsed >= self.transition_step_duration // 2:  # Shorter duration
                # Move to next round setup
                self.round_transition_state = "setup_next"
                self.transition_timer = current_time
        
        elif self.round_transition_state == "setup_next":
            if elapsed >= self.transition_step_duration // 2:
                # Clear floor lines and check for game end
                for player in self.game.players:
                    player.floor_line.clear()
                
                # Check for game end condition
                for player in self.game.players:
                    for row in player.wall.grid:
                        if all(tile is not None for tile in row):
                            self.game.game_over = True
                            break
                    if self.game.game_over:
                        break
                
                # Complete transition but pause before next round
                self.round_transition_state = "idle"
                self.moving_tiles = []
                self.score_animations = []
                
                # Pause for manual next round confirmation
                if self.game.game_over:
                    self.start_end_game_animation()
                else:
                    self.game_state = "round_complete"
                    self.setup_round_complete_buttons()
    
    def process_ai_turn_instant(self):
        """Process AI turn instantly without animations."""
        if not self.game:
            return
            
        current_idx = self.game.current_player_idx
        if current_idx not in self.ai_players:
            return
        
        # Get and execute AI move immediately
        ai_player = self.ai_players[current_idx]
        ai_move = ai_player.choose_move(self.game, current_idx)
        
        if ai_move:
            success = self.game.execute_move(ai_move)
            if success and self.game.is_round_over():
                if self.settings['transition_animations_enabled']:
                    self.start_round_transition()
                else:
                    # Skip animations and score immediately
                    self.game.score_round()
                    # After scoring, pause for manual next round
                    if self.game.game_over:
                        self.start_end_game_animation()
                    else:
                        self.game_state = "round_complete"
                        self.setup_round_complete_buttons()
    
    def start_end_game_animation(self):
        """Start the end game bonus animation sequence."""
        if not self.game or not self.game.game_over:
            return
        
        # Prevent multiple calls from recreating animations
        if self.game_state == "game_over":
            return
            
        self.game_state = "game_over"
        self.end_game_animation_state = "calculating_bonuses"
        self.end_game_timer = pygame.time.get_ticks()
        self.end_game_bonus_animations = []
        self.end_game_bonuses_calculated = False
        
        # Calculate and prepare bonus animations for each player
        for player_idx, player in enumerate(self.game.players):
            player_pos = self.get_player_score_pos(player_idx)
            if not player_pos:
                continue
                
            # Horizontal row bonuses (2 points each)
            for row_idx, row in enumerate(player.wall.grid):
                if all(tile is not None for tile in row):
                    self.end_game_bonus_animations.append({
                        'type': 'horizontal_row',
                        'player_idx': player_idx,
                        'row_idx': row_idx,
                        'bonus_points': 2,
                        'pos': (player_pos[0], player_pos[1] + 30),
                        'start_time': pygame.time.get_ticks() + 1000 + row_idx * 500,
                        'progress': 0.0
                    })
            
            # Vertical column bonuses (7 points each)
            for col_idx in range(5):
                if all(player.wall.grid[row][col_idx] is not None for row in range(5)):
                    self.end_game_bonus_animations.append({
                        'type': 'vertical_column',
                        'player_idx': player_idx,
                        'col_idx': col_idx,
                        'bonus_points': 7,
                        'pos': (player_pos[0], player_pos[1] + 50),
                        'start_time': pygame.time.get_ticks() + 3000 + col_idx * 500,
                        'progress': 0.0
                    })
            
            # Color set bonuses (10 points each)
            color_list = [c for c in TileColor if c != TileColor.FIRST_PLAYER]
            for color_idx, color in enumerate(color_list):
                color_count = 0
                for row in range(5):
                    col = (row + color_list.index(color)) % 5
                    if player.wall.grid[row][col] is not None:
                        color_count += 1
                if color_count == 5:
                    self.end_game_bonus_animations.append({
                        'type': 'color_set',
                        'player_idx': player_idx,
                        'color': color,
                        'bonus_points': 10,
                        'pos': (player_pos[0], player_pos[1] + 70),
                        'start_time': pygame.time.get_ticks() + 5000 + color_idx * 500,
                        'progress': 0.0
                    })
    
    def prepare_score_animations(self):
        """Prepare score increment animations."""
        for player_idx, player in enumerate(self.game.players):
            # Calculate score that will be gained
            score_gain = 0
            for line_idx, pattern_line in enumerate(player.pattern_lines):
                if pattern_line.is_full():
                    score_gain += self.game._calculate_wall_score(player, line_idx, pattern_line.tiles[0].color)
            
            if score_gain > 0:
                player_pos = self.get_player_score_pos(player_idx)
                if player_pos:
                    self.score_animations.append({
                        'player_idx': player_idx,
                        'score_gain': score_gain,
                        'pos': player_pos,
                        'progress': 0.0
                    })
    
    def get_pattern_line_tile_pos(self, player_idx: int, line_idx: int, tile_idx: int) -> Optional[Tuple[int, int]]:
        """Get the screen position of a tile in a pattern line."""
        player_x = PLAYER_START_X + player_idx * (PLAYER_WIDTH + PLAYER_SPACING)
        player_y = WINDOW_HEIGHT - PLAYER_HEIGHT - PLAYER_MARGIN_BOTTOM
        
        pattern_x = player_x + PATTERN_LINE_OFFSET_X
        pattern_y = player_y + PATTERN_LINE_OFFSET_Y
        
        line_y = pattern_y + line_idx * PATTERN_LINE_HEIGHT
        tile_size = self.get_tile_size()
        tile_x = pattern_x + 5 + tile_idx * (tile_size + 2)
        tile_y = line_y + 5
        
        return (tile_x, tile_y)
    
    def get_player_base_pos(self, player_idx: int) -> Tuple[int, int]:
        """Get the base screen position for a player's area."""
        player_x = PLAYER_START_X + player_idx * (PLAYER_WIDTH + PLAYER_SPACING)
        player_y = WINDOW_HEIGHT - PLAYER_HEIGHT - PLAYER_MARGIN_BOTTOM
        return (player_x, player_y)
    
    def get_wall_tile_pos(self, player_idx: int, line_idx: int, color: TileColor) -> Optional[Tuple[int, int]]:
        """Get the screen position where a tile should be placed on the wall."""
        player_x, player_y = self.get_player_base_pos(player_idx)
        pattern_x = player_x + PATTERN_LINE_OFFSET_X
        pattern_y = player_y + PATTERN_LINE_OFFSET_Y
        
        # Find the correct column for this color in this row using the same logic as Wall.place_tile
        wall_x = pattern_x + 175
        tile_size = self.get_tile_size()
        
        # Calculate column using the same formula as Wall.place_tile
        try:
            color_list = list(TileColor)
            # Remove FIRST_PLAYER from the list for calculation
            color_list = [c for c in color_list if c != TileColor.FIRST_PLAYER]
            col_idx = (line_idx + color_list.index(color)) % 5
        except ValueError:
            return None
        
        wall_tile_x = wall_x + col_idx * (tile_size + 2)
        wall_tile_y = pattern_y + line_idx * PATTERN_LINE_HEIGHT + 5
        
        return (wall_tile_x, wall_tile_y)
    
    def get_player_score_pos(self, player_idx: int) -> Optional[Tuple[int, int]]:
        """Get the screen position for score popups - positioned to the right of the wall."""
        player_x, player_y = self.get_player_base_pos(player_idx)
        
        # Position to the right of the wall
        return (player_x + 250, player_y + 25)
    
    def save_game_state(self):
        """Save current game state for undo functionality."""
        import copy
        if not self.game:
            return
            
        # Deep copy the game state
        game_state = {
            'factories': [copy.deepcopy(factory.tiles) for factory in self.game.factories],
            'center': copy.deepcopy(self.game.center.tiles),
            'center_first_player_taken': self.game.center.first_player_taken,
            'players': [],
            'current_player_idx': self.game.current_player_idx,
            'first_player_idx': self.game.first_player_idx,
            'bag': copy.deepcopy(self.game.bag),
            'discard_pile': copy.deepcopy(self.game.discard_pile)
        }
        
        # Save player states
        for player in self.game.players:
            player_state = {
                'name': player.name,
                'score': player.score,
                'pattern_lines': [copy.deepcopy(line) for line in player.pattern_lines],
                'floor_line': copy.deepcopy(player.floor_line),
                'wall_grid': copy.deepcopy(player.wall.grid)
            }
            game_state['players'].append(player_state)
        
        # Keep only the last state (single undo)
        self.move_history = [game_state]
    
    def undo_last_move(self):
        """Undo the last move."""
        if not self.move_history or not self.game:
            return
            
        import copy
        game_state = self.move_history[-1]
        
        # Restore factories
        for i, factory_tiles in enumerate(game_state['factories']):
            self.game.factories[i].tiles = copy.deepcopy(factory_tiles)
        
        # Restore center
        self.game.center.tiles = copy.deepcopy(game_state['center'])
        self.game.center.first_player_taken = game_state['center_first_player_taken']
        
        # Restore players
        for i, player_state in enumerate(game_state['players']):
            player = self.game.players[i]
            player.score = player_state['score']
            player.floor_line = copy.deepcopy(player_state['floor_line'])
            player.wall.grid = copy.deepcopy(player_state['wall_grid'])
            
            # Restore pattern lines
            for j, pattern_line in enumerate(player_state['pattern_lines']):
                player.pattern_lines[j] = copy.deepcopy(pattern_line)
        
        # Restore game state
        self.game.current_player_idx = game_state['current_player_idx']
        self.game.first_player_idx = game_state['first_player_idx']
        self.game.bag = copy.deepcopy(game_state['bag'])
        self.game.discard_pile = copy.deepcopy(game_state['discard_pile'])
        
        # Clear undo state
        self.move_history = []
        self.can_undo = False
        
        # Clear selection
        self.selected_factory = None
        self.selected_color = None
        self.selected_pattern_line = None

    def start_game_setup(self):
        """Start game setup."""
        self.game_state = "setup"
        self.setup_step = 0
        self.setup_game_setup_buttons()
    
    def draw(self):
        """Draw the current screen."""
        self.screen.fill(COLORS['background'])
        
        if self.game_state == "menu":
            self.draw_menu()
        elif self.game_state == "setup":
            self.draw_setup()
        elif self.game_state == "settings":
            self.draw_settings()
        elif self.game_state == "playing":
            self.draw_game()
        elif self.game_state == "round_complete":
            self.draw_round_complete()
        elif self.game_state == "game_over":
            self.process_end_game_animations()
            self.draw_game_over()
    
    def process_end_game_animations(self):
        """Process and update end game bonus animations."""
        if self.end_game_animation_state == "idle" or self.end_game_animation_state == "showing_results":
            return
            
        current_time = pygame.time.get_ticks()
        
        if self.end_game_animation_state == "calculating_bonuses":
            # Update animation progress for active animations
            for animation in self.end_game_bonus_animations:
                if current_time >= animation['start_time']:
                    # Calculate progress (0.0 to 1.0 over 1 second)
                    elapsed = current_time - animation['start_time']
                    animation['progress'] = min(1.0, elapsed / 1000.0)
                    
                    # Apply bonus immediately when animation starts
                    if 'applied' not in animation:
                        animation['applied'] = True
                        player = self.game.players[animation['player_idx']]
                        bonus_points = self.game._calculate_end_game_bonuses(player)
                        # Only apply the specific bonus for this animation
                        if animation['type'] == 'horizontal_row':
                            player.score += 2
                        elif animation['type'] == 'vertical_column':
                            player.score += 7
                        elif animation['type'] == 'color_set':
                            player.score += 10
            
            # Check if all animations are complete
            all_complete = all(
                animation.get('applied', False) 
                for animation in self.end_game_bonus_animations
            )
            
            if all_complete and len(self.end_game_bonus_animations) > 0:
                # Wait a bit more before showing final results
                if current_time - self.end_game_timer > 8000:  # 8 seconds total
                    self.end_game_animation_state = "showing_results"
            elif len(self.end_game_bonus_animations) == 0:
                # No bonuses to animate, go straight to results
                self.end_game_animation_state = "showing_results"
    
    def draw_menu(self):
        """Draw the main menu."""
        title = self.large_font.render("Azul - Board Game", True, COLORS['text'])
        title_rect = title.get_rect(center=(SCREEN_CENTER_X, 200))
        self.screen.blit(title, title_rect)
        
        subtitle = self.font.render("A strategic tile-laying game with AI opponents", True, COLORS['text'])
        subtitle_rect = subtitle.get_rect(center=(SCREEN_CENTER_X, 250))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            hovered = button.contains_point(mouse_pos[0], mouse_pos[1])
            button.draw(self.screen, self.font, hovered)
    
    def draw_setup(self):
        """Draw the setup screen."""
        title = self.large_font.render("Game Setup", True, COLORS['text'])
        title_rect = title.get_rect(center=(SCREEN_CENTER_X, 100))
        self.screen.blit(title, title_rect)
        
        subtitle = self.font.render("Configure Players:", True, COLORS['text'])
        subtitle_rect = subtitle.get_rect(center=(SCREEN_CENTER_X, 150))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Player configuration display
        for i in range(2):
            player_num = i + 1
            y_base = 200 + i * 120
            
            # Player label
            player_label = self.font.render(f"Player {player_num}:", True, COLORS['text'])
            self.screen.blit(player_label, (50, y_base + 10))
            
            # AI type description (if AI)
            if self.player_configs[i]["type"] == "AI":
                ai_type = self.player_configs[i]["ai_type"]
                ai_descriptions = {
                    "Random": "Makes random moves (Easy)",
                    "Greedy": "Chooses locally optimal moves (Medium)",
                    "Strategic": "Uses advanced strategy (Hard)"
                }
                desc_text = ai_descriptions.get(ai_type, "")
                desc_surface = self.small_font.render(desc_text, True, COLORS['text'])
                self.screen.blit(desc_surface, (50, y_base + 50))
        
        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            hovered = button.contains_point(mouse_pos[0], mouse_pos[1])
            button.draw(self.screen, self.font, hovered)
    
    def draw_settings(self):
        """Draw the settings screen."""
        title = self.large_font.render("Settings", True, COLORS['text'])
        title_rect = title.get_rect(center=(SCREEN_CENTER_X, 100))
        self.screen.blit(title, title_rect)
        
        # Setting descriptions
        descriptions = [
            "Toggle AI move animations on/off",
            "Toggle round transition animations on/off", 
            "Adjust AI thinking speed (faster = less realistic)",
            "Show wall pattern hints for tile placement"
        ]
        
        for i, desc in enumerate(descriptions):
            y_pos = 220 + i * 60
            desc_surface = self.small_font.render(desc, True, COLORS['text'])
            self.screen.blit(desc_surface, (50, y_pos))
        
        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            hovered = button.contains_point(mouse_pos[0], mouse_pos[1])
            button.draw(self.screen, self.font, hovered)
    
    def draw_game(self):
        """Draw the main game screen."""
        if not self.game:
            return
        
        # Process round transitions
        self.process_round_transition()
        
        # Process AI turns (only if not in transition)
        if (self.round_transition_state == "idle" and 
            self.game.current_player_idx in self.ai_players):
            if self.settings['ai_animations_enabled']:
                self.process_ai_turn()
            else:
                self.process_ai_turn_instant()
        
        # Draw game elements
        self.draw_factories()
        self.draw_center()
        self.draw_players()
        self.draw_moving_tiles()  # Draw animated tiles
        self.draw_score_animations()  # Draw score animations
        self.draw_current_player_info()
        self.draw_ai_turn_info()
        self.draw_transition_info()  # Draw transition status
        
        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            hovered = button.contains_point(mouse_pos[0], mouse_pos[1])
            button.draw(self.screen, self.font, hovered)
    
    def draw_round_complete(self):
        """Draw the round complete screen."""
        if not self.game:
            return
        
        # Draw the game board in background (dimmed)
        self.draw_game()
        
        # Draw semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # Draw round complete message
        if self.game.game_over:
            title = self.large_font.render("Game Complete!", True, COLORS['white'])
            winner = self.game.get_winner()
            subtitle = self.font.render(f"{winner.name} wins with {winner.score} points!", True, COLORS['white']) if winner else None
        else:
            title = self.large_font.render("Round Complete!", True, COLORS['white'])
            subtitle = self.font.render("Scoring finished. Ready for next round?", True, COLORS['white'])
        
        title_rect = title.get_rect(center=(SCREEN_CENTER_X, SCREEN_CENTER_Y - 100))
        self.screen.blit(title, title_rect)
        
        if subtitle:
            subtitle_rect = subtitle.get_rect(center=(SCREEN_CENTER_X, SCREEN_CENTER_Y - 50))
            self.screen.blit(subtitle, subtitle_rect)
        
        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            hovered = button.contains_point(mouse_pos[0], mouse_pos[1])
            button.draw(self.screen, self.font, hovered)
    
    def draw_game_over(self):
        """Draw the game over screen with end-game bonus animations."""
        if not self.game:
            return
        
        if self.end_game_animation_state == "calculating_bonuses":
            # Draw the game board with bonus animations
            self.draw_game()
            
            # Draw bonus animations overlay
            current_time = pygame.time.get_ticks()
            for animation in self.end_game_bonus_animations:
                if current_time >= animation['start_time'] and animation['progress'] > 0:
                    self.draw_bonus_animation(animation)
                    
            # Draw "Calculating Final Bonuses..." text
            text = self.large_font.render("Calculating Final Bonuses...", True, COLORS['text'])
            text_rect = text.get_rect(center=(SCREEN_CENTER_X, 50))
            self.screen.blit(text, text_rect)
            
        elif self.end_game_animation_state == "showing_results":
            # Show final walls instead of winner screen
            self.draw_final_walls()
    
    def draw_bonus_animation(self, animation):
        """Draw a single bonus animation with highlighting."""
        if animation['progress'] <= 0:
            return
            
        # Fade in effect
        alpha = int(255 * min(1.0, animation['progress'] * 2))
        
        # Highlight the contributing tiles/rows/columns
        player = self.game.players[animation['player_idx']]
        player_x = PLAYER_START_X + animation['player_idx'] * (PLAYER_WIDTH + PLAYER_SPACING)
        player_y = WINDOW_HEIGHT - PLAYER_HEIGHT - PLAYER_MARGIN_BOTTOM
        pattern_x = player_x + PATTERN_LINE_OFFSET_X
        wall_x = pattern_x + 175  # Use same calculation as get_wall_tile_pos
        wall_y = player_y + PATTERN_LINE_OFFSET_Y
        tile_size = self.get_tile_size()
        
        # Create thin green outline instead of full highlight
        outline_color = (0, 255, 0)  # Green
        outline_alpha = alpha // 2
        
        if animation['type'] == 'horizontal_row':
            # Outline the entire row
            row_idx = animation['row_idx']
            for col in range(5):
                if player.wall.grid[row_idx][col] is not None:
                    tile_x = wall_x + col * (tile_size + 2)
                    tile_y = wall_y + row_idx * PATTERN_LINE_HEIGHT + 5
                    # Draw thin outline
                    outline_rect = pygame.Rect(tile_x, tile_y, tile_size, tile_size)
                    pygame.draw.rect(self.screen, outline_color, outline_rect, 2)
            
        elif animation['type'] == 'vertical_column':
            # Outline the entire column
            col_idx = animation['col_idx']
            for row in range(5):
                if player.wall.grid[row][col_idx] is not None:
                    tile_x = wall_x + col_idx * (tile_size + 2)
                    tile_y = wall_y + row * PATTERN_LINE_HEIGHT + 5
                    # Draw thin outline
                    outline_rect = pygame.Rect(tile_x, tile_y, tile_size, tile_size)
                    pygame.draw.rect(self.screen, outline_color, outline_rect, 2)
            
        elif animation['type'] == 'color_set':
            # Outline all tiles of this color
            color = animation['color']
            from azul.models import TileColor
            color_list = [c for c in TileColor if c != TileColor.FIRST_PLAYER]
            for row in range(5):
                col = (row + color_list.index(color)) % 5
                if player.wall.grid[row][col] is not None:
                    tile_x = wall_x + col * (tile_size + 2)
                    tile_y = wall_y + row * PATTERN_LINE_HEIGHT + 5
                    # Draw thin outline
                    outline_rect = pygame.Rect(tile_x, tile_y, tile_size, tile_size)
                    pygame.draw.rect(self.screen, outline_color, outline_rect, 2)
        
        # Create surface with descriptive text and number
        if animation['bonus_points'] > 0:
            color = (0, 150, 0)  # Green for positive scores (same as regular popups)
            if animation['type'] == 'horizontal_row':
                text = f"Row Bonus: +{animation['bonus_points']}"
            elif animation['type'] == 'vertical_column':
                text = f"Column Bonus: +{animation['bonus_points']}"
            elif animation['type'] == 'color_set':
                text = f"Color Set Bonus: +{animation['bonus_points']}"
            else:
                text = f"+{animation['bonus_points']}"
        else:
            color = (200, 50, 50)  # Red for penalties (same as regular popups)
            text = f"{animation['bonus_points']}"
        
        # Use same font and fade effect as regular score animations
        text_surface = self.font.render(text, True, color)
        fade_alpha = int(255 * (1 - animation['progress']))  # Fade out like regular popups
        text_surface.set_alpha(fade_alpha)
        
        # Position with upward movement like regular popups
        y_offset = int(-40 * animation['progress'])  # Same movement as regular popups
        pos = (animation['pos'][0], animation['pos'][1] + y_offset)
        
        self.screen.blit(text_surface, pos)
    
    def draw_final_walls(self):
        """Draw the final game state showing all player walls and scores."""
        # Draw title
        title = self.large_font.render("Final Results", True, COLORS['text'])
        title_rect = title.get_rect(center=(SCREEN_CENTER_X, 30))
        self.screen.blit(title, title_rect)
        
        # Draw each player's final wall and score
        for i, player in enumerate(self.game.players):
            # Calculate position for this player's display
            player_x = 50 + (i % 2) * SCREEN_CENTER_X
            player_y = 80 + (i // 2) * 300
            
            # Draw player name and final score
            name_text = self.font.render(f"{player.name}: {player.score} points", True, COLORS['text'])
            self.screen.blit(name_text, (player_x, player_y))
            
            # Draw the player's wall
            wall_start_y = player_y + 30
            tile_size = self.get_tile_size()
            for row in range(5):
                for col in range(5):
                    tile_x = player_x + col * (tile_size + 2)
                    tile_y = wall_start_y + row * (tile_size + 2)
                    
                    # Draw wall slot
                    pygame.draw.rect(self.screen, COLORS['wall'], 
                                   (tile_x, tile_y, tile_size, tile_size))
                    pygame.draw.rect(self.screen, COLORS['text'], 
                                   (tile_x, tile_y, tile_size, tile_size), 1)
                    
                    # Draw tile if present
                    if player.wall.grid[row][col] is not None:
                        tile = player.wall.grid[row][col]
                        color = TILE_COLORS.get(tile.color, COLORS['text'])
                        pygame.draw.rect(self.screen, color, 
                                       (tile_x + 2, tile_y + 2, tile_size - 4, tile_size - 4))
        
        # Highlight winner
        winner = self.game.get_winner()
        if winner:
            winner_idx = self.game.players.index(winner)
            winner_x = 50 + (winner_idx % 2) * SCREEN_CENTER_X
            winner_y = 80 + (winner_idx // 2) * 300
            
            # Draw winner highlight
            pygame.draw.rect(self.screen, (255, 215, 0), 
                           (winner_x - 10, winner_y - 10, 300, 200), 3)
            
            winner_text = self.font.render("WINNER!", True, (255, 215, 0))
            self.screen.blit(winner_text, (winner_x + 200, winner_y))
    
    def draw_factories(self):
        """Draw the factories."""
        if not self.game:
            return
            
        for i, factory in enumerate(self.game.factories):
            x = FACTORY_START_X + (i % 3) * (FACTORY_SIZE + FACTORY_SPACING)
            y = FACTORY_START_Y + (i // 3) * (FACTORY_SIZE + FACTORY_SPACING)
            
            # Highlight selected factory (human) or AI highlighted factory
            if self.selected_factory == i:
                color = COLORS['selected']
            elif self.ai_highlighted_factory == i:
                color = (255, 165, 0)  # Orange for AI selection
            else:
                color = COLORS['factory']
            
            pygame.draw.rect(self.screen, color, (x, y, FACTORY_SIZE, FACTORY_SIZE))
            pygame.draw.rect(self.screen, COLORS['text'], (x, y, FACTORY_SIZE, FACTORY_SIZE), 2)
            
            # Draw factory number
            text = self.small_font.render(f"F{i+1}", True, COLORS['text'])
            self.screen.blit(text, (x + 5, y + 5))
            
            # Draw tiles
            self.draw_tiles_in_rect(factory.tiles, x + 10, y + 20, FACTORY_SIZE - 20, FACTORY_SIZE - 30, factory_idx=i)
    
    def draw_center(self):
        """Draw the center area."""
        if not self.game:
            return
            
        
        # Highlight if selected (human) or AI highlighted
        if self.selected_factory == -1:
            color = COLORS['selected']
        elif self.ai_highlighted_factory == -1:
            color = (255, 165, 0)  # Orange for AI selection
        else:
            color = COLORS['center']
        
        pygame.draw.rect(self.screen, color, (CENTER_X, CENTER_Y, CENTER_WIDTH, CENTER_HEIGHT))
        pygame.draw.rect(self.screen, COLORS['text'], (CENTER_X, CENTER_Y, CENTER_WIDTH, CENTER_HEIGHT), 2)
        
        # Draw center label
        text = self.font.render("Center", True, COLORS['text'])
        self.screen.blit(text, (CENTER_X + 5, CENTER_Y + 5))
        
        # Draw tiles
        self.draw_tiles_in_rect(self.game.center.tiles, CENTER_X + 10, CENTER_Y + 30, 
                               CENTER_WIDTH - 20, CENTER_HEIGHT - 40, factory_idx=-1)
    
    def draw_players(self):
        """Draw player boards."""
        if not self.game:
            return
            
        for i, player in enumerate(self.game.players):
            x = PLAYER_START_X + i * (PLAYER_WIDTH + PLAYER_SPACING)
            y = WINDOW_HEIGHT - PLAYER_HEIGHT - PLAYER_MARGIN_BOTTOM
            
            # Player background
            pygame.draw.rect(self.screen, COLORS['wall'], (x, y, PLAYER_WIDTH, PLAYER_HEIGHT))
            pygame.draw.rect(self.screen, COLORS['text'], (x, y, PLAYER_WIDTH, PLAYER_HEIGHT), 2)
            
            # Player name and score with round info
            name_text = self.font.render(f"{player.name} - Score: {player.score}", True, COLORS['text'])
            self.screen.blit(name_text, (x + 10, y + 10))
            
            # Show potential floor penalty
            if player.floor_line:
                penalty = self.game._calculate_floor_penalty(len(player.floor_line)) if self.game else 0
                penalty_text = self.small_font.render(f"Floor Penalty: -{penalty}", True, (200, 50, 50))
                self.screen.blit(penalty_text, (x + 10, y + 30))
            
            # Current player indicator
            if i == self.game.current_player_idx:
                pygame.draw.circle(self.screen, COLORS['selected'], (x + PLAYER_WIDTH - 20, y + 20), 8)
            
            # Draw pattern lines
            self.draw_pattern_lines(player, x + PATTERN_LINE_OFFSET_X, y + PATTERN_LINE_OFFSET_Y, i == self.game.current_player_idx)
            
            # Draw floor line
            self.draw_floor_line(player, x + PATTERN_LINE_OFFSET_X, y + PLAYER_HEIGHT - FLOOR_LINE_OFFSET_Y)
    
    def draw_pattern_lines(self, player: Player, x: int, y: int, is_current: bool):
        """Draw player's pattern lines."""
        
        for i, line in enumerate(player.pattern_lines):
            line_y = y + i * PATTERN_LINE_HEIGHT
            
            # Pattern line background - highlight if full and ready to score
            if line.is_full():
                color = (144, 238, 144)  # Light green for completed lines
            elif is_current and self.selected_pattern_line == i:
                color = COLORS['selected']
            else:
                color = COLORS['pattern_line']
            
            pygame.draw.rect(self.screen, color, (x, line_y, PATTERN_LINE_WIDTH, PATTERN_LINE_HEIGHT - 2))
            pygame.draw.rect(self.screen, COLORS['text'], (x, line_y, PATTERN_LINE_WIDTH, PATTERN_LINE_HEIGHT - 2), 1)
            
            # Show potential points for completed lines
            if line.is_full() and self.game:
                potential_points = self.game._calculate_wall_score(player, i, line.tiles[0].color)
                points_text = self.small_font.render(f"+{potential_points}", True, (0, 100, 0))
                self.screen.blit(points_text, (x + PATTERN_LINE_WIDTH + 5, line_y + 5))
            
            # Draw tiles in pattern line
            tile_size = self.get_tile_size()
            for j, tile in enumerate(line.tiles):
                tile_x = x + 5 + j * (tile_size + 2)
                tile_y = line_y + 5
                self.draw_tile(tile, tile_x, tile_y, tile_size, False)
            
            # Draw empty spaces
            for j in range(len(line.tiles), line.capacity):
                tile_x = x + 5 + j * (tile_size + 2)
                tile_y = line_y + 5
                pygame.draw.rect(self.screen, COLORS['white'], (tile_x, tile_y, tile_size, tile_size))
                pygame.draw.rect(self.screen, COLORS['text'], (tile_x, tile_y, tile_size, tile_size), 1)
            
            # Draw wall preview
            wall_x = x + 175
            for j in range(5):
                wall_tile_x = wall_x + j * (tile_size + 2)
                wall_tile_y = line_y + 5
                
                if player.wall.grid[i][j] is not None:
                    self.draw_tile(player.wall.grid[i][j], wall_tile_x, wall_tile_y, tile_size, False)
                else:
                    # Draw empty wall slot with pattern indicator
                    self.draw_wall_slot(wall_tile_x, wall_tile_y, tile_size, i, j)
    
    def draw_wall_slot(self, x: int, y: int, size: int, row: int, col: int):
        """Draw an empty wall slot with pattern indicator based on current mode."""
        from .models import Wall, TileColor
        
        # Get the wall pattern to determine what color goes in this slot
        pattern = Wall.get_wall_pattern()
        expected_color = pattern[row][col]
        
        if self.wall_pattern_mode == "off":
            # Just draw empty white slot
            pygame.draw.rect(self.screen, COLORS['white'], (x, y, size, size))
            pygame.draw.rect(self.screen, COLORS['text'], (x, y, size, size), 1)
        
        elif self.wall_pattern_mode == "subtle":
            # Draw with subtle color tint
            base_color = TILE_COLORS.get(expected_color, COLORS['white'])
            subtle_color = tuple(min(255, c + 200) for c in base_color)  # Lighten the color
            pygame.draw.rect(self.screen, subtle_color, (x, y, size, size))
            pygame.draw.rect(self.screen, COLORS['text'], (x, y, size, size), 1)
        
        elif self.wall_pattern_mode == "letters":
            # Draw white background with color letter
            pygame.draw.rect(self.screen, COLORS['white'], (x, y, size, size))
            pygame.draw.rect(self.screen, COLORS['text'], (x, y, size, size), 1)
            
            # Add color letter
            color_letters = {
                TileColor.BLUE: 'B',
                TileColor.YELLOW: 'Y', 
                TileColor.RED: 'R',
                TileColor.BLACK: 'K',
                TileColor.WHITE: 'W'
            }
            letter = color_letters.get(expected_color, '?')
            letter_surface = self.small_font.render(letter, True, COLORS['text'])
            letter_rect = letter_surface.get_rect(center=(x + size//2, y + size//2))
            self.screen.blit(letter_surface, letter_rect)
        
        elif self.wall_pattern_mode == "outlines":
            # Draw white background with colored outline
            pygame.draw.rect(self.screen, COLORS['white'], (x, y, size, size))
            outline_color = TILE_COLORS.get(expected_color, COLORS['text'])
            pygame.draw.rect(self.screen, outline_color, (x, y, size, size), 2)

    def draw_floor_line(self, player: Player, x: int, y: int):
        """Draw player's floor line with penalty indicators."""
        floor_width = 350
        pygame.draw.rect(self.screen, COLORS['floor'], (x, y, floor_width, 25))
        pygame.draw.rect(self.screen, COLORS['text'], (x, y, floor_width, 25), 2)
        
        text = self.small_font.render("Floor:", True, COLORS['white'])
        self.screen.blit(text, (x + 5, y + 5))
        
        # Draw penalty indicators for each position
        penalties = [1, 1, 2, 2, 2, 3, 3]
        tile_size = self.get_tile_size()
        start_x = x + 50
        
        for i in range(7):  # Show first 7 positions
            pos_x = start_x + i * (tile_size + 2)
            
            # Draw tile if present
            if i < len(player.floor_line):
                self.draw_tile(player.floor_line[i], pos_x, y + 5, tile_size, False)
            else:
                # Draw empty slot
                pygame.draw.rect(self.screen, COLORS['white'], (pos_x, y + 5, tile_size, tile_size))
                pygame.draw.rect(self.screen, COLORS['text'], (pos_x, y + 5, tile_size, tile_size), 1)
            
            # Draw penalty number inside the box only if no tile is present
            if i >= len(player.floor_line):
                penalty = penalties[i] if i < len(penalties) else 3
                penalty_text = self.small_font.render(f"-{penalty}", True, (200, 50, 50))
                penalty_rect = penalty_text.get_rect(center=(pos_x + tile_size // 2, y + 5 + tile_size // 2))
                self.screen.blit(penalty_text, penalty_rect)
        
        # Show additional tiles if more than 7
        if len(player.floor_line) > 7:
            extra_tiles = len(player.floor_line) - 7
            extra_text = self.small_font.render(f"+{extra_tiles} (-3 each)", True, COLORS['text'])
            self.screen.blit(extra_text, (start_x + 7 * (tile_size + 2) + 5, y + 8))
    
    def draw_current_player_info(self):
        """Draw current player information."""
        if not self.game:
            return
            
        current_player = self.game.players[self.game.current_player_idx]
        # Draw basic info
        base_info = f"Current Turn: {current_player.name}"
        
        if self.selected_factory is not None:
            source = "Center" if self.selected_factory == -1 else f"Factory {self.selected_factory + 1}"
            base_info += f" | Selected: {source}"
        
        # Draw base info in normal color
        text_surface = self.font.render(base_info, True, COLORS['text'])
        self.screen.blit(text_surface, (20, 20))
        
        # Draw color info with colored text if color is selected
        if self.selected_color:
            color_text = f" | Color: "
            color_name = self.selected_color.name
            
            # Calculate position after base text
            base_width = text_surface.get_width()
            
            # Draw "| Color: " in normal color
            color_label_surface = self.font.render(color_text, True, COLORS['text'])
            self.screen.blit(color_label_surface, (20 + base_width, 20))
            
            # Draw color name in the actual tile color
            tile_color = TILE_COLORS.get(self.selected_color, COLORS['text'])
            color_name_surface = self.font.render(color_name, True, tile_color)
            self.screen.blit(color_name_surface, (20 + base_width + color_label_surface.get_width(), 20))
        
        # Draw round info
        round_info = "Round in progress"
        if self.game.is_round_over():
            round_info = "Round complete - scoring..."
        elif self.game.game_over:
            winner = self.game.get_winner()
            round_info = f"Game Over - {winner.name} wins!" if winner else "Game Over"
        
        round_text = self.small_font.render(round_info, True, COLORS['text'])
        self.screen.blit(round_text, (700, 20))
    
    def draw_ai_turn_info(self):
        """Draw AI turn progress information."""
        if not self.game or self.ai_turn_state == "idle" or self.game_state == "round_complete":
            return
        
        current_idx = self.game.current_player_idx
        if current_idx not in self.ai_players:
            return
        
        ai_player = self.ai_players[current_idx]
        
        # AI status messages
        status_messages = {
            "thinking": f"{ai_player.name} is thinking...",
            "selecting_source": f"{ai_player.name} is selecting a source...",
            "selecting_color": f"{ai_player.name} is choosing a color...",
            "executing": f"{ai_player.name} is making the move..."
        }
        
        status_text = status_messages.get(self.ai_turn_state, "")
        if status_text:
            # Draw status background
            text_surface = self.font.render(status_text, True, COLORS['white'])
            text_rect = text_surface.get_rect()
            bg_rect = pygame.Rect(WINDOW_WIDTH - text_rect.width - 30, 
                                50, 
                                text_rect.width + 20, 
                                text_rect.height + 10)
            
            pygame.draw.rect(self.screen, (255, 165, 0), bg_rect)
            pygame.draw.rect(self.screen, COLORS['text'], bg_rect, 2)
            
            # Draw status text
            text_pos = (bg_rect.x + 10, bg_rect.y + 5)
            self.screen.blit(text_surface, text_pos)
    
    def draw_moving_tiles(self):
        """Draw tiles that are animating from pattern lines to wall."""
        if not self.moving_tiles:
            return
        
        for tile_anim in self.moving_tiles:
            # Calculate current position using easing
            progress = self.ease_in_out(tile_anim['progress'])
            
            start_x, start_y = tile_anim['start_pos']
            end_x, end_y = tile_anim['end_pos']
            
            current_x = start_x + (end_x - start_x) * progress
            current_y = start_y + (end_y - start_y) * progress
            
            # Draw the moving tile with slight glow effect
            tile_size = self.get_tile_size()
            glow_size = tile_size + 4
            
            # Draw glow
            pygame.draw.rect(self.screen, (255, 255, 0, 100), 
                           (current_x - 2, current_y - 2, glow_size, glow_size))
            
            # Draw the tile
            self.draw_tile(tile_anim['tile'], int(current_x), int(current_y), tile_size, False)
    
    def draw_score_animations(self):
        """Draw score increment animations."""
        if not self.score_animations:
            return
        
        current_time = pygame.time.get_ticks()
        
        # Draw all active score animations
        for score_anim in self.score_animations[:]:
            elapsed = current_time - score_anim['start_time']
            progress = min(1.0, elapsed / 1000)  # 1 second animation
            
            if progress >= 1.0:
                # Remove completed animations
                self.score_animations.remove(score_anim)
                continue
            
            x, y = score_anim['pos']
            score_gain = score_anim['score_gain']
            is_penalty = score_anim.get('is_penalty', False)
            
            # Animate score text floating upward
            offset_y = -40 * progress
            alpha = int(255 * (1 - progress))
            
            # Different colors for positive and negative scores
            if is_penalty:
                color = (200, 50, 50)  # Red for penalties
                text = f"{score_gain}"  # Already negative
            else:
                color = (0, 150, 0)  # Green for positive scores
                text = f"+{score_gain}"
            
            score_text = self.font.render(text, True, color)
            score_text.set_alpha(alpha)
            self.screen.blit(score_text, (x, y + offset_y))
    
    def draw_transition_info(self):
        """Draw round transition status information."""
        if self.round_transition_state == "idle":
            return
        
        # Dynamic scoring message based on current state
        scoring_message = "Scoring completed pattern lines..."
        if self.round_transition_state == "scoring_rows":
            if len(self.scoring_queue) == 0:
                scoring_message = "No completed pattern lines to score..."
            elif self.current_scoring_index < len(self.scoring_queue):
                current_tile = self.scoring_queue[self.current_scoring_index]
                player_name = self.game.players[current_tile['player_idx']].name
                line_num = current_tile['line_idx'] + 1
                scoring_message = f"Scoring {player_name}'s pattern line {line_num}..."
        
        status_messages = {
            "moving_tiles": "Moving tiles to wall...",
            "scoring_rows": scoring_message,
            "scoring_floor": "Applying floor penalties...",
            "clearing_floor": "Clearing floor lines...",
            "setup_next": "Setting up next round..."
        }
        
        status_text = status_messages.get(self.round_transition_state, "")
        if status_text:
            # Draw status background
            text_surface = self.font.render(status_text, True, COLORS['white'])
            text_rect = text_surface.get_rect()
            bg_rect = pygame.Rect(SCREEN_CENTER_X - text_rect.width // 2 - 20, 
                                WINDOW_HEIGHT - 100, 
                                text_rect.width + 40, 
                                text_rect.height + 20)
            
            pygame.draw.rect(self.screen, (70, 130, 180), bg_rect)
            pygame.draw.rect(self.screen, COLORS['text'], bg_rect, 2)
            
            # Draw status text
            text_pos = (bg_rect.x + 20, bg_rect.y + 10)
            self.screen.blit(text_surface, text_pos)
    
    def ease_in_out(self, t: float) -> float:
        """Smooth easing function for animations."""
        return t * t * (3.0 - 2.0 * t)
    
    def draw_tiles_in_rect(self, tiles: List[Tile], x: int, y: int, width: int, height: int, factory_idx: Optional[int] = None):
        """Draw tiles within a rectangle, grouped by color with multi-row support."""
        if not tiles:
            return
        
        # Group tiles by color
        from collections import defaultdict
        color_groups = defaultdict(list)
        for tile in tiles:
            if tile.color != TileColor.FIRST_PLAYER:
                color_groups[tile.color].append(tile)
        
        # Add first player token separately if present
        first_player_tiles = [tile for tile in tiles if tile.color == TileColor.FIRST_PLAYER]
        
        # Calculate tile size - make smaller for many tiles
        total_tiles = len(tiles)
        max_tiles_per_row = width // 12  # Minimum 12px per tile
        rows_needed = max(1, (total_tiles + max_tiles_per_row - 1) // max_tiles_per_row)
        
        tile_size = min(width // min(total_tiles, max_tiles_per_row), height // rows_needed) - 2
        tile_size = max(tile_size, 8)  # Minimum size
        
        # Draw grouped tiles with wrapping
        current_x = x
        current_y = y
        tiles_in_row = 0
        
        # Sort colors for consistent visual order
        sorted_colors = sorted(color_groups.keys(), key=lambda c: c.value if hasattr(c, 'value') else str(c))
        
        for color in sorted_colors:
            color_tiles = color_groups[color]
            
            # Highlight AI selected color group only in the selected factory/center
            should_highlight = (self.ai_highlighted_color == color and 
                              self.ai_highlighted_factory == factory_idx)
            
            if should_highlight:
                # Calculate highlight area for this color group
                highlight_tiles = len(color_tiles)
                remaining_in_row = max_tiles_per_row - tiles_in_row
                
                if highlight_tiles <= remaining_in_row:
                    # All tiles fit in current row
                    highlight_width = highlight_tiles * (tile_size + 2)
                    pygame.draw.rect(self.screen, (0, 255, 0), 
                                   (current_x - 2, current_y - 2, highlight_width + 2, tile_size + 4))
                else:
                    # Tiles span multiple rows - highlight each row separately
                    tiles_to_highlight = highlight_tiles
                    highlight_x = current_x
                    highlight_y = current_y
                    
                    while tiles_to_highlight > 0:
                        tiles_this_row = min(tiles_to_highlight, remaining_in_row if highlight_y == current_y else max_tiles_per_row)
                        highlight_width = tiles_this_row * (tile_size + 2)
                        pygame.draw.rect(self.screen, (0, 255, 0), 
                                       (highlight_x - 2, highlight_y - 2, highlight_width + 2, tile_size + 4))
                        
                        tiles_to_highlight -= tiles_this_row
                        highlight_y += tile_size + 4
                        highlight_x = x
                        remaining_in_row = max_tiles_per_row
            
            for i, tile in enumerate(color_tiles):
                # Check if we need to wrap to next row
                if tiles_in_row >= max_tiles_per_row:
                    current_y += tile_size + 4
                    current_x = x
                    tiles_in_row = 0
                
                # Check if we're still within the height bounds
                if current_y + tile_size <= y + height:
                    # Determine if this tile should be highlighted
                    should_highlight_tile = (self.selected_factory == factory_idx and 
                                           self.selected_color == tile.color and 
                                           tile.color != TileColor.FIRST_PLAYER)
                    self.draw_tile(tile, current_x, current_y, tile_size, should_highlight_tile)
                    current_x += tile_size + 2
                    tiles_in_row += 1
                else:
                    break
        
        # Draw first player token at the end
        for tile in first_player_tiles:
            # Check if we need to wrap to next row
            if tiles_in_row >= max_tiles_per_row:
                current_y += tile_size + 4
                current_x = x
                tiles_in_row = 0
            
            # Check if we're still within the height bounds
            if current_y + tile_size <= y + height:
                # First player token is never highlighted by color selection
                self.draw_tile(tile, current_x, current_y, tile_size, False)
                current_x += tile_size + 2
                tiles_in_row += 1
    
    def draw_tile(self, tile: Tile, x: int, y: int, size: int, highlight: bool = False):
        """Draw a single tile."""
        # Use the highlight parameter passed from the calling method
        is_selected = highlight
        
        if tile.color == TileColor.FIRST_PLAYER:
            # Ornate white square tile design
            center_x, center_y = x + size // 2, y + size // 2
            
            # Draw main white square
            pygame.draw.rect(self.screen, (250, 250, 250), (x, y, size, size))
            
            # Draw ornate border with multiple layers
            # Outer border - dark gold
            pygame.draw.rect(self.screen, (184, 134, 11), (x, y, size, size), 2)
            # Inner border - light gold
            pygame.draw.rect(self.screen, (255, 215, 0), (x + 2, y + 2, size - 4, size - 4), 1)
            
            # Draw decorative corner elements
            corner_size = max(2, size // 8)
            corner_color = (184, 134, 11)
            
            # Top-left corner decoration
            pygame.draw.rect(self.screen, corner_color, (x + 3, y + 3, corner_size, corner_size))
            # Top-right corner decoration
            pygame.draw.rect(self.screen, corner_color, (x + size - 3 - corner_size, y + 3, corner_size, corner_size))
            # Bottom-left corner decoration
            pygame.draw.rect(self.screen, corner_color, (x + 3, y + size - 3 - corner_size, corner_size, corner_size))
            # Bottom-right corner decoration
            pygame.draw.rect(self.screen, corner_color, (x + size - 3 - corner_size, y + size - 3 - corner_size, corner_size, corner_size))
            
            # Draw central ornate frame
            if size > 16:
                frame_margin = size // 4
                frame_rect = (x + frame_margin, y + frame_margin, size - 2 * frame_margin, size - 2 * frame_margin)
                pygame.draw.rect(self.screen, (255, 215, 0), frame_rect, 1)
            
            # Draw "1" in the center with ornate styling
            if size > 12:
                font_to_use = self.font if size > 20 else self.small_font
                # Draw shadow first
                shadow_text = font_to_use.render("1", True, (100, 100, 100))
                shadow_rect = shadow_text.get_rect(center=(center_x + 1, center_y + 1))
                self.screen.blit(shadow_text, shadow_rect)
                # Draw main text
                text = font_to_use.render("1", True, (184, 134, 11))  # Dark gold
                text_rect = text.get_rect(center=(center_x, center_y))
                self.screen.blit(text, text_rect)
        else:
            # Regular tile design
            color = TILE_COLORS.get(tile.color, COLORS['white'])
            
            # Highlight selected tiles with thin border (similar to AI thinking)
            if is_selected:
                # Draw thin highlight border (similar to AI highlighting scheme)
                pygame.draw.rect(self.screen, (0, 255, 0), (x - 2, y - 2, size + 4, size + 4), 2)
            
            pygame.draw.rect(self.screen, color, (x, y, size, size))
            pygame.draw.rect(self.screen, COLORS['text'], (x, y, size, size), 1)
            
            # Draw tile letter
            if size > 12:
                letter = str(tile)[0] if str(tile) else '?'
                text_color = COLORS['text']
                if is_selected:
                    text_color = (0, 0, 0)  # Black text for better contrast on highlighted tiles
                text = self.small_font.render(letter, True, text_color)
                text_rect = text.get_rect(center=(x + size // 2, y + size // 2))
                self.screen.blit(text, text_rect)
    
    def get_clicked_factory(self, x: int, y: int) -> Optional[int]:
        """Get which factory was clicked."""
        for i in range(len(self.game.factories) if self.game else 0):
            factory_x = FACTORY_START_X + (i % 3) * (FACTORY_SIZE + FACTORY_SPACING)
            factory_y = FACTORY_START_Y + (i // 3) * (FACTORY_SIZE + FACTORY_SPACING)
            
            if (factory_x <= x <= factory_x + FACTORY_SIZE and 
                factory_y <= y <= factory_y + FACTORY_SIZE):
                return i
        return None
    
    def is_center_clicked(self, x: int, y: int) -> bool:
        """Check if center was clicked."""
        return (CENTER_X <= x <= CENTER_X + CENTER_WIDTH and 
                CENTER_Y <= y <= CENTER_Y + CENTER_HEIGHT)
    
    def get_available_colors(self) -> List[TileColor]:
        """Get available colors from the selected source in visual display order."""
        if not self.game or self.selected_factory is None:
            return []
        
        if self.selected_factory == -1:  # Center
            tiles = self.game.center.tiles
        else:  # Factory
            factory = self.game.factories[self.selected_factory]
            tiles = factory.tiles
        
        # Get colors in the order they appear visually (grouped)
        seen_colors = []
        available_colors = []
        
        # Sort colors for consistent visual grouping
        color_groups = {}
        for tile in tiles:
            if tile.color != TileColor.FIRST_PLAYER:
                if tile.color not in color_groups:
                    color_groups[tile.color] = []
                color_groups[tile.color].append(tile)
        
        # Return colors in sorted order (same as visual display)
        sorted_colors = sorted(color_groups.keys(), key=lambda c: c.value if hasattr(c, 'value') else str(c))
        return sorted_colors
    
    def get_first_available_color(self) -> Optional[TileColor]:
        """Get the first available color from the selected source."""
        colors = self.get_available_colors()
        return colors[0] if colors else None
    
    def cycle_color(self):
        """Cycle to the next available color."""
        colors = self.get_available_colors()
        if not colors:
            self.selected_color = None
            return
        
        if self.selected_color is None:
            self.selected_color = colors[0]
        else:
            try:
                current_index = colors.index(self.selected_color)
                next_index = (current_index + 1) % len(colors)
                self.selected_color = colors[next_index]
            except ValueError:
                # Current color not in available colors, select first
                self.selected_color = colors[0]
    
    
    def get_clicked_pattern_line(self, x: int, y: int) -> Optional[int]:
        """Get which pattern line was clicked."""
        if not self.game:
            return None
            
        current_player_idx = self.game.current_player_idx
        if current_player_idx in self.ai_players:
            return None
            
        player_x = PLAYER_START_X + current_player_idx * (PLAYER_WIDTH + PLAYER_SPACING)
        player_y = WINDOW_HEIGHT - PLAYER_HEIGHT - PLAYER_MARGIN_BOTTOM
        
        pattern_x = player_x + PATTERN_LINE_OFFSET_X
        pattern_y = player_y + PATTERN_LINE_OFFSET_Y
        
        for i in range(5):
            line_y = pattern_y + i * PATTERN_LINE_HEIGHT
            if (pattern_x <= x <= pattern_x + PATTERN_LINE_WIDTH and 
                line_y <= y <= line_y + PATTERN_LINE_HEIGHT - 2):
                return i
        
        # Check floor line
        floor_y = player_y + PLAYER_HEIGHT - FLOOR_LINE_OFFSET_Y
        if (pattern_x <= x <= pattern_x + 300 and 
            floor_y <= y <= floor_y + 25):
            return -1  # Floor line
            
        return None

def main():
    """Main entry point for the UI."""
    ui = AzulUI()
    ui.run()

if __name__ == "__main__":
    main()
