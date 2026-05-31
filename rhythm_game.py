import cv2
import mediapipe as mp
import pygame
import random
import time
import os
import librosa
import numpy as np

# ==========================================
# 1. 初始化與全域參數
# ==========================================
WIDTH, HEIGHT = 640, 480
HIT_WINDOW = 0.25         # 判定成功時間窗口 (秒)
SELECT_TIME = 1.5         # 選單懸停選取時間 (秒)
LATENCY_OFFSET = 0.1      # 延遲補償 (根據硬體效能調整)
SONG_FOLDER = "music"     # 音樂資料夾路徑

# 初始化 MediaPipe 手部偵測
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.8,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# 初始化 Pygame 音訊系統
pygame.mixer.init()

# 確保音樂資料夾存在
if not os.path.exists(SONG_FOLDER):
    os.makedirs(SONG_FOLDER)

# ==========================================
# 2. 核心邏輯功能
# ==========================================

def analyze_music(file_path):
    """ 使用 Librosa 分析音樂並提取節拍點 """
    print(f"[*] 正在分析譜面: {os.path.basename(file_path)}，請稍候...")
    try:
        y, sr = librosa.load(file_path)
        # 提取節拍 (Beats)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        print(f"[+] 分析完成！估計 BPM: {tempo:.2f}")
        return beat_times.tolist()
    except Exception as e:
        print(f"[!] 分析失敗: {e}")
        return [i * 0.5 for i in range(1, 100)] # 失敗時回傳預設節拍

def get_gesture_info(hand_landmarks):
    """ 判定玩家手勢：必須僅伸出食指，並判斷其指向 """
    # 取得關鍵點位置
    tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    
    # 判斷手指是否伸直 (簡化判斷：食指尖端 Y 座標低於第二關節)
    # 同時檢查其他手指是否收起 (中指尖端 Y 座標高於其關節)
    is_index_open = tip.y < pip.y
    is_middle_closed = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y > \
                       hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
    
    if is_index_open and is_middle_closed:
        dx = tip.x - mcp.x
        dy = tip.y - mcp.y
        if abs(dx) > abs(dy):
            return "LEFT" if dx < 0 else "RIGHT"
        else:
            return "UP" if dy < 0 else "DOWN"
    return None

# ==========================================
# 3. 遊戲主類別
# ==========================================

