import unittest
import json
import os
import tempfile
from unittest.mock import patch
from azul.ui import AzulUI
from azul.game import AzulGame
from azul.models import TileColor, Tile


class TestSaveLoadFunctionality(unittest.TestCase):
    """Test save and load game functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ui = AzulUI()
        self.ui.game = AzulGame(["Player 1", "Player 2"])
        self.ui.game.setup_round()
        
        # Set up some game state
        self.ui.player_configs = [
            {"type": "Human", "ai_type": "Random"},
            {"type": "AI", "ai_type": "Greedy"}
        ]
        
        # Make some moves to create interesting state
        player = self.ui.game.players[0]
        player.score = 15
        player.pattern_lines[0].tiles = [Tile(TileColor.BLUE)]
        player.floor_line = [Tile(TileColor.RED), Tile(TileColor.FIRST_PLAYER)]
        player.wall.place_tile(0, TileColor.BLUE)
        
        # Add some tiles to factories and center
        self.ui.game.factories[0].tiles = [Tile(TileColor.RED), Tile(TileColor.BLUE)]
        self.ui.game.center.tiles = [Tile(TileColor.YELLOW)]
        self.ui.game.center.first_player_taken = False
        
        # Modify bag and discard pile
        self.ui.game.bag = [Tile(TileColor.BLACK), Tile(TileColor.CYAN)]
        self.ui.game.discard_pile = [Tile(TileColor.CYAN)]
        
        # Set current player
        self.ui.game.current_player_idx = 1
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists("azul_savegame.json"):
            os.remove("azul_savegame.json")
    
    def test_save_game_creates_file(self):
        """Test that save_game creates a save file."""
        result = self.ui.save_game()
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists("azul_savegame.json"))
    
    def test_save_game_no_game_returns_false(self):
        """Test that save_game returns False when no game exists."""
        self.ui.game = None
        result = self.ui.save_game()
        
        self.assertFalse(result)
        self.assertFalse(os.path.exists("azul_savegame.json"))
    
    def test_save_game_content_structure(self):
        """Test that saved game has correct structure."""
        self.ui.save_game()
        
        with open("azul_savegame.json", 'r') as f:
            data = json.load(f)
        
        # Check required keys
        required_keys = ['players', 'factories', 'center', 'bag', 'discard_pile', 
                        'current_player_idx', 'game_ended', 'player_configs']
        for key in required_keys:
            self.assertIn(key, data)
        
        # Check player data structure
        self.assertEqual(len(data['players']), 2)
        player_data = data['players'][0]
        player_required_keys = ['name', 'score', 'pattern_lines', 'floor_line', 'wall_grid']
        for key in player_required_keys:
            self.assertIn(key, player_data)
        
        # Check specific values
        self.assertEqual(data['current_player_idx'], 1)
        self.assertEqual(data['players'][0]['score'], 15)
        self.assertEqual(len(data['factories']), 5)  # Standard number of factories
    
    def test_load_game_no_file_returns_false(self):
        """Test that load_game returns False when no save file exists."""
        result = self.ui.load_game()
        self.assertFalse(result)
    
    def test_save_and_load_game_state(self):
        """Test complete save and load cycle preserves game state."""
        # Save the game
        save_result = self.ui.save_game()
        self.assertTrue(save_result)
        
        # Create new UI and load the game
        new_ui = AzulUI()
        load_result = new_ui.load_game()
        self.assertTrue(load_result)
        
        # Verify game state was restored correctly
        self.assertIsNotNone(new_ui.game)
        
        # Check player state
        loaded_player = new_ui.game.players[0]
        self.assertEqual(loaded_player.score, 15)
        self.assertEqual(len(loaded_player.pattern_lines[0].tiles), 1)
        self.assertEqual(loaded_player.pattern_lines[0].tiles[0].color, TileColor.BLUE)
        self.assertEqual(len(loaded_player.floor_line), 2)
        self.assertEqual(loaded_player.floor_line[0].color, TileColor.RED)
        self.assertEqual(loaded_player.floor_line[1].color, TileColor.FIRST_PLAYER)
        
        # Check wall state - find where blue tile was placed
        blue_found = False
        for col in range(5):
            if loaded_player.wall.grid[0][col] is not None:
                if loaded_player.wall.grid[0][col].color == TileColor.BLUE:
                    blue_found = True
                    break
        self.assertTrue(blue_found, "Blue tile should be found in wall row 0")
        
        # Check factory state
        self.assertEqual(len(new_ui.game.factories[0].tiles), 2)
        factory_colors = [tile.color for tile in new_ui.game.factories[0].tiles]
        self.assertIn(TileColor.RED, factory_colors)
        self.assertIn(TileColor.BLUE, factory_colors)
        
        # Check center state
        self.assertEqual(len(new_ui.game.center.tiles), 1)
        self.assertEqual(new_ui.game.center.tiles[0].color, TileColor.YELLOW)
        self.assertFalse(new_ui.game.center.first_player_taken)
        
        # Check bag and discard pile
        self.assertEqual(len(new_ui.game.bag), 2)
        self.assertEqual(len(new_ui.game.discard_pile), 1)
        self.assertEqual(new_ui.game.discard_pile[0].color, TileColor.CYAN)
        
        # Check current player
        self.assertEqual(new_ui.game.current_player_idx, 1)
        
        # Check player configs
        self.assertEqual(new_ui.player_configs[0]["type"], "Human")
        self.assertEqual(new_ui.player_configs[1]["type"], "AI")
        self.assertEqual(new_ui.player_configs[1]["ai_type"], "Greedy")
    
    def test_save_game_with_ai_players(self):
        """Test saving and loading game with AI players configured."""
        # Set up AI players
        from azul.ai import GreedyAI, StrategicAI
        self.ui.ai_players = {1: GreedyAI("AI Player 2")}
        
        # Save and load
        self.ui.save_game()
        new_ui = AzulUI()
        new_ui.load_game()
        
        # Verify AI player was restored
        self.assertIn(1, new_ui.ai_players)
        self.assertIsInstance(new_ui.ai_players[1], GreedyAI)
    
    def test_load_game_invalid_json_returns_false(self):
        """Test that load_game handles invalid JSON gracefully."""
        # Create invalid JSON file
        with open("azul_savegame.json", 'w') as f:
            f.write("invalid json content")
        
        result = self.ui.load_game()
        self.assertFalse(result)
    
    def test_save_game_handles_io_error(self):
        """Test that save_game handles IO errors gracefully."""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            result = self.ui.save_game()
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
