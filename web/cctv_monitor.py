#웹소켓을 이용한 실시간 비디오 스트리밍

import cv2
import torch
import threading
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pyngrok import ngrok
from ultralytics import YOLO
from queue import Queue

app = FastAPI()

# 모델 로드
person_model = YOLO("yolo11n.pt")  # 사람 탐지 모델
knife_model = YOLO("customknife_v1.1.pt")  # 나이프 탐지 모델
custom_labels = {0: "Person", 1: "Knife"}

# 각 카메라의 프레임을 전송할 큐
frame_queues = {0: Queue(), 1: Queue()}

# 각 카메라에서 영상 캡처를 위한 함수
def capture_frames(cam_id: int, frame_queue: Queue):
    cap = cv2.VideoCapture(cam_id)
    if not cap.isOpened():
        print(f"웹캠 {cam_id}을 열 수 없습니다.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (320, 240))

        # 사람 및 나이프 추론
        person_results = person_model(frame, conf=0.5, verbose=False)
        knife_results = knife_model(frame, conf=0.5, verbose=False)

        # Person 모델의 결과 처리
        for result in person_results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                cls = int(box.cls[0].item())
                label = "Person" if cls == 0 else None  # cls가 0인 경우에만 "Person"

                # "Person"만 처리 (cls == 0인 경우)
                if conf > 0.5 and label == "Person":
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(frame, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                            
        # Knife 모델의 결과 처리
        for result in knife_results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                cls = int(box.cls[0].item())
                label = "Knife"  # 칼은 항상 "Knife"

                if conf > 0.5 and label == "Knife":
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                    cv2.putText(frame, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # 큐에 프레임 넣기
        frame_queues[cam_id].put(frame)

    cap.release()

@app.get("/")
async def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>실시간 CCTV</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                display: flex;
                height: 100vh;
            }
            .menu {
                width: 20%;
                background-color: #01387A;
                color: white;
                padding: 20px;
                text-align: center;
            }
            .menu img {
                width: 80%;
                margin-bottom: 20px;
            }
            .video-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                width: 80%;
                height: 100%;
            }
            .video-container {
                overflow: hidden;
                height: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
                background-color: black;
            }
            canvas {
                width: 100%;
                height: 100%;
                object-fit: contain;
                background-color: #000;
            }
        </style>
    </head>
    <body>
        <div class="menu">
            <img src="/static/logo2.png" alt="로고"
            <h1>실시간 CCTV<br>모니터링 시스템</h1>
        </div>
        <div class="video-grid">
            <div class="video-container">
                <canvas id="cam0" width="640" height="480"></canvas>
            </div>
            <div class="video-container">
                <canvas id="cam1" width="640" height="480"></canvas>
            </div>
        </div>

        <script>
        function connectWebSocket(camId) {
            const canvas = document.getElementById(`cam${camId}`);
            const ctx = canvas.getContext('2d');
            const ws = new WebSocket(`wss://${location.host}/video/live/${camId}`);

            let img = new Image();
            img.onload = () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            };

            ws.binaryType = 'blob';
            ws.onmessage = (event) => {
                const blob = new Blob([event.data], { type: 'image/jpeg' });
                img.src = URL.createObjectURL(blob);
            };

            ws.onerror = (e) => console.error(`WebSocket error on camera ${camId}`, e);
            ws.onclose = () => console.warn(`WebSocket closed for camera ${camId}`);
        }

        // 두 카메라 연결 시도
        connectWebSocket(0);
        connectWebSocket(1);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 영상 스트리밍 웹소켓 라우트
@app.websocket("/video/live/{cam_id}")
async def video_stream(websocket: WebSocket, cam_id: int):
    await websocket.accept()

    while True:
        if not frame_queues[cam_id].empty():
            frame = frame_queues[cam_id].get()

            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                await websocket.send_bytes(jpeg.tobytes())
        await asyncio.sleep(0.05)  # 20fps

# === 실행부 ===

# ngrok 연결
ngrok_tunnel = ngrok.connect(5000)
print(f"Public URL: {ngrok_tunnel.public_url}")

# 멀티스레딩으로 카메라 영상 캡처 시작
threading.Thread(target=capture_frames, args=(0, frame_queues[0]), daemon=True).start()
threading.Thread(target=capture_frames, args=(1, frame_queues[1]), daemon=True).start()

# FastAPI 실행
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=5000)