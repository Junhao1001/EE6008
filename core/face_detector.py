import cv2
import insightface
from insightface.app import FaceAnalysis
import numpy as np

# 初始化人脸分析应用
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=-1)  # 使用GPU，如果使用CPU则设置为ctx_id=-1

# 初始化摄像头
cap = cv2.VideoCapture(0)  # 0表示默认摄像头

# 设置摄像头参数（可选）
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("按 'q' 键退出程序")

# 人脸数据库（简单示例）
face_database = {}
# 假设我们已经有一些已知人脸
# face_database = {
#     "person1": np.array([...]),  # 512维特征向量
#     "person2": np.array([...]),
# }

# 相似度阈值
threshold = 0.6

while True:
    # 读取一帧
    ret, frame = cap.read()
    if not ret:
        print("无法获取视频帧")
        break

    # 水平翻转图像（镜像效果）
    frame = cv2.flip(frame, 1)

    # 进行人脸检测和分析
    faces = app.get(frame)

    # 在图像上绘制结果
    for face in faces:
        # 获取人脸边界框
        bbox = face.bbox.astype(int)

        # 绘制边界框
        color = (0, 255, 0)  # 绿色框
        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

        # 绘制关键点
        landmarks = face.kps.astype(int)
        for landmark in landmarks:
            cv2.circle(frame, tuple(landmark), 2, (0, 0, 255), -1)  # 红色点

        # 获取特征向量
        embedding = face.normed_embedding

        # 如果有数据库，可以进行人脸识别
        if face_database:
            # 与数据库中的人脸进行比较
            max_similarity = 0
            identity = "Unknown"

            for name, db_embedding in face_database.items():
                similarity = np.dot(embedding, db_embedding)
                if similarity > max_similarity:
                    max_similarity = similarity
                    identity = name if similarity > threshold else "Unknown"

            # 显示识别结果
            label = f"{identity} ({max_similarity:.2f})"
            cv2.putText(frame, label, (bbox[0], bbox[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        else:
            # 只显示检测结果
            cv2.putText(frame, "Face Detected", (bbox[0], bbox[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # 显示帧率
    cv2.putText(frame, f"Faces: {len(faces)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # 显示图像
    cv2.imshow('Real-time Face Detection', frame)

    # 按'q'退出
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 释放资源
cap.release()
cv2.destroyAllWindows()