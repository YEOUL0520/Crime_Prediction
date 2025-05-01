import cv2
from ultralytics import YOLO

# 모델 로드 (COCO 사전 학습 모델 & 커스텀 나이프 모델)
person_model = YOLO("yolo11n.pt")  # 사람 탐지 (COCO 모델)
knife_model = YOLO("customknife_v1.1.pt")  # 나이프 탐지 (커스텀 모델)

# 커스텀 라벨 정의
custom_labels = {0: "Person", 1: "Knife"}

# 웹캠 실행
cap1 = cv2.VideoCapture(0)
#cap2 = cv2.VideoCapture(1)

if not cap1.isOpened():
    print("웹캠을 열 수 없습니다.")
    exit()

while True:
    ret1, frame1 = cap1.read()
    if not ret1:
        print("프레임을 가져올 수 없습니다.")
        break

    # 웹캠 1에 대해 YOLO 객체 탐지 (사람 탐지)
    person_results1 = person_model.predict(frame1, conf=0.35, classes=[0])
    knife_results1 = knife_model.predict(frame1, conf=0.35, classes=[0])


    # 탐지된 객체 리스트
    all_results1 = [person_results1, knife_results1]

    # 웹캠 1 결과 처리
    for model_results, label in zip(all_results1, ["Person", "Knife"]):
        for box in model_results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf.item()
            color = (0, 255, 0) if label == "Person" else (0, 0, 255)
            cv2.rectangle(frame1, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame1, f"{label} {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # 두 웹캠의 결과를 화면에 출력
    cv2.imshow("Webcam 1 - YOLO Object Detection", frame1)

    # ESC 키 누르면 종료
    if cv2.waitKey(1) & 0xFF == 27:
        break

# 자원 해제
cap1.release()
cv2.destroyAllWindows()