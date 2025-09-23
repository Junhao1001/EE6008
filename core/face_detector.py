import cv2
from insightface.app import FaceAnalysis
from core.face_database import FaceDatabase
import numpy as np

class FaceDetector:
    def __init__(self):
        # 初始化人脸分析应用
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1)  # 使用GPU，如果使用CPU则设置为ctx_id=-1

        # 存储人脸特征向量的字典
        self.face_database = FaceDatabase()

    def run(self):
        # 初始化摄像头
        cap = cv2.VideoCapture(0)  # 0表示默认摄像头

        # 设置摄像头参数（可选）
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("按 'q' 键退出程序")

        # 相似度阈值
        threshold = 0.7

        while True:
            # 读取一帧
            ret, frame = cap.read()
            if not ret:
                print("无法获取视频帧")
                break

            # 水平翻转图像（镜像效果）
            frame = cv2.flip(frame, 1)

            # 进行人脸检测和分析
            faces = self.app.get(frame)

            if len(faces) == 0:
                # 显示提示
                cv2.putText(frame, "No face detected. Please adjust your position", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                # 显示图像
                cv2.imshow('Real-time Face Detection', frame)
            else:
                # 获取最大的人脸（按面积计算）
                face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

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

                # 获取比较结果
                max_similarity, identity = self.face_database.compare_faces(embedding)

                #显示识别结果
                label = f"{identity} ({max_similarity:.2f})"
                cv2.putText(frame, label, (bbox[0], bbox[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # 显示检测人脸数量
                cv2.putText(frame, f"Faces: {len(faces)}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                # 显示图像
                cv2.imshow('Real-time Face Detection', frame)

                if max_similarity > 0:
                    print("检测到人脸，用户为:", identity)
                    cv2.waitKey(3000)
                    break

            # 按'q'退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # 释放资源
        cap.release()
        cv2.destroyAllWindows()