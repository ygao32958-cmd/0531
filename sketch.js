let handPose;
let hands = [];
let video;
let videoFlipped;

// 遊戲狀態
let state = "MENU"; // MENU, GAME
let score = 0;
let combo = 0;
let currentTarget = "UP";
let directions = ["UP", "DOWN", "LEFT", "RIGHT"];

// 中文方向映射（用於文字顯示）
const directionMap = {
  "UP": "向上 ↑",
  "DOWN": "向下 ↓",
  "LEFT": "← 向左",
  "RIGHT": "向右 →"
};

// 視覺資源
let particles = [];
let uiPulse = 0;
let hitShake = 0;
let bgColor;
let accentColor;
let comboScale = 1;

// 音樂與節奏 (網頁版建議手動設定 BPM)
let song;
let bpm = 120;
let beatInterval; // 毫秒
let lastBeatTime = 0;
let hitWindow = 250; // 判定範圍 (毫秒)

// 選單變數
let hoverStartTime = 0;
let hoverIndex = -1;
function setup() {
  createCanvas(windowWidth, windowHeight);
  bgColor = color(10, 10, 25);
  accentColor = color(0, 255, 255);
  
  // 確保文字與繪圖模式一致
  textAlign(CENTER, CENTER);
  rectMode(CORNER);

  // 使用 flipped: true 讓鏡頭自動鏡像
  video = createCapture(VIDEO, { flipped: true });
  video.size(640, 480);
  video.hide();
  beatInterval = (60 / bpm) * 1000;
  // 啟動 ml5 手勢偵測
  handPose.detectStart(video, gotHands);
}

function preload() {
  // 初始化 ml5 HandPose 模型
  handPose = ml5.handPose({ flipped: true });
}

function gotHands(results) {
  hands = results;
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
}

function draw() {
  background(bgColor);
  
  // 隨節奏計算 UI 縮放
  uiPulse = lerp(uiPulse, 1, 0.1);
  if (millis() % floor(beatInterval) < 50) uiPulse = 1.15;

  // 處理畫面震動
  if (hitShake > 0) {
    translate(random(-hitShake, hitShake), random(-hitShake, hitShake));
    hitShake *= 0.8;
  }

  // 計算全螢幕影片縮放比例
  let vW = width, vH = (video.height / video.width) * width;
  if (vH < height) {
    vH = height;
    vW = (video.width / video.height) * height;
  }

  push();
  image(video, (width - vW) / 2, (height - vH) / 2, vW, vH);
  pop();

  background(0, 180);
  drawBackgroundDecor();

  let fingerPos = null;
  let gesture = null;
  if (hands.length > 0) {
    let hand = hands[0];
    if (hand.confidence > 0.1) {
      // 將 ml5 偵測座標映射到畫布大小
      let scaleFactor = vW / video.width;
      let xOffset = (width - vW) / 2;
      let yOffset = (height - vH) / 2;
      
      let tip = hand.keypoints[8]; // 食指尖
      fingerPos = { x: tip.x * scaleFactor + xOffset, y: tip.y * scaleFactor + yOffset };
      gesture = getGesture(hand);
      
      // 畫出指尖發光點
      drawCursor(fingerPos.x, fingerPos.y);
    }
  }

  if (state === "MENU") {
    drawMenu(fingerPos);
  } else if (state === "GAME") {
    drawGame(gesture);
  }
}
/**
 * 改進後的手勢判定
 */
function getGesture(hand) {
  let k = hand.keypoints;
  let tip = k[8];  // 食指尖
  let mcp = k[5];  // 食指根
  
  // 只要指尖跟根部有足夠距離就判定
  let d = dist(tip.x, tip.y, mcp.x, mcp.y);
  if (d > 30) { 
    let dx = tip.x - mcp.x;
    let dy = tip.y - mcp.y;
    
    // 判斷哪個位移量較大
    if (Math.abs(dx) > Math.abs(dy)) {
      return dx < 0 ? "LEFT" : "RIGHT";
    } else {
      return dy < 0 ? "UP" : "DOWN";
    }
  }
  return null;
}

