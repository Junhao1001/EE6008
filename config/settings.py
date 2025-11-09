# Face matching threshold
FACE_MATCHING_THRESHOLD = 0.5
REGISTER_FACE_MATCHING_THRESHOLD = 0.5

# Registration status
REGISTER_FAIL = 0
REGISTER_SUCCESS = 1
REGISTER_DUPLICATE = 2

# Liveness detection model image size
class LivenessModelParam:
    scale = 2.7
    out_width = 80
    out_height = 80

# Face registration related parameters
class RegistionParam:
    # Number of valid frames to collect
    required_frames = 5
    # Face detection confidence threshold
    confidence_threshold = 0.6
    # Minimum time interval between valid frames (seconds)
    frame_interval = 0.5
    # Maximum duration of detection (seconds)
    detection_time_limit = 10