from pathlib import Path

# Project root directory
ROOT_DIR = Path(__file__).parent.parent

# Liveness detection model path
LIVENESS_MODEL_PATH = ROOT_DIR / "model" / "anti_spoof_model" / "2.7_80x80_MiniFASNetV2.pth"

# users data path
USER_DATA_FILE = ROOT_DIR / "data" / "users_data.json"

# Data-related paths
FACE_SAMPLE_DIR = ROOT_DIR / "data" / "face_samples"
FACE_DATA_FILE = ROOT_DIR / "data" / "face_data.json"

# Config-related paths
CONFIG_DIR = ROOT_DIR / "config"

# Source code directory
SRC_DIR = ROOT_DIR / "src"

# Tests directory
TESTS_DIR = ROOT_DIR / "tests"

# Sample image
SAMPLE_IMAGES_DIR = ROOT_DIR / "data" / "face_samples" / "image_F1.jpg"

# Fingerprint sample directory
FINGERPRINT_DIR = ROOT_DIR / "data" / "fingerprints"
FINGERPRINT_DIR.mkdir(parents=True, exist_ok=True)