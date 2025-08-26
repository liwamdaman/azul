import pytest
from azul.models import Tile, TileColor, PatternLine, Wall, Player

def test_tile_creation():
    """Test that tiles are created with the correct color."""
    tile = Tile(TileColor.BLUE)
    assert tile.color == TileColor.BLUE
    assert str(tile) == 'B'

def test_pattern_line():
    """Test pattern line functionality."""
    line = PatternLine(capacity=3)
    assert line.capacity == 3
    assert not line.is_full()
    
    # Add tiles up to capacity
    assert line.add_tile(Tile(TileColor.BLUE))
    assert line.add_tile(Tile(TileColor.BLUE))
    assert line.add_tile(Tile(TileColor.BLUE))
    assert line.is_full()
    
    # Should not be able to add more tiles
    assert not line.add_tile(Tile(TileColor.BLUE))

def test_pattern_line_color_consistency():
    """Test that pattern lines enforce color consistency."""
    line = PatternLine(capacity=3)
    
    # Add first tile
    assert line.add_tile(Tile(TileColor.BLUE))
    assert len(line.tiles) == 1
    
    # Should be able to add same color
    assert line.add_tile(Tile(TileColor.BLUE))
    assert len(line.tiles) == 2
    
    # Should NOT be able to add different color
    assert not line.add_tile(Tile(TileColor.RED))
    assert len(line.tiles) == 2  # Should remain unchanged
    
    # Should still be able to add original color
    assert line.add_tile(Tile(TileColor.BLUE))
    assert len(line.tiles) == 3
    assert line.is_full()

def test_wall_placement():
    """Test wall tile placement rules."""
    wall = Wall()
    
    # Should be able to place first tile in row
    assert wall.place_tile(0, TileColor.BLUE)
    
    # Should not be able to place same color in same row
    assert not wall.place_tile(0, TileColor.BLUE)
    
    # Should be able to place different color in same row
    assert wall.place_tile(0, TileColor.RED)

def test_player_initialization():
    """Test player initialization."""
    player = Player("Test Player")
    assert player.name == "Test Player"
    assert player.score == 0
    assert len(player.pattern_lines) == 5
    assert len(player.floor_line) == 0
    
    # Check pattern line capacities
    for i, line in enumerate(player.pattern_lines, 1):
        assert line.capacity == i
