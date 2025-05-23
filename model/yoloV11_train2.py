from ultralytics import YOLO
from roboflow import Roboflow
import torch

# Roboflow 데이터셋 다운로드, 데이터셋 ver.2
rf = Roboflow(api_key="arQQJlhQp5Z2aUNJ6kBj")
project = rf.workspace("work-4iofb").project("knife-detection-bstjz-2k6wu")
version = project.version(2)
dataset = version.download("yolov11")
                

# 모델 import
model = YOLO("yolo11n.pt") 

# 모델 학습 (gpu 사용, 환경에서 학습습)
model.train(
    data=dataset.location + "/data.yaml",
    epochs=100,
    imgsz=960,
    batch=16,
    device="cuda",
    augment=True,
    degrees=10,
    translate=0.1,
    scale=0.5,
    shear=2.0,
    perspective=0.001,
    flipud=0.2,
    mosaic=True,
    mixup=0.2,
    optimizer="AdamW"
)

# 모델 저장 (v1.2)
model.save("customknife_v1.2.pt")

# Validation 평가
print("\nValidation 평가:")
val_results = model.val()

# Test 평가 (Roboflow 테스트셋 사용)
print("\nTest 평가:")
test_results = model.val(data=dataset.location + "/data.yaml", split="test")

# 결과 확인
print("\nValidation:")
print(val_results)

print("\nTest:")
print(test_results)