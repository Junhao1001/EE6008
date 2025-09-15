import insightface
import cv2
import numpy as np
import time

# 初始化模型 - 使用CPU
model = insightface.app.FaceAnalysis(name='buffalo_l')
model.prepare(ctx_id=-1)  # ctx_id=-1 表示使用CPU

# 读取测试图像
img = cv2.imread('data/face_samples/sample1.jpg')  # 替换为您的测试图像路径
if img is None:
    print("无法读取图像，请提供有效的图像路径")
    exit()

# 进行人脸分析
start_time = time.time()
faces = model.get(img)
elapsed_time = time.time() - start_time

print(f"处理时间: {elapsed_time:.2f} 秒")

if len(faces) == 0:
    print("未检测到人脸")
else:
    # 获取第一个人脸的特征向量
    face = faces[0]
    embedding = face.embedding
    print(f"检测到 {len(faces)} 张人脸")
    print(f"特征向量形状: {embedding.shape}")
    print(f"特征向量前5个值: {embedding[:5]}")

    # 绘制人脸框（可选）
    for face in faces:
        bbox = face.bbox.astype(int)
        cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)

    # 保存结果图像
    cv2.imwrite('data/face_samples/result1.jpg', img)
    print("结果已保存到 result.jpg")