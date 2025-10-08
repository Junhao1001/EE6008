import os
import json
import numpy as np
from config.paths import FACE_DATA_DIR
from config.settings import FACE_MATCHING_THRESHOLD

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
        # 从文件加载已注册的人脸数据
        data_file = os.path.join(self.save_dir, "face_data.json")
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                # 将列表数据转换回numpy数组
                for name, embedding_list in data.items():
                    self.face_data[name] = np.array(embedding_list)
            print(f"已加载 {len(self.face_data)} 个人脸数据")

    def save_faces(self):
        # 保存人脸数据到文件
        data_file = os.path.join(self.save_dir, "face_data.json")
        # 将numpy数组转换为列表以便JSON序列化
        save_data = {name: embedding.tolist() for name, embedding in self.face_data.items()}
        with open(data_file, 'w') as f:
            json.dump(save_data, f)
        print(f"已保存 {len(self.face_data)} 个人脸数据")

    def delete_faces(self, name):
        # 根据姓名删除人脸数据
        if name in self.face_data:
            del self.face_data[name]
            # 同步保存到本地文件中
            self.save_faces()
            print(f"成功删除姓名为{name}的人脸数据")
        else:
            print(f"未查询到姓名为{name}的人脸数据")

    def compare_faces(self, input_embedding):
        # 在当前数据库中查找和输入人脸特征最匹配的向量(需大于匹配阈值)，返回相似度和姓名
        if not self.face_data:
            print("人脸数据库为空，无法进行比对")
            return 0.0, "Unknown"

        # 初始化返回值
        max_similarity = 0
        most_similar_name = "Unknown"
        threshold = FACE_MATCHING_THRESHOLD

        for name, db_embedding in self.face_data.items():
            # 计算相似度
            similarity = np.dot(input_embedding, db_embedding)

            # 如果相似度大于阈值，则认为成功匹配
            if similarity > threshold:
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_name = name

        print(f"最大相似度为: {max_similarity:.4f}，对应姓名: {most_similar_name}")
        return max_similarity, most_similar_name

    def show_names(self):
        for name in self.face_data:
            print(name)
