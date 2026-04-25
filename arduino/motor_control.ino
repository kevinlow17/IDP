// =========================
// Motor & Ultrasonic Pins
// =========================
int IN1 = 3;
int IN2 = 4;
int IN3 = 12;
int IN4 = 13;

int ENA = 5;
int ENB = 6;

const int TRIG_PIN = 9;
const int ECHO_PIN = 10;
const int STOP_DISTANCE = 10;

// =========================
// Serial Input
// =========================
String input = "";

int leftSpeed  = 0;
int rightSpeed = 0;

const int DEADZONE = 90;  // Deadzone Compensation

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

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  moveMotor(0, 0);
}

// =========================
// Main Loop
// =========================
void loop() {

  // =========================
  // Read Serial from Raspberry Pi
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
  // Ultrasonic
  // =========================
  float distance = getDistance();

  if (distance < STOP_DISTANCE) {
    moveMotor(0, 0);
  } else {
    moveMotor(leftSpeed, rightSpeed);
  }
  delay(10);
}

// =========================
// Deadzone Compensation
// =========================
int applyDeadzone(int speed) {
  if (speed == 0)                     return 0;
  if (speed > 0 && speed < DEADZONE)  return DEADZONE;
  if (speed < 0 && speed > -DEADZONE) return -DEADZONE;
  return speed;
}

// =========================
// Ultrasonic
// =========================
float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) return 999;

  float distance = duration * 0.034 / 2.0;
  return distance;
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
