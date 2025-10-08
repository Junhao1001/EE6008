# -*- coding: utf-8 -*-
# @Time : 20-6-9 上午10:20
# @Author : zhuying
# @Company : Minivision
# @File : anti_spoof_predict.py
# @Software : PyCharm

import os

import numpy as np
import torch
import torch.nn.functional as F
from src.face_recognition.functional import to_tensor, CropImage, get_kernel, parse_model_name
from src.face_recognition.MiniFASNet import MiniFASNetV1, MiniFASNetV2,MiniFASNetV1SE,MiniFASNetV2SE
from config.settings import LivenessModelParam
from config.paths import LIVENESS_MODEL_PATH

MODEL_MAPPING = {
    'MiniFASNetV1': MiniFASNetV1,
    'MiniFASNetV2': MiniFASNetV2,
    'MiniFASNetV1SE':MiniFASNetV1SE,
    'MiniFASNetV2SE':MiniFASNetV2SE
}

class AntiSpoofPredict:
    def __init__(self):
        self.device = torch.device("cpu")

        # 加载模型
        self._load_model(LIVENESS_MODEL_PATH)
        self.model.eval()

    def _load_model(self, model_path):
        # define model
        model_name = os.path.basename(model_path)
        h_input, w_input, model_type, _ = parse_model_name(model_name)
        self.kernel_size = get_kernel(h_input, w_input)
        self.model = MODEL_MAPPING[model_type](conv6_kernel=self.kernel_size).to(self.device)

        # load model weight
        state_dict = torch.load(model_path, map_location=self.device)
        keys = iter(state_dict)
        first_layer_name = keys.__next__()
        if first_layer_name.find('module.') >= 0:
            from collections import OrderedDict
            new_state_dict = OrderedDict()
            for key, value in state_dict.items():
                name_key = key[7:]
                new_state_dict[name_key] = value
            self.model.load_state_dict(new_state_dict)
        else:
            self.model.load_state_dict(state_dict)
        return None

    def img_preprocess(self, img, bbox):
        # 图像预处理
        image_cropper = CropImage()
        param = LivenessModelParam()

        # 图像裁剪至模型所需尺寸
        img = image_cropper.crop(img, bbox, param.scale, param.out_width, param.out_height, True)

        # 转换为Tensor
        dst_img = to_tensor(img)
        dst_img = dst_img.unsqueeze(0).to(self.device)
        return dst_img

    def predict(self, img, face_bbox):
        # 图像预处理
        input_img = self.img_preprocess(img, face_bbox)

        # 预测结果
        with torch.no_grad():
            result = self.model.forward(input_img)
            result = F.softmax(result).cpu().numpy()

        label = np.argmax(result)
        if label == 1:
            return True
        else:
            return False