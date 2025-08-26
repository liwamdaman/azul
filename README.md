# Azul Board Game Implementation

A Python implementation of the Azul board game with a beautiful graphical interface and AI player capabilities.

## Features
- Complete game logic for Azul
- Beautiful pygame-based graphical interface
- AI players with multiple difficulty levels (Random, Greedy, Strategic)
- Interactive tile selection and placement
- Real-time game state visualization
- Extensible architecture for more advanced AI implementations

## Installation
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Game

```bash
python -m azul
```

The game features a graphical interface with:
- **Interactive tile selection**: Click on factories or the center to select tiles
- **Visual pattern lines**: Click on pattern lines to place selected tiles
- **AI opponents**: Currently plays against a Greedy AI opponent
- **Real-time updates**: Watch AI moves and game state changes
- **Beautiful visualization**: Color-coded tiles and clear game board layout

### Controls
- Click on factories (F1-F5) or center to select tile source
- Click on pattern lines (1-5) or floor to place tiles
- Use Menu button to return to main menu
- Use Restart button to start a new game
- Press ESC to return to menu during gameplay

## Running Tests

The project includes a comprehensive unit test suite covering all game logic, scoring mechanics, and AI functionality.

### Quick Test Run
```bash
# Using the test runner script (recommended)
python run_tests.py

# Or using pytest directly
source venv/bin/activate
python -m pytest tests/ -v
```

### Running Specific Tests
```bash
# Test specific components
python run_tests.py models     # Test data models
python run_tests.py scoring    # Test scoring logic
python run_tests.py game       # Test game mechanics
python run_tests.py ai         # Test AI functionality

# Run tests matching a pattern
python -m pytest tests/ -k "pattern_line" -v
```

### Test Coverage
The test suite includes **48 comprehensive tests** covering:
- ✅ **Game Logic**: Round setup, tile taking, overflow handling
- ✅ **Scoring System**: Floor penalties, wall adjacency, pattern line completion
- ✅ **Data Models**: Tile creation, pattern lines, wall placement
- ✅ **Rule Enforcement**: Color consistency, capacity limits
- ✅ **AI Integration**: Move validation and execution
- ✅ **Factory & Center**: Tile management, first player token

### Test-Driven Development
Always run tests before and after making changes to game logic:
```bash
# Before making changes
python run_tests.py

# Make your changes...

# After making changes
python run_tests.py
```
