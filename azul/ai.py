from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import random
from .models import TileColor, Player
from .game import AzulGame

@dataclass
class Move:
    """Represents a possible move in the game."""
    source_type: str  # "factory" or "center"
    source_index: int  # Factory index (0-4) or -1 for center
    color: TileColor
    pattern_line: int  # 0-4 for pattern lines, -1 for floor
    
    def __str__(self) -> str:
        source = f"Factory {self.source_index + 1}" if self.source_type == "factory" else "Center"
        line = f"Pattern Line {self.pattern_line + 1}" if self.pattern_line >= 0 else "Floor"
        return f"{source} -> {self.color.name} -> {line}"

class AIPlayer(ABC):
    """Abstract base class for AI players."""
    
    def __init__(self, name: str, difficulty: str = "medium"):
        self.name = name
        self.difficulty = difficulty
    
    @abstractmethod
    def choose_move(self, game: AzulGame, player_index: int) -> Optional[Move]:
        """Choose the best move for the current game state."""
        pass
    
    def get_valid_moves(self, game: AzulGame) -> List[Move]:
        """Get all valid moves from the current game state."""
        moves = []
        
        # Check factory moves
        for i, factory in enumerate(game.factories):
            if not factory.is_empty():
                available_colors = set(tile.color for tile in factory.tiles)
                for color in available_colors:
                    if color != TileColor.FIRST_PLAYER:
                        # Try each pattern line
                        for line_idx in range(5):
                            moves.append(Move("factory", i, color, line_idx))
                        # Also consider floor line
                        moves.append(Move("factory", i, color, -1))
        
        # Check center moves
        if not game.center.is_empty():
            available_colors = set(tile.color for tile in game.center.tiles)
            for color in available_colors:
                if color != TileColor.FIRST_PLAYER:
                    # Try each pattern line
                    for line_idx in range(5):
                        moves.append(Move("center", -1, color, line_idx))
                    # Also consider floor line
                    moves.append(Move("center", -1, color, -1))
        
        return moves

class GreedyAI(AIPlayer):
    """A greedy AI that makes locally optimal moves."""
    
    def choose_move(self, game: AzulGame, player_index: int) -> Optional[Move]:
        """Choose move based on greedy heuristics."""
        valid_moves = self.get_valid_moves(game)
        if not valid_moves:
            return None
        
        player = game.players[player_index]
        best_move = None
        best_score = float('-inf')
        
        for move in valid_moves:
            score = self._evaluate_move(game, player, move)
            if score > best_score:
                best_score = score
                best_move = move
        
        return best_move
    
    def _evaluate_move(self, game: AzulGame, player: Player, move: Move) -> float:
        """Evaluate the quality of a move."""
        score = 0.0
        
        # Get tiles that would be taken
        if move.source_type == "factory":
            factory = game.factories[move.source_index]
            taken_tiles = [t for t in factory.tiles if t.color == move.color]
            remaining_tiles = [t for t in factory.tiles if t.color != move.color]
        else:
            taken_tiles = [t for t in game.center.tiles if t.color == move.color]
            remaining_tiles = []
        
        num_tiles = len(taken_tiles)
        
        # Evaluate pattern line placement
        if move.pattern_line >= 0:
            pattern_line = player.pattern_lines[move.pattern_line]
            
            # Prefer completing lines
            spaces_needed = pattern_line.capacity - len(pattern_line.tiles)
            if num_tiles >= spaces_needed and spaces_needed > 0:
                score += 20.0  # High bonus for completing a line
            
            # Prefer lines that can use more tiles (less waste)
            usable_tiles = min(num_tiles, spaces_needed)
            score += usable_tiles * 2.0
            
            # Penalty for waste (tiles going to floor)
            waste = max(0, num_tiles - spaces_needed)
            score -= waste * 3.0
            
            # Check if we can place this color on the wall
            if not player.wall.can_place_tile(move.pattern_line, move.color):
                score -= 50.0  # Heavy penalty for invalid wall placement
        else:
            # Floor line placement - generally bad but sometimes necessary
            score -= num_tiles * 5.0
        
        # Bonus for taking first player token when beneficial
        if move.source_type == "center":
            first_player_in_center = any(t.color == TileColor.FIRST_PLAYER 
                                       for t in game.center.tiles)
            if first_player_in_center:
                # Being first player is generally good
                score += 3.0
        
        # Penalty for giving opponents good tiles
        if move.source_type == "factory" and remaining_tiles:
            # Tiles go to center, making them available to opponents
            score -= len(remaining_tiles) * 1.0
        
        return score

