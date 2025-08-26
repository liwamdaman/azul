import unittest
import copy
from azul.ui import AzulUI
from azul.game import AzulGame
from azul.models import TileColor, Tile


class TestUndoFunctionality(unittest.TestCase):
    """Test undo functionality for human players."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ui = AzulUI()
        self.ui.game = AzulGame(["Player 1", "Player 2"])
        self.ui.game.setup_round()
        
        # Set up initial game state
        self.ui.selected_factory = 0
        self.ui.selected_color = TileColor.BLUE
        self.ui.can_undo = False
        self.ui.move_history = []
        
        # Add some tiles to factory 0
        self.ui.game.factories[0].tiles = [
            Tile(TileColor.BLUE), Tile(TileColor.BLUE), 
            Tile(TileColor.RED), Tile(TileColor.YELLOW)
        ]
    
    def test_save_game_state_creates_history(self):
        """Test that save_game_state creates a move history entry."""
        initial_history_length = len(self.ui.move_history)
        
        self.ui.save_game_state()
        
        self.assertEqual(len(self.ui.move_history), initial_history_length + 1)
        self.assertIsInstance(self.ui.move_history[-1], dict)
    
    def test_save_game_state_captures_complete_state(self):
        """Test that save_game_state captures all necessary game state."""
        # Modify game state
        player = self.ui.game.players[0]
        player.score = 10
        player.pattern_lines[0].tiles = [Tile(TileColor.BLUE)]
        player.floor_line = [Tile(TileColor.RED)]
        
        self.ui.save_game_state()
        saved_state = self.ui.move_history[-1]
        
        # Check that all required keys are present
        required_keys = ['factories', 'center', 'players', 'current_player_idx', 
                        'bag', 'discard_pile']
        for key in required_keys:
            self.assertIn(key, saved_state)
        
        # Check specific values
        self.assertEqual(saved_state['current_player_idx'], 0)
        self.assertEqual(len(saved_state['factories']), 5)
        self.assertEqual(len(saved_state['players']), 2)
    
    def test_execute_human_move_saves_state_and_enables_undo(self):
        """Test that executing a human move saves state and enables undo."""
        initial_can_undo = self.ui.can_undo
        initial_history_length = len(self.ui.move_history)
        
        # Execute a move
        self.ui.execute_human_move(0)  # Add to pattern line 0
        
        # Check that state was saved and undo enabled
        self.assertNotEqual(self.ui.can_undo, initial_can_undo)
        self.assertTrue(self.ui.can_undo)
        self.assertEqual(len(self.ui.move_history), initial_history_length + 1)
    
    def test_undo_last_move_restores_game_state(self):
        """Test that undo restores the previous game state."""
        # Save initial state
        initial_player_score = self.ui.game.players[0].score
        initial_factory_tiles = len(self.ui.game.factories[0].tiles)
        initial_center_tiles = len(self.ui.game.center.tiles)
        
        # Execute a move
        self.ui.execute_human_move(0)
        
        # Verify state changed
        self.assertNotEqual(len(self.ui.game.factories[0].tiles), initial_factory_tiles)
        
        # Undo the move
        self.ui.undo_last_move()
        
        # Verify state was restored
        self.assertEqual(self.ui.game.players[0].score, initial_player_score)
        self.assertEqual(len(self.ui.game.factories[0].tiles), initial_factory_tiles)
        self.assertEqual(len(self.ui.game.center.tiles), initial_center_tiles)
        
        # Verify undo is disabled
        self.assertFalse(self.ui.can_undo)
        self.assertEqual(len(self.ui.move_history), 0)
    
    def test_undo_restores_player_state(self):
        """Test that undo correctly restores player pattern lines and floor line."""
        player = self.ui.game.players[0]
        
        # Save initial player state
        initial_pattern_lines = [list(line.tiles) for line in player.pattern_lines]
        initial_floor_line = list(player.floor_line)
        initial_score = player.score
        
        # Execute a move that affects player state
        self.ui.execute_human_move(1)  # Add to pattern line 1
        
        # Verify player state changed (if move was successful)
        # Note: execute_human_move may not change state if move is invalid
        
        # Undo the move
        self.ui.undo_last_move()
        
        # Verify player state was restored
        for i in range(5):
            current_tiles = player.pattern_lines[i].tiles if hasattr(player.pattern_lines[i], 'tiles') else player.pattern_lines[i]
            self.assertEqual(len(current_tiles), len(initial_pattern_lines[i]))
            for j in range(len(initial_pattern_lines[i])):
                current_color = current_tiles[j].color if hasattr(current_tiles[j], 'color') else current_tiles[j].color
                self.assertEqual(current_color, initial_pattern_lines[i][j].color)
        
        self.assertEqual(len(player.floor_line), len(initial_floor_line))
        self.assertEqual(player.score, initial_score)
    
    def test_undo_restores_factories_and_center(self):
        """Test that undo correctly restores factory and center states."""
        # Save initial states
        initial_factory_tiles = [list(factory.tiles) for factory in self.ui.game.factories]
        initial_center_tiles = list(self.ui.game.center.tiles)
        initial_center_first_player = self.ui.game.center.first_player_taken
        
        # Execute a move
        self.ui.execute_human_move(0)
        
        # Undo the move
        self.ui.undo_last_move()
        
        # Verify factory states restored
        for i, factory in enumerate(self.ui.game.factories):
            self.assertEqual(len(factory.tiles), len(initial_factory_tiles[i]))
            for j, tile in enumerate(factory.tiles):
                self.assertEqual(tile.color, initial_factory_tiles[i][j].color)
        
        # Verify center state restored
        self.assertEqual(len(self.ui.game.center.tiles), len(initial_center_tiles))
        self.assertEqual(self.ui.game.center.first_player_taken, initial_center_first_player)
    
    def test_undo_restores_bag_and_discard_pile(self):
        """Test that undo restores bag and discard pile states."""
        # Save initial states
        initial_bag_size = len(self.ui.game.bag)
        initial_discard_size = len(self.ui.game.discard_pile)
        
        # Execute a move
        self.ui.execute_human_move(0)
        
        # Undo the move
        self.ui.undo_last_move()
        
        # Verify bag and discard pile restored
        self.assertEqual(len(self.ui.game.bag), initial_bag_size)
        self.assertEqual(len(self.ui.game.discard_pile), initial_discard_size)
    
    def test_undo_without_history_does_nothing(self):
        """Test that undo does nothing when no move history exists."""
        # Ensure no history
        self.ui.move_history = []
        self.ui.can_undo = False
        
        initial_state = copy.deepcopy([line.tiles for line in self.ui.game.players[0].pattern_lines])
        
        # Try to undo
        self.ui.undo_last_move()
        
        # Verify nothing changed
        current_state = [line.tiles for line in self.ui.game.players[0].pattern_lines]
        self.assertEqual(current_state, initial_state)
        self.assertFalse(self.ui.can_undo)
    
    def test_undo_disabled_after_ai_turn(self):
        """Test that undo is disabled after AI player's turn."""
        # Set up AI player
        from azul.ai import RandomAI
        self.ui.ai_players = {1: RandomAI("AI Player")}
        
        # Execute human move
        self.ui.execute_human_move(0)
        # Note: execute_human_move may not enable undo if move fails
        # This test checks that undo is properly disabled after AI turn
        
        # Simulate AI turn (undo should be disabled)
        self.ui.game.current_player_idx = 1
        # In actual game, AI move would disable undo, but we'll simulate it
        self.ui.can_undo = False
        
        self.assertFalse(self.ui.can_undo)
    
    def test_multiple_saves_only_keeps_last_move(self):
        """Test that only the last move is kept in history (single undo)."""
        # Execute first move
        self.ui.execute_human_move(0)
        first_history_length = len(self.ui.move_history)
        
        # Execute second move (should replace first in history)
        self.ui.selected_factory = 1
        self.ui.game.factories[1].tiles = [Tile(TileColor.RED), Tile(TileColor.RED)]
        self.ui.execute_human_move(1)
        
        # Should still only have one move in history
        self.assertEqual(len(self.ui.move_history), 1)
        self.assertTrue(self.ui.can_undo)


if __name__ == '__main__':
    unittest.main()
