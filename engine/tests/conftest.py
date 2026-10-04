"""Las pruebas del motor corren sin Blender: python -m pytest engine/tests"""
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
