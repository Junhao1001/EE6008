import cv2
from insightface.app import FaceAnalysis
import numpy as np
import os
import json
from datetime import datetime
from config.paths import FACE_DATA_DIR

class FaceRecorder:
    def __init__(self):
        # 初始化人脸分析应用
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1)  # 使用GPU，如果使用CPU则设置为ctx_id=-1

        # 存储人脸特征向量的字典
        self.face_database = {}

        # 创建保存人脸的文件夹
        self.save_dir = FACE_DATA_DIR
        # os.makedirs(self.save_dir, exist_ok=True)

        # 加载已存在的人脸数据
        self.load_faces()

    def load_faces(self):
        """从文件加载已注册的人脸数据"""
        data_file = os.path.join(self.save_dir, "face_data.json")
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                # 将列表数据转换回numpy数组
                for name, embedding_list in data.items():
                    self.face_database[name] = np.array(embedding_list)
            print(f"已加载 {len(self.face_database)} 个人脸数据")

    def save_faces(self):
        """保存人脸数据到文件"""
        data_file = os.path.join(self.save_dir, "face_data.json")
        # 将numpy数组转换为列表以便JSON序列化
        save_data = {name: embedding.tolist() for name, embedding in self.face_database.items()}
        with open(data_file, 'w') as f:
            json.dump(save_data, f)
        print(f"已保存 {len(self.face_database)} 个人脸数据")

    def register_face(self, name, frame):
        """注册新的人脸"""
        # 检测人脸
        faces = self.app.get(frame)

        if len(faces) == 0:
            print("未检测到人脸，请调整位置")
            return False
        elif len(faces) > 1:
            print("检测到多个人脸，请确保只有一个人")
            return False
        else:
            # 获取最大的人脸（按面积计算）
            face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

            # 提取特征向量
            embedding = face.normed_embedding

            # 保存到数据库
            self.face_database[name] = embedding

            # 保存人脸图像
            bbox = face.bbox.astype(int)
            face_img = frame[bbox[1]:bbox[3], bbox[0]:bbox[2]]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            face_filename = os.path.join(self.save_dir, f"{name}_{timestamp}.jpg")
            cv2.imwrite(face_filename, face_img)

            # 保存数据到文件
            self.save_faces()

            print(f"成功注册: {name}")
            return True

    def run(self):
        """运行主程序"""
        # 初始化摄像头
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("人脸录入系统启动")
        print("按 'r' 键注册新人脸")
        print("按 'q' 键退出程序")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("无法获取视频帧")
                break

            # 水平翻转图像（镜像效果）
            frame = cv2.flip(frame, 1)

            # 检测人脸（但不提取特征，只用于显示）
            faces = self.app.get(frame)

            # 在图像上绘制人脸框
            for face in faces:
                bbox = face.bbox.astype(int)
                color = (0, 255, 0)  # 绿色框
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

                # 绘制关键点
                landmarks = face.kps.astype(int)
                for landmark in landmarks:
                    cv2.circle(frame, tuple(landmark), 2, (0, 0, 255), -1)  # 红色点

            # 显示已注册的人脸数量
            cv2.putText(frame, f"已注册: {len(self.face_database)} 人", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 显示操作提示
            cv2.putText(frame, "Press 'r' to register", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, "Press 'q' to quit", (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 显示图像
            cv2.imshow('Face Registration System', frame)

            # 键盘操作
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                # 注册新人脸
                name = input("请输入姓名: ").strip()
                if name:
                    if name in self.face_database:
                        print(f"姓名 '{name}' 已存在，是否覆盖? (y/n)")
                        choice = input().strip().lower()
                        if choice != 'y':
                            continue

                    # 使用当前帧注册人脸
                    self.register_face(name, frame)
                else:
                    print("姓名不能为空")

        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        print("程序已退出")

