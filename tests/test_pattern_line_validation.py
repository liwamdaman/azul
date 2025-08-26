import unittest
from azul.models import Player, TileColor, Tile


class TestPatternLineValidation(unittest.TestCase):
    """Test pattern line color validation against wall placement."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.player = Player("Test Player")
    
    def test_add_to_pattern_line_valid_placement(self):
        """Test adding tiles to pattern line when color not in wall row."""
        # Add blue tiles to pattern line 0 (wall row 0 doesn't have blue)
        tiles = [Tile(TileColor.BLUE)]
        overflow = self.player.add_to_pattern_line(0, tiles)
        
        self.assertEqual(len(overflow), 0)  # No overflow
        self.assertEqual(len(self.player.pattern_lines[0].tiles), 1)
        self.assertEqual(self.player.pattern_lines[0].tiles[0].color, TileColor.BLUE)
    
    def test_add_to_pattern_line_blocked_by_wall(self):
        """Test that adding tiles is blocked when color exists in wall row."""
        # First place a blue tile in the wall at row 0
        self.player.wall.place_tile(0, TileColor.BLUE)
        
        # Try to add blue tiles to pattern line 0
        tiles = [Tile(TileColor.BLUE), Tile(TileColor.BLUE)]
        overflow = self.player.add_to_pattern_line(0, tiles)
        
        self.assertEqual(len(overflow), 2)  # All tiles returned as overflow
        self.assertEqual(len(self.player.pattern_lines[0].tiles), 0)  # No tiles should be added
    
    def test_add_to_pattern_line_different_row_allowed(self):
        """Test that same color can be added to different pattern line if wall allows."""
        # Place blue tile in wall row 0
        self.player.wall.place_tile(0, TileColor.BLUE)
        
        # Should still be able to add blue to pattern line 1 (different row)
        tiles = [Tile(TileColor.BLUE)]
        overflow = self.player.add_to_pattern_line(1, tiles)
        
        self.assertEqual(len(overflow), 0)  # No overflow
        self.assertEqual(len(self.player.pattern_lines[1].tiles), 1)
        self.assertEqual(self.player.pattern_lines[1].tiles[0].color, TileColor.BLUE)
    
    def test_add_to_pattern_line_multiple_colors_in_wall(self):
        """Test validation with multiple colors already in wall."""
        # Place multiple tiles in wall row 2
        self.player.wall.place_tile(2, TileColor.RED)
        self.player.wall.place_tile(2, TileColor.YELLOW)
        
        # Try to add red (should fail)
        red_tiles = [Tile(TileColor.RED)]
        red_overflow = self.player.add_to_pattern_line(2, red_tiles)
        self.assertEqual(len(red_overflow), 1)  # All returned as overflow
        
        # Try to add yellow (should fail)
        yellow_tiles = [Tile(TileColor.YELLOW)]
        yellow_overflow = self.player.add_to_pattern_line(2, yellow_tiles)
        self.assertEqual(len(yellow_overflow), 1)  # All returned as overflow
        
        # Try to add blue (should succeed)
        blue_tiles = [Tile(TileColor.BLUE)]
        blue_overflow = self.player.add_to_pattern_line(2, blue_tiles)
        self.assertEqual(len(blue_overflow), 0)  # No overflow
        self.assertEqual(len(self.player.pattern_lines[2].tiles), 1)
        self.assertEqual(self.player.pattern_lines[2].tiles[0].color, TileColor.BLUE)
    
    def test_add_to_pattern_line_existing_pattern_same_color(self):
        """Test adding to pattern line that already has same color tiles."""
        # Add blue tile to pattern line first
        tiles1 = [Tile(TileColor.BLUE)]
        self.player.add_to_pattern_line(1, tiles1)
        
        # Add more blue tiles (should work)
        tiles2 = [Tile(TileColor.BLUE)]
        overflow = self.player.add_to_pattern_line(1, tiles2)
        self.assertEqual(len(overflow), 0)  # No overflow
        self.assertEqual(len(self.player.pattern_lines[1].tiles), 2)
    
    def test_add_to_pattern_line_existing_pattern_different_color(self):
        """Test adding different color to pattern line with existing tiles."""
        # Add blue tile to pattern line first
        blue_tiles = [Tile(TileColor.BLUE)]
        self.player.add_to_pattern_line(1, blue_tiles)
        
        # Try to add red tiles (should fail due to color consistency)
        red_tiles = [Tile(TileColor.RED)]
        overflow = self.player.add_to_pattern_line(1, red_tiles)
        self.assertEqual(len(overflow), 1)  # All returned as overflow
        self.assertEqual(len(self.player.pattern_lines[1].tiles), 1)  # Should still be 1
        self.assertEqual(self.player.pattern_lines[1].tiles[0].color, TileColor.BLUE)
    
    def test_add_to_pattern_line_overflow_to_floor(self):
        """Test that overflow tiles are returned when pattern line is full."""
        # Fill pattern line 0 (capacity 1) and add more
        tiles = [Tile(TileColor.BLUE), Tile(TileColor.BLUE), Tile(TileColor.BLUE)]
        overflow = self.player.add_to_pattern_line(0, tiles)
        
        self.assertEqual(len(self.player.pattern_lines[0].tiles), 1)  # Pattern line full
        self.assertEqual(len(overflow), 2)  # 2 overflow tiles returned
    
    def test_add_to_pattern_line_wall_validation_with_overflow(self):
        """Test wall validation still works when tiles would overflow."""
        # Place blue in wall row 0
        self.player.wall.place_tile(0, TileColor.BLUE)
        
        # Try to add blue tiles that would overflow
        tiles = [Tile(TileColor.BLUE), Tile(TileColor.BLUE), Tile(TileColor.BLUE)]
        overflow = self.player.add_to_pattern_line(0, tiles)
        
        self.assertEqual(len(overflow), 3)  # All tiles returned as overflow
        self.assertEqual(len(self.player.pattern_lines[0].tiles), 0)
        self.assertEqual(len(self.player.floor_line), 0)  # No tiles should be added anywhere
    
    def test_wall_can_place_tile(self):
        """Test the wall tile placement validation method."""
        # Initially can place any color in any row
        self.assertTrue(self.player.wall.can_place_tile(0, TileColor.BLUE))
        
        # Place a blue tile
        self.player.wall.place_tile(0, TileColor.BLUE)
        
        # Now blue cannot be placed in row 0
        self.assertFalse(self.player.wall.can_place_tile(0, TileColor.BLUE))
        # But red can still be placed
        self.assertTrue(self.player.wall.can_place_tile(0, TileColor.RED))
        # And blue can be placed in other rows
        self.assertTrue(self.player.wall.can_place_tile(1, TileColor.BLUE))


if __name__ == '__main__':
    unittest.main()
