# 人脸匹配阈值
FACE_MATCHING_THRESHOLD = 0.8
REGISTER_FACE_MATCHING_THRESHOLD = 0.7

# 注册状态
REGISTER_FAIL = 0
REGISTER_SUCCESS = 1
REGISTER_DUPLICATE = 2

# 活体检测模型图像尺寸
class LivenessModelParam:
    scale = 2.7
    out_width = 80
    out_height = 80

# 人脸注册相关参数
class RegistionParam:
    # 需要收集的有效帧数量
    required_frames = 5
    # 人脸检测置信度阈值
    confidence_threshold = 0.6
    # 有效帧之间的最小时间间隔（second)
    frame_interval = 0.5
    # 检测的最长持续时间
    detection_time_limit = 10
