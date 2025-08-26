"""
Azul - A Python implementation of the Azul board game.
"""

def main():
    """Entry point for the Azul game."""
    from .ui import main as ui_main
    ui_main()

if __name__ == "__main__":
    main()