function drawMenu(fingerPos) {
  // 標題發光
  push();
  drawingContext.shadowBlur = 20;
  drawingContext.shadowColor = accentColor;
  fill(255);
  textSize(width * 0.04 * uiPulse);
  textFont('Arial Black');
  text("手勢節奏遊戲", width / 2, height * 0.15);
  textSize(18);
  text("RHYTHM FINGER MASTER", width / 2, height * 0.2);
  pop();

  let songs = ["電音節奏 (120 BPM)", "流行舞曲 (128 BPM)"];
  let w = width * 0.5;
  let h = 80;
  let x = width / 2 - w / 2;

  for (let i = 0; i < songs.length; i++) {
    let y = height * 0.35 + i * 120;
    let isHover = fingerPos && fingerPos.x > x && fingerPos.x < x + w && fingerPos.y > y && fingerPos.y < y + h;
    
    push();
    if (isHover) {
      drawingContext.shadowBlur = 15;
      drawingContext.shadowColor = color(0, 255, 0);
    }
    fill(isHover ? "rgba(0, 255, 255, 0.5)" : "rgba(255, 255, 255, 0.2)");
    stroke(isHover ? 255 : 100);
    strokeWeight(isHover ? 3 : 1);
    rect(x, y, w, h, 20);
    
    fill(255);
    noStroke();
    textSize(24);
    text(songs[i], x + w / 2, y + h / 2);
    pop();

    if (isHover) {
      if (hoverIndex !== i) {
        hoverIndex = i;
        hoverStartTime = millis();
      }
      let prog = (millis() - hoverStartTime) / 1500;
      fill(0, 255, 127);
      rect(x + 10, y + h - 15, (w - 20) * Math.min(prog, 1), 5, 5);
      if (prog >= 1) startGame();
    } else if (hoverIndex === i) {
      hoverIndex = -1;
    }
  }
}
function startGame() {
  state = "GAME";
  score = 0;
  combo = 0;
  lastBeatTime = millis();
}

function drawGame(gesture) {
  let currentTime = millis();
  let timeSinceLastBeat = currentTime - lastBeatTime;

  // 節奏判定
  if (timeSinceLastBeat > beatInterval + hitWindow) {
    lastBeatTime += beatInterval;
    currentTarget = random(directions);
    combo = 0;
    showFeedback("漏拍 (MISS)", color(255, 0, 0));
  }

  // 當手勢正確且在窗口內
  if (gesture === currentTarget && timeSinceLastBeat < hitWindow) {
    // Hit!
    score += 10 + Math.floor(combo / 5);
    combo++;
    // 重置節拍點並更新目標
    lastBeatTime = currentTime;
    currentTarget = random(directions);
    showFeedback("完美 (PERFECT)!", color(0, 255, 0));
    hitShake = 10;
  }

  // UI 顯示
  fill(255);
  textSize(28);
  textAlign(LEFT, TOP);
  text(`總分: ${score}`, 30, 30);
  text(`連擊: ${combo}`, 30, 70);
  textAlign(CENTER, CENTER);

  // 指令箭頭
  drawArrow(width / 2, height / 2, currentTarget);
  
  // 節奏收縮圈
  noFill();
  stroke(255, 150);
  strokeWeight(2);
  let r = map(timeSinceLastBeat, 0, beatInterval, width * 0.25, 20);
  if (r > 20) circle(width / 2, height / 2, r);
}

function drawArrow(x, y, dir) {
  push();
  translate(x, y);
  if (dir === "DOWN") rotate(PI);
  if (dir === "LEFT") rotate(-HALF_PI);
  if (dir === "RIGHT") rotate(HALF_PI);

  scale(uiPulse);
  drawingContext.shadowBlur = 25;
  drawingContext.shadowColor = accentColor;

  fill(255);
  noStroke();
  triangle(0, -60, -40, -10, 40, -10);
  rect(-15, -10, 30, 50, 5);
  pop();
}
function drawBackgroundDecor() {
  stroke(255, 20);
  strokeWeight(1);
  for (let i = 0; i < width; i += width / 15) line(i, 0, i, height);
  for (let i = 0; i < height; i += height / 15) line(0, i, width, i);
}

function drawCursor(x, y) {
  noFill();
  stroke(0, 255, 255, 200);
  strokeWeight(2);
  circle(x, y, 30 + sin(frameCount * 0.2) * 5);
  fill(0, 255, 255, 100);
  circle(x, y, 10);
}

let feedbackText = "";
let feedbackColor;
let feedbackAlpha = 0;

function showFeedback(txt, col) {
  feedbackText = txt;
  feedbackColor = col;
  feedbackAlpha = 255;
}

function drawFeedback() {
  if (feedbackAlpha > 0) {
    fill(red(feedbackColor), green(feedbackColor), blue(feedbackColor), feedbackAlpha);
    textSize(45);
    text(feedbackText, width / 2, height / 2 + 150);
    feedbackAlpha -= 5;
  }
}
