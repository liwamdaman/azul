import pytest
from azul.ai import GreedyAI, StrategicAI, RandomAI, Move
from azul.game import AzulGame
from azul.models import TileColor

def test_ai_player_creation():
    """Test AI player creation."""
    ai = GreedyAI("TestAI")
    assert ai.name == "TestAI"
    assert ai.difficulty == "medium"

def test_get_valid_moves():
    """Test that AI can identify valid moves."""
    game = AzulGame(["Human", "AI"])
    game.setup_round()
    
    ai = GreedyAI("TestAI")
    moves = ai.get_valid_moves(game)
    
    # Should have moves available after setup
    assert len(moves) > 0
    
    # All moves should be valid Move objects
    for move in moves:
        assert isinstance(move, Move)
        assert move.color != TileColor.FIRST_PLAYER

def test_random_ai_chooses_move():
    """Test that RandomAI can choose a move."""
    game = AzulGame(["Human", "AI"])
    game.setup_round()
    
    ai = RandomAI("RandomAI")
    move = ai.choose_move(game, 1)
    
    assert move is not None
    assert isinstance(move, Move)

def test_greedy_ai_chooses_move():
    """Test that GreedyAI can choose a move."""
    game = AzulGame(["Human", "AI"])
    game.setup_round()
    
    ai = GreedyAI("GreedyAI")
    move = ai.choose_move(game, 1)
    
    assert move is not None
    assert isinstance(move, Move)

def test_strategic_ai_chooses_move():
    """Test that StrategicAI can choose a move."""
    game = AzulGame(["Human", "AI"])
    game.setup_round()
    
    ai = StrategicAI("StrategicAI")
    move = ai.choose_move(game, 1)
    
    assert move is not None
    assert isinstance(move, Move)
