# simpleaudio의 경우 wav형식만 인식하기 때문에 별도의 변환 코드 생성해 변환 진행행
from pydub import AudioSegment

sound = AudioSegment.from_mp3("alarm.mp3")
sound.export("alarm.wav", format="wav")
