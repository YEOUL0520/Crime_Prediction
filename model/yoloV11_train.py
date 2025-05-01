import torch
from ultralytics import YOLO

# YOLO 모델 파일 경로 (절대 경로로 설정)
model_path = r"C:\Users\sally\Desktop\4-1\정통_종설\Crime_Prediction\yolo11n.pt"  # 다운로드한 모델 사용

# 모델 로드
model = YOLO(model_path)  

# 학습 데이터 경로
data_yaml = r"C:\Users\sally\Desktop\4-1\정통_종설\Crime_Prediction\ver1.1\data\data.yaml"

# GPU 사용 여부 확인
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 학습 실행
model.train(
    data=data_yaml,
    epochs=100,        
    imgsz=640,        
    batch=16,         
    device=device,    
    augment=True,
    optimizer="AdamW"
)

# 학습된 모델 저장
model.save("customknife_v1.1.pt")