import os
import json
import numpy as np
from config.paths import FACE_DATA_DIR

class FaceDatabase:
    def __init__(self):
        # 存储人脸特征向量的字典
        self.face_data = {}

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
                    self.face_data[name] = np.array(embedding_list)
            print(f"已加载 {len(self.face_data)} 个人脸数据")

    def save_faces(self):
        """保存人脸数据到文件"""
        data_file = os.path.join(self.save_dir, "face_data.json")
        # 将numpy数组转换为列表以便JSON序列化
        save_data = {name: embedding.tolist() for name, embedding in self.face_data.items()}
        with open(data_file, 'w') as f:
            json.dump(save_data, f)
        print(f"已保存 {len(self.face_data)} 个人脸数据")