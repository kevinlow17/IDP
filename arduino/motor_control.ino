// =========================
// Motor Pins
// =========================
int IN1 = 3;
int IN2 = 4;
int IN3 = 12;
int IN4 = 13;

int ENA = 5;
int ENB = 6;

// =========================
// ⭐ Ultrasonic Pins
// =========================
const int TRIG_PIN = 9;
const int ECHO_PIN = 10;
const int STOP_DISTANCE = 10;  // 停止距离（cm），可调

// =========================
// Serial Input
// =========================
String input = "";

int leftSpeed  = 0;
int rightSpeed = 0;

// 死区补偿
const int DEADZONE = 90;

// =========================
// Setup
// =========================
void setup() {
  Serial.begin(9600);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);

  // ⭐ 超声波引脚
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  moveMotor(0, 0);
}

// =========================
// ⭐ 超声波测距函数
// =========================
float getDistance() {
  // 发送触发信号
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // 读取回声时间（最多等30ms，避免卡住）
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) return 999;  // 没有回声 = 没有障碍物

  float distance = duration * 0.034 / 2.0;
  return distance;
}

// =========================
// Main Loop
// =========================
void loop() {

  // =========================
  // 1. 读取 Serial（格式：L,R）
  // =========================
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      int commaIndex = input.indexOf(',');
      if (commaIndex > 0) {
        leftSpeed  = input.substring(0, commaIndex).toInt();
        rightSpeed = input.substring(commaIndex + 1).toInt();
      }
      input = "";
    } else {
      input += c;
    }
  }

  // =========================
  // ⭐ 2. 超声波检测
  // =========================
  float distance = getDistance();

  if (distance < STOP_DISTANCE) {
    // 障碍物太近，强制停止
    moveMotor(0, 0);
  } else {
    // 正常执行来自树莓派的指令
    moveMotor(leftSpeed, rightSpeed);
  }

  delay(10);
}

// =========================
// 死区补偿
// =========================
int applyDeadzone(int speed) {
  if (speed == 0)                     return 0;
  if (speed > 0 && speed < DEADZONE)  return DEADZONE;
  if (speed < 0 && speed > -DEADZONE) return -DEADZONE;
  return speed;
}

// =========================
// Motor Control
// =========================
void moveMotor(int left, int right) {

  left  = constrain(left,  -255, 255);
  right = constrain(right, -255, 255);

  left  = applyDeadzone(left);
  right = applyDeadzone(right);

  // LEFT MOTOR
  if (left > 0) {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
    analogWrite(ENA, left);
  }
  else if (left < 0) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    analogWrite(ENA, -left);
  }
  else {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    analogWrite(ENA, 0);
  }

  // RIGHT MOTOR
  if (right > 0) {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
    analogWrite(ENB, right);
  }
  else if (right < 0) {
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
    analogWrite(ENB, -right);
  }
  else {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);
    analogWrite(ENB, 0);
  }
}

