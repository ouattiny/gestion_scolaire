import os
import sys

# Ajoute le chemin courant au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
