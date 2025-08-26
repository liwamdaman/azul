"""Tests for end-of-game scoring bonuses."""

import pytest
from azul.game import AzulGame
from azul.models import TileColor, Tile


class TestEndGameScoring:
    """Test end-of-game bonus scoring."""
    
    def test_horizontal_row_bonus(self):
        """Test 2 points per completed horizontal row."""
        game = AzulGame(["Alice"])
        player = game.players[0]
        
        # Complete first row (5 tiles)
        for col in range(5):
            player.wall.grid[0][col] = Tile(TileColor.BLUE)
        
        # Complete third row (5 tiles)
        for col in range(5):
            player.wall.grid[2][col] = Tile(TileColor.RED)
        
        bonus = game._calculate_end_game_bonuses(player)
        assert bonus == 4, f"Expected 4 points (2 rows × 2 pts), got {bonus}"
    
    def test_vertical_column_bonus(self):
        """Test 7 points per completed vertical column."""
        game = AzulGame(["Alice"])
        player = game.players[0]
        
        # Complete first column (5 tiles)
        for row in range(5):
            player.wall.grid[row][0] = Tile(TileColor.BLUE)
        
        # Complete last column (5 tiles)
        for row in range(5):
            player.wall.grid[row][4] = Tile(TileColor.RED)
        
        bonus = game._calculate_end_game_bonuses(player)
        assert bonus == 14, f"Expected 14 points (2 columns × 7 pts), got {bonus}"
    
    def test_color_set_bonus(self):
        """Test 10 points per completed color set."""
        game = AzulGame(["Alice"])
        player = game.players[0]
        
        # Complete BLUE color set (all 5 BLUE tiles placed)
        color_list = [c for c in TileColor if c != TileColor.FIRST_PLAYER]
        blue_idx = color_list.index(TileColor.BLUE)
        
        for row in range(5):
            col = (row + blue_idx) % 5
            player.wall.grid[row][col] = Tile(TileColor.BLUE)
        
        # Complete RED color set
        red_idx = color_list.index(TileColor.RED)
        for row in range(5):
            col = (row + red_idx) % 5
            player.wall.grid[row][col] = Tile(TileColor.RED)
        
        bonus = game._calculate_end_game_bonuses(player)
        assert bonus == 20, f"Expected 20 points (2 colors × 10 pts), got {bonus}"
    
    def test_combined_bonuses(self):
        """Test multiple bonus types combined."""
        game = AzulGame(["Alice"])
        player = game.players[0]
        
        # Fill entire wall (5×5 grid)
        colors = [TileColor.BLUE, TileColor.YELLOW, TileColor.RED, TileColor.BLACK, TileColor.CYAN]
        for row in range(5):
            for col in range(5):
                color_idx = (col - row) % 5
                player.wall.grid[row][col] = Tile(colors[color_idx])
        
        bonus = game._calculate_end_game_bonuses(player)
        # 5 horizontal rows × 2 = 10 points
        # 5 vertical columns × 7 = 35 points  
        # 5 color sets × 10 = 50 points
        # Total = 95 points
        assert bonus == 95, f"Expected 95 points (full wall), got {bonus}"
    
    def test_partial_completions_no_bonus(self):
        """Test that partial completions don't give bonuses."""
        game = AzulGame(["Alice"])
        player = game.players[0]
        
        # Incomplete row (4 out of 5 tiles)
        for col in range(4):
            player.wall.grid[0][col] = Tile(TileColor.BLUE)
        
        # Incomplete column (3 out of 5 tiles)
        for row in range(3):
            player.wall.grid[row][1] = Tile(TileColor.RED)
        
        # Incomplete color set (3 out of 5 YELLOW tiles)
        color_list = [c for c in TileColor if c != TileColor.FIRST_PLAYER]
        yellow_idx = color_list.index(TileColor.YELLOW)
        for row in range(3):
            col = (row + yellow_idx) % 5
            player.wall.grid[row][col] = Tile(TileColor.YELLOW)
        
        bonus = game._calculate_end_game_bonuses(player)
        assert bonus == 0, f"Expected 0 points (no complete sets), got {bonus}"
    
    def test_winner_determination_with_bonuses(self):
        """Test that winner is determined correctly after applying bonuses."""
        game = AzulGame(["Alice", "Bob"])
        alice = game.players[0]
        bob = game.players[1]
        
        # Alice has lower base score but gets bonuses
        alice.score = 50
        bob.score = 60
        
        # Give Alice a completed row (2 bonus points)
        for col in range(5):
            alice.wall.grid[0][col] = Tile(TileColor.BLUE)
        
        # Give Alice a completed column (7 bonus points)
        for row in range(5):
            alice.wall.grid[row][1] = Tile(TileColor.RED)
        
        # Alice total: 50 + 2 + 7 = 59 (still loses)
        # Bob total: 60 (wins)
        
        game.game_over = True
        winner = game.get_winner()
        assert winner == bob, "Bob should win with higher total score"
        
        # Now give Alice a color set bonus (10 points)
        color_list = [c for c in TileColor if c != TileColor.FIRST_PLAYER]
        yellow_idx = color_list.index(TileColor.YELLOW)
        for row in range(5):
            col = (row + yellow_idx) % 5
            alice.wall.grid[row][col] = Tile(TileColor.YELLOW)
        
        # Reset scores for fresh calculation
        alice.score = 50
        bob.score = 60
        
        # Manually apply bonuses since UI now handles this during animations
        alice_bonuses = game._calculate_end_game_bonuses(alice)
        bob_bonuses = game._calculate_end_game_bonuses(bob)
        alice.score += alice_bonuses
        bob.score += bob_bonuses
        
        winner = game.get_winner()
        # Alice total: 50 + 2 + 7 + 10 = 69 (wins)
        assert winner == alice, "Alice should win with bonuses"
    
    def test_tie_breaking_by_completed_rows(self):
        """Test tie-breaking by number of completed horizontal rows."""
        game = AzulGame(["Alice", "Bob"])
        alice = game.players[0]
        bob = game.players[1]
        
        # Both players have same base score
        alice.score = 50
        bob.score = 50
        
        # Alice has 2 completed rows
        for col in range(5):
            alice.wall.grid[0][col] = Tile(TileColor.BLUE)
            alice.wall.grid[1][col] = Tile(TileColor.RED)
        
        # Bob has 1 completed row
        for col in range(5):
            bob.wall.grid[0][col] = Tile(TileColor.BLUE)
        
        game.game_over = True
        winner = game.get_winner()
        
        # Both get same bonus (2×2 = 4 vs 1×2 = 2), but Alice has more completed rows
        assert winner == alice, "Alice should win tie-breaker with more completed rows"
