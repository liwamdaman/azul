from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple
import numpy as np

class TileColor(Enum):
    BLUE = auto()
    YELLOW = auto()
    RED = auto()
    BLACK = auto()
    CYAN = auto()
    FIRST_PLAYER = auto()  # Special marker for first player token

@dataclass
class Tile:
    color: TileColor
    
    def __str__(self) -> str:
        return self.color.name[0]  # First letter of color name

@dataclass
class PatternLine:
    capacity: int
    tiles: List[Tile] = field(default_factory=list)
    
    def is_full(self) -> bool:
        return len(self.tiles) == self.capacity
    
    def add_tile(self, tile: Tile) -> bool:
        """Add a tile to the pattern line if there's space and color matches."""
        if len(self.tiles) >= self.capacity:
            return False
            
        # Check color consistency - all tiles in a pattern line must be the same color
        if self.tiles and self.tiles[0].color != tile.color:
            return False
            
        self.tiles.append(tile)
        return True

@dataclass
class Wall:
    """Represents a player's wall where tiles are placed."""
    SIZE = 5
    
    def __init__(self):
        self.grid = np.full((self.SIZE, self.SIZE), None, dtype=object)
        # Initialize wall with empty spaces
        
    def can_place_tile(self, row: int, color: TileColor) -> bool:
        """Check if a tile of given color can be placed in the specified row."""
        if row < 0 or row >= self.SIZE:
            return False
        
        # Check if color already exists in row
        return all(tile.color != color for tile in self.grid[row] if tile is not None)
    
    def place_tile(self, row: int, color: TileColor) -> bool:
        """Place a tile in the wall if possible. Returns True if successful."""
        if not self.can_place_tile(row, color):
            return False
            
        # Calculate the column based on the row and color
        col = (row + list(TileColor).index(color)) % self.SIZE
        self.grid[row][col] = Tile(color)
        return True
    
    @staticmethod
    def get_wall_pattern() -> List[List[TileColor]]:
        """Get the standard Azul wall pattern showing which color goes in each position."""
        # Get colors excluding FIRST_PLAYER
        colors = [c for c in TileColor if c != TileColor.FIRST_PLAYER]
        pattern = []
        
        for row in range(5):
            row_pattern = []
            for col in range(5):
                # Each row shifts the pattern by the row index
                color_idx = (col - row) % len(colors)
                row_pattern.append(colors[color_idx])
            pattern.append(row_pattern)
        
        return pattern

@dataclass
class Player:
    """Represents a player in the game."""
    name: str
    wall: Wall = field(default_factory=Wall)
    pattern_lines: List[PatternLine] = field(default_factory=list)
    floor_line: List[Tile] = field(default_factory=list)
    score: int = 0
    
    def __post_init__(self):
        # Initialize pattern lines with capacities 1-5
        self.pattern_lines = [PatternLine(capacity=i+1) for i in range(5)]
    
    def add_to_pattern_line(self, line_idx: int, tiles: List[Tile]) -> List[Tile]:
        """Add tiles to a pattern line. Returns any overflow tiles."""
        if line_idx < 0 or line_idx >= len(self.pattern_lines):
            return tiles
        
        # Check if this color can be placed on the wall at this row
        if tiles and not self.wall.can_place_tile(line_idx, tiles[0].color):
            return tiles  # Return all tiles as overflow if color already exists in wall row
            
        line = self.pattern_lines[line_idx]
        remaining = []
        
        for tile in tiles:
            if not line.add_tile(tile):
                remaining.append(tile)
                
        return remaining
    
    def score_wall(self) -> int:
        """Score the current wall and update player's score."""
        # TODO: Implement wall scoring logic
        return 0

@dataclass
class Factory:
    """Represents a factory that holds tiles."""
    MAX_TILES = 4
    tiles: List[Tile] = field(default_factory=list)
    
    def is_empty(self) -> bool:
        return len(self.tiles) == 0
    
    def take_tiles(self, color: TileColor) -> List[Tile]:
        """Take all tiles of the specified color. Returns the taken tiles."""
        taken = [t for t in self.tiles if t.color == color]
        remaining = [t for t in self.tiles if t.color != color]
        self.tiles = remaining
        return taken
    
    def remaining_tiles(self) -> List[Tile]:
        """Get all remaining tiles in the factory."""
        return self.tiles.copy()

@dataclass
class Center:
    """The center area where tiles are placed when factories are empty."""
    tiles: List[Tile] = field(default_factory=list)
    first_player_taken: bool = False
    
    def add_tiles(self, tiles: List[Tile]) -> None:
        """Add tiles to the center."""
        self.tiles.extend(tiles)
    
    def take_tiles(self, color: TileColor) -> Tuple[List[Tile], bool]:
        """
        Take all tiles of the specified color.
        Returns a tuple of (taken_tiles, took_first_player)
        """
        took_first = False
        if TileColor.FIRST_PLAYER in [t.color for t in self.tiles]:
            took_first = True
            self.first_player_taken = True
            
        taken = [t for t in self.tiles if t.color == color]
        remaining = [t for t in self.tiles 
                    if t.color != color and t.color != TileColor.FIRST_PLAYER]
        
        self.tiles = remaining
        return taken, took_first
    
    def is_empty(self) -> bool:
        return len(self.tiles) == 0
