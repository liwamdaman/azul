import pytest
from azul.models import Factory, Center, Tile, TileColor

class TestFactory:
    """Test suite for Factory class."""
    
    def test_factory_initialization(self):
        """Test factory starts empty."""
        factory = Factory()
        assert len(factory.tiles) == 0
        assert factory.is_empty()
    
    def test_factory_add_tiles(self):
        """Test adding tiles to factory."""
        factory = Factory()
        tiles = [Tile(TileColor.BLUE), Tile(TileColor.RED)]
        
        factory.tiles.extend(tiles)
        assert len(factory.tiles) == 2
        assert not factory.is_empty()
    
    def test_factory_take_color(self):
        """Test taking tiles of specific color from factory."""
        factory = Factory()
        factory.tiles = [
            Tile(TileColor.BLUE), Tile(TileColor.BLUE),
            Tile(TileColor.RED), Tile(TileColor.CYAN)
        ]
        
        # Take blue tiles
        taken = factory.take_tiles(TileColor.BLUE)
        remaining = factory.remaining_tiles()
        
        assert len(taken) == 2
        assert all(tile.color == TileColor.BLUE for tile in taken)
        assert len(remaining) == 2
        assert TileColor.RED in [tile.color for tile in remaining]
        assert TileColor.CYAN in [tile.color for tile in remaining]
    
    def test_factory_take_nonexistent_color(self):
        """Test taking color that doesn't exist in factory."""
        factory = Factory()
        factory.tiles = [Tile(TileColor.BLUE), Tile(TileColor.RED)]
        
        taken = factory.take_tiles(TileColor.CYAN)
        
        assert len(taken) == 0
        # Factory should still have original tiles
        assert len(factory.tiles) == 2
    
    def test_factory_get_available_colors(self):
        """Test getting available colors from factory."""
        factory = Factory()
        factory.tiles = [
            Tile(TileColor.BLUE), Tile(TileColor.BLUE),
            Tile(TileColor.RED), Tile(TileColor.CYAN)
        ]
        
        colors = set(tile.color for tile in factory.tiles)
        expected_colors = {TileColor.BLUE, TileColor.RED, TileColor.CYAN}
        assert colors == expected_colors
    
    def test_factory_max_tiles_constraint(self):
        """Test factory respects max tiles constraint."""
        factory = Factory()
        
        # Add exactly max tiles
        tiles = [Tile(TileColor.BLUE)] * Factory.MAX_TILES
        factory.tiles.extend(tiles)
        
        # Should have MAX_TILES
        assert len(factory.tiles) == Factory.MAX_TILES

class TestCenter:
    """Test suite for Center class."""
    
    def test_center_initialization(self):
        """Test center starts empty."""
        center = Center()
        assert len(center.tiles) == 0
        assert center.is_empty()
    
    def test_center_add_tiles(self):
        """Test adding tiles to center."""
        center = Center()
        tiles = [Tile(TileColor.BLUE), Tile(TileColor.RED)]
        
        center.add_tiles(tiles)
        assert len(center.tiles) == 2
        assert not center.is_empty()
    
    def test_center_take_color(self):
        """Test taking tiles of specific color from center."""
        center = Center()
        center.tiles = [
            Tile(TileColor.BLUE), Tile(TileColor.BLUE),
            Tile(TileColor.RED), Tile(TileColor.FIRST_PLAYER)
        ]
        
        # Take blue tiles
        taken, took_first = center.take_tiles(TileColor.BLUE)
        
        assert len(taken) == 2
        assert all(tile.color == TileColor.BLUE for tile in taken)
        assert took_first  # Should take first player token
        
        # Center should have remaining tiles (only RED, first player removed)
        assert len(center.tiles) == 1
        assert center.tiles[0].color == TileColor.RED
    
    def test_center_take_first_player_token(self):
        """Test taking first player token from center."""
        center = Center()
        center.tiles = [
            Tile(TileColor.BLUE), Tile(TileColor.FIRST_PLAYER)
        ]
        
        # Take any color should also take first player token
        taken, took_first = center.take_tiles(TileColor.BLUE)
        
        # Should get blue tile and first player flag
        assert len(taken) == 1
        assert taken[0].color == TileColor.BLUE
        assert took_first
        
        # Center should be empty
        assert center.is_empty()
    
    def test_center_get_available_colors(self):
        """Test getting available colors from center."""
        center = Center()
        center.tiles = [
            Tile(TileColor.BLUE), Tile(TileColor.RED),
            Tile(TileColor.FIRST_PLAYER)
        ]
        
        colors = set(tile.color for tile in center.tiles if tile.color != TileColor.FIRST_PLAYER)
        # Should not include FIRST_PLAYER in available colors
        expected_colors = {TileColor.BLUE, TileColor.RED}
        assert colors == expected_colors
    
    def test_center_has_first_player_token(self):
        """Test detection of first player token in center."""
        center = Center()
        
        # Initially no first player token
        has_first = any(tile.color == TileColor.FIRST_PLAYER for tile in center.tiles)
        assert not has_first
        
        # Add first player token
        center.tiles = [Tile(TileColor.FIRST_PLAYER)]
        has_first = any(tile.color == TileColor.FIRST_PLAYER for tile in center.tiles)
        assert has_first
        
        # Add other tiles
        center.tiles.append(Tile(TileColor.BLUE))
        has_first = any(tile.color == TileColor.FIRST_PLAYER for tile in center.tiles)
        assert has_first
    
    def test_center_take_nonexistent_color(self):
        """Test taking color that doesn't exist in center."""
        center = Center()
        center.tiles = [Tile(TileColor.BLUE), Tile(TileColor.RED)]
        
        taken, took_first = center.take_tiles(TileColor.CYAN)
        
        assert len(taken) == 0
        assert not took_first
        # Center should still have original tiles
        assert len(center.tiles) == 2
    
    def test_center_unlimited_capacity(self):
        """Test center can hold many tiles (unlike factories)."""
        center = Center()
        
        # Add many tiles (more than factory max)
        tiles = [Tile(TileColor.BLUE)] * 20
        center.add_tiles(tiles)
        
        # Should accept all tiles
        assert len(center.tiles) == 20
