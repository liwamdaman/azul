from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import random
from .models import Tile, TileColor, Player, PatternLine, Wall, Factory, Center


class AzulGame:
    """Main game class that manages the game state and flow."""
    # Game constants
    NUM_FACTORIES = 5  # For 2-3 players
    TILES_PER_COLOR = 20
    TILES_PER_FACTORY = 4
    WALL_SIZE = 5
    
    # Bonus points
    ROW_BONUS = 2
    COLUMN_BONUS = 7
    COLOR_SET_BONUS = 10
    
    # Floor line penalties: -1, -1, -2, -2, -2, -3, -3 for positions 1-7+
    FLOOR_PENALTIES = [1, 1, 2, 2, 2, 3, 3]
    FLOOR_PENALTY_OVERFLOW = 3
    
    def __init__(self, player_names: List[str]):
        self.players = [Player(name) for name in player_names]
        self.current_player_idx = 0
        self.first_player_idx = 0
        self.game_over = False
        self.factories = [Factory() for _ in range(self.NUM_FACTORIES)]
        self.center = Center()
        self.bag = self._initialize_bag()
        self.discard_pile: List[Tile] = []
    
    @property
    def game_colors(self) -> List[TileColor]:
        """Get list of game colors (excluding FIRST_PLAYER token)."""
        return [c for c in TileColor if c != TileColor.FIRST_PLAYER]
        
    def _initialize_bag(self) -> List[Tile]:
        """Initialize the bag with all tiles."""
        bag = []
        # TILES_PER_COLOR tiles of each game color
        for color in self.game_colors:
            bag.extend([Tile(color) for _ in range(self.TILES_PER_COLOR)])
        random.shuffle(bag)
        return bag
    
    def setup_round(self) -> None:
        """Set up a new round by filling factories with tiles."""
        # Reset first player token availability and add to center
        self.center.first_player_taken = False
        self.center.tiles.append(Tile(TileColor.FIRST_PLAYER))
        
        # Fill each factory with TILES_PER_FACTORY tiles
        for factory in self.factories:
            factory.tiles = self._draw_tiles(self.TILES_PER_FACTORY)
    
    def _draw_tiles(self, count: int) -> List[Tile]:
        """Draw tiles from the bag. Refill from discard if needed."""
        if len(self.bag) < count:
            # Move discard pile back to bag and shuffle
            self.bag.extend(self.discard_pile)
            self.discard_pile = []
            random.shuffle(self.bag)
            
            if len(self.bag) < count:
                # Still not enough tiles, return what we have
                count = len(self.bag)
                
        drawn = self.bag[:count]
        self.bag = self.bag[count:]
        return drawn
    
    def take_tiles_from_factory(self, factory_idx: int, color: TileColor, 
                              pattern_line_idx: int) -> bool:
        """
        Take tiles of a specific color from a factory.
        Returns True if the move was successful.
        """
        if factory_idx < 0 or factory_idx >= len(self.factories):
            return False
            
        factory = self.factories[factory_idx]
        if factory.is_empty():
            return False
            
        # Take tiles from factory
        taken_tiles = factory.take_tiles(color)
        if not taken_tiles:
            return False
            
        # Move remaining tiles to center
        remaining = factory.remaining_tiles()
        if remaining:
            self.center.add_tiles(remaining)
            factory.tiles = []
        
        # Add tiles to player's pattern line or floor
        player = self.players[self.current_player_idx]
        overflow = player.add_to_pattern_line(pattern_line_idx, taken_tiles)
        
        # Any overflow goes to the floor line
        if overflow:
            player.floor_line.extend(overflow)
        
        self._next_player()
        return True
    
    def take_tiles_from_center(self, color: TileColor, 
                             pattern_line_idx: int) -> bool:
        """Take tiles of a specific color from the center."""
        if self.center.is_empty():
            return False
            
        taken_tiles, took_first = self.center.take_tiles(color)
        if not taken_tiles:
            return False
            
        player = self.players[self.current_player_idx]
        overflow = player.add_to_pattern_line(pattern_line_idx, taken_tiles)
        
        # Any overflow goes to the floor line
        if overflow:
            player.floor_line.extend(overflow)
            
        # If player took first player token, they go first next round and add token to floor
        if took_first:
            self.first_player_idx = self.current_player_idx
            player.floor_line.append(Tile(TileColor.FIRST_PLAYER))
            
        self._next_player()
        return True
    
    def _next_player(self) -> None:
        """Move to the next player's turn."""
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
    
    def is_round_over(self) -> bool:
        """Check if the current round is over."""
        # Round is over when all factories and center are empty
        factories_empty = all(factory.is_empty() for factory in self.factories)
        center_empty = self.center.is_empty()
        return factories_empty and center_empty
    
    def score_round(self) -> None:
        """Score the current round and prepare for the next one."""
        for player in self.players:
            # Score completed pattern lines
            for i, line in enumerate(player.pattern_lines):
                if line.is_full():
                    # Move one tile to wall, rest to discard
                    tile_color = line.tiles[0].color
                    if player.wall.place_tile(i, tile_color):
                        # Score the placed tile
                        points = self._calculate_wall_score(player, i, tile_color)
                        player.score += points
                    
                    # Move remaining tiles to discard pile, then clear the pattern line
                    if len(line.tiles) > 1:  # One tile went to wall, rest go to discard
                        self.discard_pile.extend(line.tiles[1:])
                    line.tiles.clear()
            
            # Score floor line (negative points)
            floor_penalty = self._calculate_floor_penalty(len(player.floor_line))
            player.score = max(0, player.score - floor_penalty)  # Score can't go below 0
            
            # Move floor line tiles to discard pile (excluding first player token)
            for tile in player.floor_line:
                if tile.color != TileColor.FIRST_PLAYER:
                    self.discard_pile.append(tile)
            player.floor_line.clear()
        
        # Clear any remaining tiles from factories and center (move to discard)
        for factory in self.factories:
            self.discard_pile.extend(factory.tiles)
            factory.tiles = []
        
        # Clear center tiles (excluding first player token)
        center_tiles = [t for t in self.center.tiles if t.color != TileColor.FIRST_PLAYER]
        self.discard_pile.extend(center_tiles)
        self.center.tiles = [t for t in self.center.tiles if t.color == TileColor.FIRST_PLAYER]
        
        # Check for game end condition
        for player in self.players:
            for row in player.wall.grid:
                if all(tile is not None for tile in row):
                    self.game_over = True
                    break
            if self.game_over:
                break
        
        # Prepare for next round
        if not self.game_over:
            self.current_player_idx = self.first_player_idx
            self.setup_round()
    
    def _calculate_wall_score(self, player: Player, row: int, color: TileColor) -> int:
        """Calculate points for placing a tile on the wall."""
        # Calculate the column where this color should be placed
        try:
            col = (row + self.game_colors.index(color)) % self.WALL_SIZE
        except ValueError:
            return 1  # Fallback for invalid color
        
        points = 1
        
        # Count horizontal adjacent tiles
        horizontal = 1
        # Count left
        for j in range(col - 1, -1, -1):
            if player.wall.grid[row][j] is not None:
                horizontal += 1
            else:
                break
        # Count right
        for j in range(col + 1, self.WALL_SIZE):
            if player.wall.grid[row][j] is not None:
                horizontal += 1
            else:
                break
        
        # Count vertical adjacent tiles
        vertical = 1
        # Count up
        for i in range(row - 1, -1, -1):
            if player.wall.grid[i][col] is not None:
                vertical += 1
            else:
                break
        # Count down
        for i in range(row + 1, self.WALL_SIZE):
            if player.wall.grid[i][col] is not None:
                vertical += 1
            else:
                break
        
        # Debug output for testing
        # print(f"Scoring tile at ({row}, {col}): horizontal={horizontal}, vertical={vertical}")
        
        # Score is the sum of horizontal and vertical chains
        # But if there's only one direction with connections, count just that
        # If both directions have connections, add them together
        if horizontal > 1 and vertical > 1:
            # Both horizontal and vertical connections exist
            return horizontal + vertical
        else:
            # Only one direction has connections (or neither)
            return max(horizontal, vertical)
    
    def _calculate_floor_penalty(self, floor_tiles: int) -> int:
        """Calculate penalty points for floor line tiles."""
        total_penalty = 0
        
        for i in range(min(floor_tiles, len(self.FLOOR_PENALTIES))):
            total_penalty += self.FLOOR_PENALTIES[i]
        
        # Any tiles beyond the penalty array are FLOOR_PENALTY_OVERFLOW each
        if floor_tiles > len(self.FLOOR_PENALTIES):
            total_penalty += (floor_tiles - len(self.FLOOR_PENALTIES)) * self.FLOOR_PENALTY_OVERFLOW
        
        return total_penalty
    
    def get_floor_penalty_for_position(self, position: int) -> int:
        """Get the penalty value for a specific floor position (0-indexed)."""
        if position < len(self.FLOOR_PENALTIES):
            return self.FLOOR_PENALTIES[position]
        return self.FLOOR_PENALTY_OVERFLOW  # Any position beyond array length
    
    def execute_move(self, move) -> bool:
        """Execute a move from an AI player. Returns True if successful."""
        from .ai import Move  # Import here to avoid circular imports
        
        if move.source_type == "factory":
            return self.take_tiles_from_factory(
                move.source_index, move.color, move.pattern_line
            )
        elif move.source_type == "center":
            return self.take_tiles_from_center(move.color, move.pattern_line)
        return False
    
    def _calculate_end_game_bonuses(self, player: Player) -> int:
        """Calculate end-of-game bonus points for a player."""
        bonus_points = 0
        
        # Completed horizontal rows: ROW_BONUS points each
        for row in player.wall.grid:
            if all(tile is not None for tile in row):
                bonus_points += self.ROW_BONUS
        
        # Completed vertical columns: COLUMN_BONUS points each
        for col in range(self.WALL_SIZE):
            if all(player.wall.grid[row][col] is not None for row in range(self.WALL_SIZE)):
                bonus_points += self.COLUMN_BONUS
        
        # Completed color sets: COLOR_SET_BONUS points each
        for color in self.game_colors:
            # Check if all WALL_SIZE tiles of this color are placed
            color_count = 0
            for row in range(self.WALL_SIZE):
                col = (row + self.game_colors.index(color)) % self.WALL_SIZE
                if player.wall.grid[row][col] is not None:
                    color_count += 1
            if color_count == self.WALL_SIZE:
                bonus_points += self.COLOR_SET_BONUS
        
        return bonus_points

    def get_winner(self) -> Optional[Player]:
        """Determine the winner of the game."""
        if not self.game_over:
            return None
        
        # Find winner (highest score, with tie-breaking by completed horizontal rows)
        def player_score_key(player: Player) -> Tuple[int, int]:
            completed_rows = sum(1 for row in player.wall.grid if all(tile is not None for tile in row))
            return (player.score, completed_rows)
        
        return max(self.players, key=player_score_key)
