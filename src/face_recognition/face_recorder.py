import cv2
import time
import os
import numpy as np
from datetime import datetime

from insightface.app import FaceAnalysis
from src.face_recognition.anti_spoof_predict import AntiSpoofPredict
from src.face_recognition.face_database import FaceDatabase
from config.settings import RegistionParam, REGISTER_FACE_MATCHING_THRESHOLD

FACE_STATUS_VALID = 0
FACE_STATUS_INVALID = 1
FACE_STATUS_DUPLICATE = 2

class FaceRecorder:
    def __init__(self):
        # 初始化人脸分析应用
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1)  # 使用GPU，如果使用CPU则设置为ctx_id=-1

        self.liveness_model = AntiSpoofPredict()

        # 存储人脸特征向量的字典
        self.face_database = FaceDatabase()
        # 注册相关参数
        self.param = RegistionParam()

    def check_face_validity(self, frame, face, bbox):
        # 活体检测
        is_real = self.liveness_model.predict(frame, bbox)

        if is_real & (face.det_score > self.param.confidence_threshold):
            embedding = face.normed_embedding
            max_similarity, identity = self.face_database.compare_faces(embedding, REGISTER_FACE_MATCHING_THRESHOLD)
            if max_similarity == 0:
                return FACE_STATUS_VALID
            else:
                print("Duplicate Face with user:{}".format(identity))
                return FACE_STATUS_DUPLICATE
        else:
            return FACE_STATUS_INVALID

    def register_face(self, name, embedding, face_img):
        """注册新的人脸"""
        self.face_database.face_data[name] = embedding

        # 保存人脸图像
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        face_filename = os.path.join(self.face_database.save_dir, f"{name}_{timestamp}.jpg")
        cv2.imwrite(face_filename, face_img)

        # 保存数据到文件
        self.face_database.save_faces()

        print(f"成功注册: {name}")
        return True

    def run(self, name):
        """运行主程序"""
        # 记录初始时间
        start_time = time.time()
        # 上一个有效帧的时间
        last_collect_time = 0
        # 存储收集到的有效特征向量
        collected_embedding = []
        registration_completion = False

        # 初始化摄像头
        print("turn on the video")
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while True:
            elapsed_time = time.time() - start_time
            ret, frame = cap.read()
            if not ret:
                print("无法获取视频帧")
                break

            # 水平翻转图像（镜像效果）
            frame = cv2.flip(frame, 1)

            # 检测人脸（但不提取特征，只用于显示）
            faces = self.app.get(frame)

            if len(faces) == 0:
                # 提示未检测到人脸
                face_valid = FACE_STATUS_INVALID
            else:

                # 获取最大的人脸（按面积计算）用于注册
                face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                bbox = face.bbox.astype(int)
                face_img = frame[bbox[1]:bbox[3], bbox[0]:bbox[2]]

                face_valid = self.check_face_validity(frame, face, bbox)

                if face_valid == FACE_STATUS_VALID:
                    label = "Valid Face"
                    color = (0, 255, 0)
                elif face_valid == FACE_STATUS_DUPLICATE:
                    label = "Duplicate Face"
                    color = (0, 0, 255)
                else:
                    label = "Invalid Face"
                    color = (0, 0, 255)

                # 绘制边界框
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                # 显示标签
                cv2.putText(frame, label, (bbox[0], bbox[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # 判断当前注册状态
            if registration_completion:
                cv2.putText(frame, f"Face Detection Complete!", (200, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, f"Face Detection in Process...", (200, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                # 距离上一个有效帧需要一定间隔
                if face_valid == FACE_STATUS_VALID & (time.time() - last_collect_time > self.param.frame_interval):
                    # 提取特征向量
                    current_embedding = face.normed_embedding

                    # 更新有效帧时间戳
                    last_collect_time = time.time()
                    collected_embedding.append(current_embedding)
                    print("debug: reserve face embedding:", len(collected_embedding))
                    if len(collected_embedding) >= self.param.required_frames:
                        # 收集到足够的有效帧，则进行注册
                        avg_embedding = np.mean(collected_embedding, axis=0)
                        save_img = face_img
                        print("Register Successfully!")
                        registration_completion = True

            cv2.putText(frame, "Press 'q' to quit", (500, 450),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 显示图像
            cv2.imshow('Face Registration', frame)

            # 键盘操作
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("用户手动退出程序")
                break

            #退出条件判断
            if registration_completion:
                # 注册成功后显示2秒再退出
                if time.time() - last_collect_time > 3:
                    break
            elif elapsed_time > self.param.detection_time_limit:
                print("注册时间超过10s!")
                break

        if registration_completion:
            self.register_face(name, avg_embedding, save_img)
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        print("程序已退出")

        return registration_completion

