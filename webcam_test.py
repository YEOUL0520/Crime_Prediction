import cv2
from ultralytics import YOLO


# 모델 로드 (COCO 사전 학습 모델 & 커스텀 나이프 모델)
person_model = YOLO("yolo11s.pt")  # 사람 탐지 (COCO 모델)
knife_model = YOLO("best(v11ep100).pt")  # 나이프 탐지 (커스텀 모델)

# 커스텀 라벨 정의
custom_labels = {0: "Person", 1: "Knife"}

# 웹캠 실행
cap1 = cv2.VideoCapture(0)
cap2 = cv2.VideoCapture(1)
cap3 = cv2.VideoCapture(2)

CONFIDENCE=0.5
LABEL_COLORS = {"Person": (0, 255, 0), "Knife": (0, 0, 255)}

def detect_objects(frame, models_labels):
    for model, label in models_labels:
        results = model.predict(frame, conf = CONFIDENCE, classes=[0])
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf.item()
            color = LABEL_COLORS[label]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame

if not cap1.isOpened():
    print("웹캠을 열 수 없습니다.")
    exit()

if not cap2.isOpened():
    print("웹캠을 열 수 없습니다.")
    exit()

if not cap3.isOpened():
    print("웹캠을 열 수 없습니다.")
    exit()

while True:
    ret1, frame1 = cap1.read()
    ret2, frame2 = cap2.read()
    ret3, frame3 = cap3.read()
    if not ret1 or not ret2:
        print("프레임을 가져올 수 없습니다.")
        break

    # 웹캠 1에 대해 YOLO 객체 탐지 
    person_results1 = person_model.predict(frame1, conf=0.35, classes=[0])
    knife_results1 = knife_model.predict(frame1, conf=0.35, classes=[0])

    # 웹캠 2에 대해 YOLO 객체 탐지 
    person_results2 = person_model.predict(frame2, conf=0.35, classes=[0])
    knife_results2 = knife_model.predict(frame2, conf=0.35, classes=[0])

    person_results3 = person_model.predict(frame3, conf=0.35, classes=[0])
    knife_results3 = knife_model.predict(frame3, conf=0.35, classes=[0])

    # 탐지된 객체 리스트
    all_results1 = [person_results1, knife_results1]
    all_results2 = [person_results2, knife_results2]
    all_results3 = [person_results3, knife_results3]

  # 객체 탐지
    frame1 = detect_objects(frame1, [(person_model, "Person"), (knife_model, "Knife")])
    frame2 = detect_objects(frame2, [(person_model, "Person"), (knife_model, "Knife")])
    frame3 = detect_objects(frame3, [(person_model, "Person"), (knife_model, "Knife")])

    # 두 웹캠의 결과를 화면에 출력
    cv2.imshow("Webcam 1 - YOLO Object Detection", frame1)
    cv2.imshow("Webcam 2 - YOLO Object Detection", frame2)
    cv2.imshow("Webcam 3 - YOLO Object Detection", frame3)

    # ESC 키 누르면 종료
    if cv2.waitKey(1) & 0xFF == 27:
        break

# 자원 해제
cap1.release()
cap2.release()
cap3.release()
cv2.destroyAllWindows()
