import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from utils.phone_utils import validate_numbers
    print("Success: Imported validate_numbers")
except ImportError as e:
    print(f"Error: {e}")