class StrategicAI(AIPlayer):
    """A more advanced AI that considers longer-term strategy."""
    
    def choose_move(self, game: AzulGame, player_index: int) -> Optional[Move]:
        """Choose move based on strategic considerations."""
        valid_moves = self.get_valid_moves(game)
        if not valid_moves:
            return None
        
        player = game.players[player_index]
        best_move = None
        best_score = float('-inf')
        
        for move in valid_moves:
            score = self._evaluate_strategic_move(game, player, move, player_index)
            if score > best_score:
                best_score = score
                best_move = move
        
        return best_move
    
    def _evaluate_strategic_move(self, game: AzulGame, player: Player, 
                               move: Move, player_index: int) -> float:
        """Evaluate move with strategic considerations."""
        # Start with greedy evaluation
        greedy_ai = GreedyAI("temp")
        base_score = greedy_ai._evaluate_move(game, player, move)
        
        # Add strategic considerations
        strategic_bonus = 0.0
        
        # Prefer moves that complete rows for end-game bonus
        if move.pattern_line >= 0:
            wall_row = player.wall.grid[move.pattern_line]
            filled_in_row = sum(1 for tile in wall_row if tile is not None)
            if filled_in_row >= 3:  # Close to completing row
                strategic_bonus += 5.0
        
        # Consider color completion bonuses
        color_counts = self._count_wall_colors(player)
        if move.pattern_line >= 0:
            current_count = color_counts.get(move.color, 0)
            if current_count >= 3:  # Close to completing color
                strategic_bonus += 3.0
        
        # Defensive play - avoid giving opponents easy completions
        defensive_penalty = self._evaluate_opponent_benefit(game, move, player_index)
        
        return base_score + strategic_bonus - defensive_penalty
    
    def _count_wall_colors(self, player: Player) -> Dict[TileColor, int]:
        """Count how many of each color are on the wall."""
        counts = {}
        for row in player.wall.grid:
            for tile in row:
                if tile is not None:
                    counts[tile.color] = counts.get(tile.color, 0) + 1
        return counts
    
    def _evaluate_opponent_benefit(self, game: AzulGame, move: Move, 
                                 player_index: int) -> float:
        """Evaluate how much this move benefits opponents."""
        penalty = 0.0
        
        if move.source_type == "factory":
            factory = game.factories[move.source_index]
            remaining_tiles = [t for t in factory.tiles if t.color != move.color]
            
            # Check if remaining tiles help opponents complete lines
            for i, opponent in enumerate(game.players):
                if i == player_index:
                    continue
                    
                for tile in remaining_tiles:
                    for line_idx, line in enumerate(opponent.pattern_lines):
                        if (len(line.tiles) > 0 and 
                            line.tiles[0].color == tile.color and
                            not line.is_full()):
                            spaces_left = line.capacity - len(line.tiles)
                            if spaces_left <= 2:  # Close to completion
                                penalty += 2.0
        
        return penalty

class RandomAI(AIPlayer):
    """A random AI for testing and baseline comparison."""
    
    def choose_move(self, game: AzulGame, player_index: int) -> Optional[Move]:
        """Choose a random valid move."""
        valid_moves = self.get_valid_moves(game)
        return random.choice(valid_moves) if valid_moves else None
