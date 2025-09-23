import cv2
import time
import os
import numpy as np
from insightface.app import FaceAnalysis
from datetime import datetime
from core.face_database import FaceDatabase
from config.settings import REGISTER_SUCCESS, REGISTER_UNFINISHED, REGISTER_DUPLICATE

class FaceRecorder:
    def __init__(self):
        # 初始化人脸分析应用
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1)  # 使用GPU，如果使用CPU则设置为ctx_id=-1

        # 存储人脸特征向量的字典
        self.face_database = FaceDatabase()
        # 需要收集的有效帧数量
        self.required_frames = 5
        # 人脸检测置信度阈值
        self.confidence_threshold = 0.6
        # 有效帧之间的最小时间间隔（second)
        self.frame_interval = 0.5
        # 检测的最长持续时间
        self.detection_time_limit = 10

    def register_face(self, name, embedding, face_img):
        """注册新的人脸"""
        # 检测数据库中是否有类似人脸注册
        max_similarity, identity = self.face_database.compare_faces(embedding)

        if max_similarity == 0:
            # 保存到数据库
            self.face_database.face_data[name] = embedding

            # 保存人脸图像
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            face_filename = os.path.join(self.face_database.save_dir, f"{name}_{timestamp}.jpg")
            cv2.imwrite(face_filename, face_img)

            # 保存数据到文件
            self.face_database.save_faces()

            print(f"成功注册: {name}")
            return True
        else:
            print(f"当前人脸已被注册，用户为{identity}")
            return False

    def run(self):
        """运行主程序"""
        # 注册新人脸
        name = None
        while not name:
            name = input("Please enter your name: ").strip()
            if not name:
                print("Name cannot be empty.")
            elif name in self.face_database.face_data:
                print(f"姓名 '{name}' 已存在，请重新输入")
                name = None

        # 初始化摄像头
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # 记录初始时间
        start_time = time.time()
        # 上一个有效帧的时间
        last_collect_time = 0
        # 存储收集到的有效特征向量
        collected_embedding = []
        registration_status = REGISTER_UNFINISHED

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
                cv2.putText(frame, f"No Face Detected", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            else:
                # 在图像上绘制人脸框
                for face in faces:
                    bbox = face.bbox.astype(int)
                    color = (0, 255, 0)  # 绿色框
                    cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

                    # 绘制关键点
                    landmarks = face.kps.astype(int)
                    for landmark in landmarks:
                        cv2.circle(frame, tuple(landmark), 2, (0, 0, 255), -1)  # 红色点

                # 获取最大的人脸（按面积计算）用于注册
                face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                bbox = face.bbox.astype(int)
                face_img = frame[bbox[1]:bbox[3], bbox[0]:bbox[2]]

                # 判断当前注册状态
                if registration_status == REGISTER_SUCCESS:
                    cv2.putText(frame, f"Register Successfully!", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                elif registration_status == REGISTER_DUPLICATE:
                    cv2.putText(frame, f"Register Duplicate!", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                else:
                    # 检查人脸质量是否达标
                    if face.det_score > self.confidence_threshold:
                        cv2.putText(frame, f"Valid Face Detected", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                        #距离上一个有效帧需要一定间隔
                        if time.time() - last_collect_time > self.frame_interval:
                            # 提取特征向量
                            current_embedding = face.normed_embedding
                            # 更新有效帧时间戳
                            last_collect_time = time.time()
                            collected_embedding.append(current_embedding)

                            if len(collected_embedding) >= self.required_frames:
                                # 收集到足够的有效帧，则进行注册
                                avg_embedding = np.mean(collected_embedding, axis=0)
                                if self.register_face(name, avg_embedding, face_img):
                                    print("Register Successfully!")
                                    registration_status = REGISTER_SUCCESS
                                else:
                                    registration_status = REGISTER_DUPLICATE
                    else:
                        cv2.putText(frame, f"Invalid Face Detected", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 显示已注册的人脸数量
            cv2.putText(frame, f"Registered Number: {len(self.face_database.face_data)}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.putText(frame, "Press 'q' to quit", (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 显示图像
            cv2.imshow('Face Registration System', frame)

            # 键盘操作
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("用户手动退出程序")
                break

            #退出条件判断
            if registration_status == REGISTER_SUCCESS or registration_status == REGISTER_DUPLICATE:
                # 注册成功后显示2秒再退出
                if time.time() - last_collect_time > 5:
                    break
            elif elapsed_time > self.detection_time_limit:
                print("注册时间超过10s!")
                break

        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        print("程序已退出")

