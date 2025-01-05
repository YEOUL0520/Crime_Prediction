import os
import re
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pyngrok import ngrok
import uvicorn

app = FastAPI()

# 파일 경로 설정
base_dir = os.path.dirname(__file__)  # 현재 파일의 디렉터리
video_filenames = ["6_1_outputs.mp4", "6_2_outputs.mp4", "6_3_outputs.mp4"]  #이거 코드에 있는 폴더랑 같이 들어있어야함

# 정적 파일을 제공하기 위해 추가한 코드 (로고 이미지 삽입용)
app.mount("/static", StaticFiles(directory="."), name="static")

# 비디오 파일 존재 확인
for video_filename in video_filenames:
    video_path = os.path.join(base_dir, video_filename)
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")

# 비디오 스트리밍 함수
def stream_local_video(video_path, start_byte: int, chunk_size: int = 1024 * 1024):  # 1MB씩 전송
    with open(video_path, 'rb') as vid_file:
        vid_file.seek(start_byte)  # 지정된 위치에서 시작
        while chunk := vid_file.read(chunk_size):
            yield chunk

@app.get("/")
async def home():
    """HTML 페이지 제공"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>실시간 CCTV</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: grid;
                grid-template-columns: 1fr 3fr;
                gap: 0;
                margin: 0;
                height: 100vh;  /* 전체 화면 높이 */
            }}
            .menu {{
                padding: 20px;
                background-color: #01387A;
                color: white;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }}
            .menu h1 {{
                text-align: center;
            }}
            .menu div {{
                margin: 10px 0;
                border-bottom: 1px solid white;  /* 줄 추가 */
                padding-bottom: 10px;  /* 여백 추가 */
                display: flex;
                justify-content: space-between;  /* 양쪽 끝으로 정렬 */
                align-items: center;  /* 세로 정렬 */
            }}
            .menu div:first-child {{
                border-bottom: none;  /* 첫 번째 항목은 줄 제거 */
            }}
            .menu div:last-child {{
                border-bottom: none;  /* 마지막 항목은 줄 제거 */
            }}
            .logo-container img {{
                max-width: 40%;  /* 로고 크기 조정 */
                height: auto;   /* 비율 유지 */
                margin: 0 auto; /* 수평 가운데 정렬 */
            }}
            .video-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 0;
                height: 100%;  /* 비디오 그리드 높이 */
            }}
            .video-container {{
                overflow: hidden;  /* 테두리 없이 영상만 표시 */
            }}
            video {{
                width: 100%;
                height: 100%;  /* 영상이 구역을 가득 채우도록 설정 */
                object-fit: cover;  /* 비율을 유지하며 크기를 조절 */
            }}
            .dropdown {{
                display: none;  /* 기본적으로 드롭다운 숨김 */
            }}
            .dropdown-label {{
                cursor: pointer;  /* 클릭 가능하게 변경 */
            }}
            .alert {{
                display: none; /* 기본적으로 숨김 */
                position: fixed;
                top: 20%;
                left: 83%;
                transform: translate(-50%, -50%);
                background-color: white;
                color: black;
                padding: 20px;
                border: 3px solid red;
                z-index: 1000;
                text-align: center; /* 중앙 정렬 */
            }}
            alert button {{
                margin-top: 10px; /* 버튼과 텍스트 간의 여백 */
                padding: 10px 20px; /* 버튼 패딩 */
                cursor: pointer; /* 클릭 가능하게 */
            }}
        </style>
        <script>
            function showAlert() {{
                document.getElementById('alert').style.display = 'block';
            }}
            function hideAlert() {{
                document.getElementById('alert').style.display = 'none';
            }}
            function startVideoAlert() {{
                setTimeout(showAlert, 2000); // 2초 후에 showAlert 호출
            }}
        </script>
    </head>
    <body>
        <div class="menu">
            <div class="logo-container">
                <img src="/static/logo2.png" alt="로고" style="max-width: 40%; height: auto;">
            </div>
            <h1 style="text-align: center;">실시간 CCTV<br>모니터링 시스템</h1>
            <div>
                <label class="dropdown-label" onclick="toggleDropdown('date-dropdown')">
                    일자별 다시보기
                </label>
                <span onclick="toggleDropdown('date-dropdown')" style="cursor: pointer; font-size: 1.5em;">&#9662;</span> <!-- 아래쪽 화살표 -->
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
                <span onclick="toggleDropdown('location-dropdown')" style="cursor: pointer; font-size: 1.5em;">&#9662;</span> <!-- 아래쪽 화살표 -->
                <select id="location-dropdown" class="dropdown">
                    <option value="1">1층</option>
                    <option value="2">2층</option>
                    <option value="3">3층</option>
                </select>
            </div>
            <div class="logo-container">
                <img src="/static/logo.png" alt="로고" style="max-width: 100%; height: auto;">
            </div>
        </div>
        <div class="video-grid">
    """

    # 비디오 파일 목록을 바로 HTML에 삽입하여 비디오를 표시
    for video_filename in video_filenames:
        video_path = f"/video/{video_filename}"
        html_content += f"""
        <div class="video-container">
            <video controls autoplay muted loop>
                <source src="{video_path}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
        """

    html_content += """
        </div>
        <script>
            function toggleDropdown(id) {{
                var dropdown = document.getElementById(id);
                if (dropdown.style.display === "none" || dropdown.style.display === "") {{
                    dropdown.style.display = "block";  // 드롭다운 보이기
                }} else {{
                    dropdown.style.display = "none";  // 드롭다운 숨기기
                }}
            }}
        </script>
        <div id="alert" class="alert">
            <p>흉기가 감지되었습니다!</p>
            <button onclick="hideAlert()">확인</button>
        </div>
        <script>
            startVideoAlert(); // 페이지 로드 시 비디오 재생 2초 후 알림 시작
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)



@app.get("/video/{filename}")
async def video_stream(request: Request, filename: str):
    """비디오 스트리밍"""
    video_path = os.path.join(base_dir, filename)
    
    if not os.path.exists(video_path):
        return HTMLResponse(content="Error: Video file not found", status_code=404)

    range_header = request.headers.get('Range')
    start_byte = 0
    end_byte = None
    if range_header:
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start_byte = int(range_match.group(1))
            end_byte = int(range_match.group(2)) if range_match.group(2) else None

    def generate_video():
        return stream_local_video(video_path, start_byte)

    file_size = os.path.getsize(video_path)
    headers = {
        "Content-Range": f"bytes {start_byte}-{end_byte or file_size - 1}/{file_size}",
        "Accept-Ranges": "bytes"
    }

    return StreamingResponse(generate_video(), headers=headers, media_type="video/mp4", status_code=206)

# ngrok 연결
ngrok_tunnel = ngrok.connect(5000)  # 포트를 5000으로 설정
print(f"Public URL: {ngrok_tunnel.public_url}")

# 서버 실행
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