class RhythmGame:
    def __init__(self):
        self.state = "MENU"
        self.songs = [f for f in os.listdir(SONG_FOLDER) if f.endswith('.mp3')]
        self.score = 0
        self.combo = 0
        self.beat_chart = []
        self.beat_ptr = 0
        self.current_target = "UP"
        
        # 視覺特效與懸停邏輯
        self.flash_timer = 0
        self.flash_color = (0, 0, 0)
        self.hover_idx = -1
        self.hover_start_time = 0
        self.selected_song_path = None

    def start_game(self, song_name):
        self.selected_song_path = os.path.join(SONG_FOLDER, song_name)
        self.state = "LOADING"

    def _perform_analysis(self):
        path = self.selected_song_path
        self.beat_chart = analyze_music(path)
        self.beat_ptr = 0
        self.score = 0
        self.combo = 0
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        self.state = "GAME"

    def update(self, frame, finger_pos, gesture):
        if self.state == "MENU":
            self.draw_menu(frame, finger_pos)
        elif self.state == "LOADING":
            cv2.putText(frame, "ANALYZING MUSIC...", (150, HEIGHT//2), 1, 2, (0, 255, 255), 2)
            cv2.imshow("Gesture Game", frame)
            cv2.waitKey(1)
            self._perform_analysis()
        elif self.state == "GAME":
            self.draw_game(frame, gesture)
        
        # 繪製全亮/閃爍回饋
        if self.flash_timer > 0:
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), self.flash_color, -1)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            self.flash_timer -= 1

    def draw_menu(self, frame, finger_pos):
        cv2.putText(frame, "MUSIC GESTURE SELECT", (120, 60), 1, 2, (255, 255, 255), 2)
        
        if not self.songs:
            cv2.putText(frame, "Please add MP3 files to /music folder", (80, 240), 1, 1.2, (0, 0, 255), 2)
            return

        for i, song in enumerate(self.songs[:4]): # 顯示前 4 首音樂
            x, y, w, h = 150, 120 + i*80, 340, 60
            hover = finger_pos and x < finger_pos[0] < x+w and y < finger_pos[1] < y+h
            
            color = (0, 255, 255) if hover else (180, 180, 180)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, song[:25], (x+15, y+40), 1, 1.2, (255, 255, 255), 1)
            
            if hover:
                if self.hover_idx != i:
                    self.hover_idx = i
                    self.hover_start_time = time.time()
                
                prog = min(1.0, (time.time() - self.hover_start_time) / SELECT_TIME)
                cv2.rectangle(frame, (x, y+h-5), (x + int(w * prog), y+h), (0, 255, 0), -1)
                if prog >= 1.0:
                    self.start_game(song)
            elif self.hover_idx == i:
                self.hover_idx = -1

    def draw_game(self, frame, gesture):
        m_time = (pygame.mixer.music.get_pos() / 1000.0) - LATENCY_OFFSET
        if m_time < 0 or self.beat_ptr >= len(self.beat_chart):
            if self.beat_ptr >= len(self.beat_chart) and not pygame.mixer.music.get_busy():
                self.state = "MENU"
            return

        target_time = self.beat_chart[self.beat_ptr]

        # Miss 判定
        if m_time > target_time + HIT_WINDOW:
            self.beat_ptr += 1
            self.combo = 0
            self.current_target = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
            self.flash_timer, self.flash_color = 5, (0, 0, 200) # 紅色

        # Hit 判定
        if abs(m_time - target_time) <= HIT_WINDOW:
            if gesture == self.current_target:
                self.score += 10 + (self.combo // 5)
                self.combo += 1
                self.beat_ptr += 1
                self.current_target = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
                self.flash_timer, self.flash_color = 5, (0, 200, 0) # 綠色

        # 介面繪製
        cv2.putText(frame, f"SCORE: {self.score}", (20, 40), 1, 1.5, (255, 255, 255), 2)
        cv2.putText(frame, f"COMBO: {self.combo}", (20, 80), 1, 1.5, (0, 255, 255), 2)
        cv2.putText(frame, "TARGET:", (WIDTH//2-50, 150), 1, 1.2, (255, 255, 255), 1)
        cv2.putText(frame, self.current_target, (WIDTH//2-60, 220), 1, 3, (0, 255, 0), 5)
        
        # 節奏收縮圈
        t_diff = target_time - m_time
        if t_diff > 0:
            r = int(80 * (t_diff / 0.8)) if t_diff < 0.8 else 80
            cv2.circle(frame, (WIDTH//2, 200), max(10, r), (255, 255, 255), 2)

# ==========================================
# 4. 執行入口
# ==========================================

def main():
    print("[*] 正在啟動鏡頭，請稍候...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[!] 錯誤：找不到鏡頭！請檢查鏡頭是否連接，或嘗試將 VideoCapture(0) 改為 (1)")
        return

    game = RhythmGame()
    print("[*] 程式已執行，按下 'q' 鍵可退出遊戲")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("[!] 警告：無法接收鏡頭影像")
            break
        
        frame = cv2.flip(frame, 1) # 鏡像
        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = hands.process(rgb)
        
        finger_pos, gesture = None, None
        if res.multi_hand_landmarks:
            landmarks = res.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(frame, landmarks, mp_hands.HAND_CONNECTIONS)
            tip = landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            finger_pos = (int(tip.x * WIDTH), int(tip.y * HEIGHT))
            gesture = get_gesture_info(landmarks)

        game.update(frame, finger_pos, gesture)
        cv2.imshow("Gesture Game", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()