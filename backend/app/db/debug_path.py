import os
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print('BACKEND_DIR:', BACKEND_DIR)
DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "data", "floatchat.db")
print('DB_PATH:', DEFAULT_DB_PATH)
print('Dir exists:', os.path.exists(os.path.dirname(DEFAULT_DB_PATH)))