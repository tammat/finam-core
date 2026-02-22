import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Удаляем конфликтующие пути
if "/Users/alex" in sys.path:
    sys.path.remove("/Users/alex")

# Гарантируем что проект первый
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)