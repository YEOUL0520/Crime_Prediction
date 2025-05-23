import cv2
import torch
import threading
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pyngrok import ngrok
from ultralytics import YOLO
from queue import Queue
import simpleaudio as sa  # playsound 대신 simpleaudio 사용

app = FastAPI()

# 모델 로드
person_model = YOLO("yolo11n.pt")  # 사람 탐지 모델
knife_model = YOLO("customknife_v1.1.pt")  # 나이프 탐지 모델

# 각 카메라의 프레임을 전송할 큐
frame_queues = {0: Queue(), 1: Queue()}
# 각 카메라의 이벤트(알림) 큐
event_queues = {0: Queue(), 1: Queue()}

alarm_playing = threading.Event()

# 알람 함수 수정 -> 상황별 조건문 설정
# 조건별 음성 종류 다양화 / 음성 길이 줄여서 짧은 상황 대응되도록 할 것 / 경보음도 추가 (사이렌 소리)
# 경찰청 규정? 같은거 찾아보기 (보행 신호 자동 연장 시스템 표준 규격) ->ppt 상에도 추가해 볼 것 (참고/소리 크기.종류.성별etc)
def play_alarm():
    if not alarm_playing.is_set():
        alarm_playing.set()
        try:
            wave_obj = sa.WaveObject.from_wave_file("alarm.wav")  # .mp3 → .wav로 변경
            play_obj = wave_obj.play()
            play_obj.wait_done()
        except Exception as e:
            print(f"알람 재생 중 오류 발생: {e}")
        finally:
            alarm_playing.clear()

# 웹캠 열리는 번호 수정 (1,2)로 수정해야함
def capture_frames(cam_id: int, frame_queue: Queue, event_queue: Queue):
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
        knife_results = knife_model(frame, conf=0.7, verbose=False) # 0.7정확도로 수정

        knife_detected = False

        # Person 모델의 결과 처리
        for result in person_results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                cls = int(box.cls[0].item())
                label = "Person" if cls == 0 else None

                if conf > 0.5 and label == "Person":
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(frame, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Knife 모델의 결과 처리
        for result in knife_results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                label = "Knife"

                if conf > 0.5 and label == "Knife":
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                    cv2.putText(frame, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    knife_detected = True

        # 감지 이벤트 있으면 큐에 추가
        # 상황별 음성을 다르게 한 설계서가 있었으면 좋겠음. 
        # 어느 상황에 어떤 음성이 나오고 어떤 안내가 나오는지를 구체적으로 작성할 것 (표준화하기기)

        if knife_detected and event_queue.empty():
            event_queue.put({"type": "alert", "message": "⚠️ 흉기 감지!"})
            threading.Thread(target=play_alarm, daemon=True).start()

        frame_queue.put(frame)

    cap.release()

@app.get("/")
async def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8" />
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
                position: relative;
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
            .alertBox {
                display: none;
                position: absolute;
                top: 20px;
                left: 20px;
                background-color: rgba(255, 76, 76, 0.85);
                color: white;
                padding: 15px 20px;
                border-radius: 10px;
                font-size: 16px;
                box-shadow: 0 0 15px rgba(255, 0, 0, 0.7);
                z-index: 10;
            }
            .alertBox button {
                margin-left: 15px;
                background-color: white;
                color: #ff4c4c;
                border: none;
                padding: 5px 10px;
                font-weight: bold;
                border-radius: 5px;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="menu">
            <div class="logo-container">
                <img src="/static/logo2.png" alt="로고">
            </div>
            <h1>실시간 CCTV<br>모니터링 시스템</h1>
            <div>
                <label class="dropdown-label" onclick="toggleDropdown('date-dropdown')">
                    일자별 다시보기
                </label>
                <span onclick="toggleDropdown('date-dropdown')" style="cursor: pointer; font-size: 1.5em;">&#9662;</span>
                <select id="date-dropdown" class="dropdown">
                    <option value="1">1월</option>
                    <option value="2">2월</option>
                    <option value="3">3월</option>
                    <option value="4">4월</option>
                    <option value="5">5월</option>
                    <option value="6">6월</option>
                    <option value="7">7월</option>
                    <option value="8">8월</option>
                    <option value="9">9월</option>
                    <option value="10">10월</option>
                    <option value="11">11월</option>
                    <option value="12">12월</option>
                </select>
            </div>
            <div>
                <label class="dropdown-label" onclick="toggleDropdown('location-dropdown')">
                    장소별 다시보기
                </label>
                <span onclick="toggleDropdown('location-dropdown')" style="cursor: pointer; font-size: 1.5em;">&#9662;</span>
                <select id="location-dropdown" class="dropdown">
                    <option value="1">1층</option>
                    <option value="2">2층</option>
                    <option value="3">3층</option>
                </select>
            </div>
            <div class="logo-container">
                <img src="/static/logo.png" alt="하단 로고">
            </div>
        </div>
        
        <div class="video-grid">
            <div class="video-container">
                <canvas id="cam0" width="640" height="480"></canvas>
                <div id="alertBox0" class="alertBox">
                    <span class="alertMessage"></span>
                    <button class="alertCloseBtn">확인</button>
                </div>
            </div>
            <div class="video-container">
                <canvas id="cam1" width="640" height="480"></canvas>
                <div id="alertBox1" class="alertBox">
                    <span class="alertMessage"></span>
                    <button class="alertCloseBtn">확인</button>
                </div>
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

            function showAlert(camId, message) {
                const alertBox = document.getElementById(`alertBox${camId}`);
                const alertMessage = alertBox.querySelector('.alertMessage');
                alertMessage.textContent = message;
                alertBox.style.display = 'block';
            }

            document.querySelectorAll('.alertCloseBtn').forEach((btn, idx) => {
                btn.onclick = () => {
                    const alertBox = document.getElementById(`alertBox${idx}`);
                    alertBox.style.display = 'none';
                };
            });

            function connectAlertWebSocket(camId) {
                const ws = new WebSocket(`wss://${location.host}/event/${camId}`);
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === "alert") {
                        showAlert(camId, data.message);
                    }
                };
                ws.onerror = (e) => console.error("Alert WS error", e);
                ws.onclose = () => console.warn("Alert WS closed");
            }

            connectWebSocket(0);
            connectWebSocket(1);
            connectAlertWebSocket(0);
            connectAlertWebSocket(1);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/video/live/{cam_id}")
async def video_stream(websocket: WebSocket, cam_id: int):
    await websocket.accept()
    while True:
        if not frame_queues[cam_id].empty():
            frame = frame_queues[cam_id].get()
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                await websocket.send_bytes(jpeg.tobytes())
        await asyncio.sleep(0.05)

@app.websocket("/event/{cam_id}")
async def event_stream(websocket: WebSocket, cam_id: int):
    await websocket.accept()
    try:
        while True:
            if not event_queues[cam_id].empty():
                event = event_queues[cam_id].get()
                await websocket.send_json(event)
            else:
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    ngrok_tunnel = ngrok.connect(5000)
    print(f"Public URL: {ngrok_tunnel.public_url}")

    threading.Thread(target=capture_frames, args=(0, frame_queues[0], event_queues[0]), daemon=True).start()
    threading.Thread(target=capture_frames, args=(1, frame_queues[1], event_queues[1]), daemon=True).start()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)