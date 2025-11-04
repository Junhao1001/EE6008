from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 活体检测模型目录
LIVENESS_MODEL_PATH = ROOT_DIR / "model" / "anti_spoof_model" / "2.7_80x80_MiniFASNetV2.pth"

# users data path
USER_DATA_FILE = ROOT_DIR / "data" / "users_data.json"

# 数据相关路径
FACE_SAMPLE_DIR = ROOT_DIR / "data" / "face_samples"
FACE_DATA_FILE = ROOT_DIR / "data" / "face_data.json"

# 配置相关路径
CONFIG_DIR = ROOT_DIR / "config"

# 源代码路径
SRC_DIR = ROOT_DIR / "src"

# 测试路径
TESTS_DIR = ROOT_DIR / "tests"

# 示例图片
SAMPLE_IMAGES_DIR = ROOT_DIR / "data" / "face_samples" / "image_F1.jpg"

# 指纹样本库
FINGERPRINT_DIR = ROOT_DIR / "data" / "fingerprints"
FINGERPRINT_DIR.mkdir(parents=True, exist_ok=True)
