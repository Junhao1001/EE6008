import cv2
from insightface.app import FaceAnalysis
import os
from datetime import datetime
from core.face_database import FaceDatabase

class FaceRecorder:
    def __init__(self):
        # 初始化人脸分析应用
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1)  # 使用GPU，如果使用CPU则设置为ctx_id=-1

        # 存储人脸特征向量的字典
        self.face_database = FaceDatabase()

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

            # 检测数据库中已有类似人脸注册
            max_similarity, identity = self.face_database.compare_faces(embedding)

            if max_similarity == 0:
                # 保存到数据库
                self.face_database.face_data[name] = embedding

                # 保存人脸图像
                bbox = face.bbox.astype(int)
                face_img = frame[bbox[1]:bbox[3], bbox[0]:bbox[2]]
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
            cv2.putText(frame, f"Registered Number: {len(self.face_database.face_data)}", (10, 30),
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
                    if name in self.face_database.face_data:
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

