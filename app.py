import os
import sys

# Tambahkan path agar modul 'src' bisa diakses jika belum
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app import app

if __name__ == "__main__":
    app.launch()
