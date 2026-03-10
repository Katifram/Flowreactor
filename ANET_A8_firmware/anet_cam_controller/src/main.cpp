#include <Arduino.h>

// ANET A8 / ATmega1284P X-axis pins from your working tests
#define X_STEP_PIN    15   // D7
#define X_DIR_PIN     21   // C5
#define X_ENABLE_PIN  14   // D6, active LOW

// ------------------------------
// Command system
// ------------------------------

enum CommandType {
  CMD_NONE,
  CMD_PING,
  CMD_ENABLE,
  CMD_DISABLE,
  CMD_DIR,
  CMD_STEP,
  CMD_SET_SPEED,
  CMD_STOP,
  CMD_STATUS
};

struct Command {
  CommandType type;
  long value;
};

static const uint8_t QUEUE_SIZE = 8;
Command commandQueue[QUEUE_SIZE];
uint8_t queueHead = 0;
uint8_t queueTail = 0;
uint8_t queueCount = 0;

bool enqueueCommand(const Command& cmd) {
  if (queueCount >= QUEUE_SIZE) {
    return false;
  }
  commandQueue[queueTail] = cmd;
  queueTail = (queueTail + 1) % QUEUE_SIZE;
  queueCount++;
  return true;
}

bool dequeueCommand(Command& cmd) {
  if (queueCount == 0) {
    return false;
  }
  cmd = commandQueue[queueHead];
  queueHead = (queueHead + 1) % QUEUE_SIZE;
  queueCount--;
  return true;
}

// ------------------------------
// Motion state
// ------------------------------

bool commandActive = false;
Command activeCommand = {CMD_NONE, 0};

// finite STEP command state
bool stepCommandRunning = false;
bool stepStateHigh = false;
unsigned long stepsRemaining = 0;
unsigned long lastStepMicros = 0;
unsigned long activeHalfPeriodUs = 1000;   // used by active STEP command

// continuous speed mode state
bool continuousMode = false;
bool continuousStepStateHigh = false;
unsigned long continuousLastStepMicros = 0;
unsigned long continuousHalfPeriodUs = 0;
unsigned long continuousSpeedStepsPerSec = 0;

// safe limits
const unsigned long DEFAULT_STEP_HALF_PERIOD_US = 1000;  // for STEP n
const unsigned long MIN_SPEED_STEPS_PER_SEC = 1;
const unsigned long MAX_SPEED_STEPS_PER_SEC = 3000;

// ------------------------------
// Serial input buffer
// ------------------------------

String lineBuffer;

// ------------------------------
// Helpers
// ------------------------------

void printStatus() {
  Serial.print("OK STATUS Q=");
  Serial.print(queueCount);
  Serial.print(" ACTIVE=");
  Serial.print(commandActive ? 1 : 0);
  Serial.print(" STEP_RUNNING=");
  Serial.print(stepCommandRunning ? 1 : 0);
  Serial.print(" STEPS_LEFT=");
  Serial.print(stepsRemaining);
  Serial.print(" CONT=");
  Serial.print(continuousMode ? 1 : 0);
  Serial.print(" SPEED=");
  Serial.println(continuousSpeedStepsPerSec);
}

bool speedToHalfPeriodUs(unsigned long speedStepsPerSec, unsigned long& halfPeriodUsOut) {
  if (speedStepsPerSec < MIN_SPEED_STEPS_PER_SEC || speedStepsPerSec > MAX_SPEED_STEPS_PER_SEC) {
    return false;
  }

  // one full step = HIGH + LOW
  // full period us = 1,000,000 / steps_per_sec
  // half period us = 500,000 / steps_per_sec
  unsigned long hp = 500000UL / speedStepsPerSec;

  if (hp == 0) {
    hp = 1;
  }

  halfPeriodUsOut = hp;
  return true;
}

Command parseCommand(const String& line) {
  Command cmd;
  cmd.type = CMD_NONE;
  cmd.value = 0;

  if (line == "PING") {
    cmd.type = CMD_PING;
  }
  else if (line == "ENABLE") {
    cmd.type = CMD_ENABLE;
  }
  else if (line == "DISABLE") {
    cmd.type = CMD_DISABLE;
  }
  else if (line == "DIR 0") {
    cmd.type = CMD_DIR;
    cmd.value = 0;
  }
  else if (line == "DIR 1") {
    cmd.type = CMD_DIR;
    cmd.value = 1;
  }
  else if (line == "STOP") {
    cmd.type = CMD_STOP;
  }
  else if (line == "STATUS") {
    cmd.type = CMD_STATUS;
  }
  else if (line.startsWith("STEP ")) {
    long steps = line.substring(5).toInt();
    if (steps > 0) {
      cmd.type = CMD_STEP;
      cmd.value = steps;
    }
  }
  else if (line.startsWith("SET_SPEED ")) {
    long speed = line.substring(10).toInt();
    if (speed >= 0) {
      cmd.type = CMD_SET_SPEED;
      cmd.value = speed;
    }
  }

  return cmd;
}

void finishActiveCommand() {
  commandActive = false;
  activeCommand.type = CMD_NONE;
  activeCommand.value = 0;
}

void startStepCommand(unsigned long steps, unsigned long halfPeriodUs) {
  stepsRemaining = steps;
  stepStateHigh = false;
  stepCommandRunning = true;
  activeHalfPeriodUs = halfPeriodUs;
  lastStepMicros = micros();
  digitalWrite(X_STEP_PIN, LOW);
}

void stopContinuousMode() {
  continuousMode = false;
  continuousSpeedStepsPerSec = 0;
  continuousHalfPeriodUs = 0;
  continuousStepStateHigh = false;
  digitalWrite(X_STEP_PIN, LOW);
}

void startContinuousMode(unsigned long speedStepsPerSec, unsigned long halfPeriodUs) {
  continuousMode = true;
  continuousSpeedStepsPerSec = speedStepsPerSec;
  continuousHalfPeriodUs = halfPeriodUs;
  continuousStepStateHigh = false;
  continuousLastStepMicros = micros();
  digitalWrite(X_STEP_PIN, LOW);
}

void serviceStepCommand() {
  if (!stepCommandRunning) {
    return;
  }

  unsigned long now = micros();
  if (now - lastStepMicros < activeHalfPeriodUs) {
    return;
  }

  lastStepMicros = now;

  if (!stepStateHigh) {
    digitalWrite(X_STEP_PIN, HIGH);
    stepStateHigh = true;
  } else {
    digitalWrite(X_STEP_PIN, LOW);
    stepStateHigh = false;

    if (stepsRemaining > 0) {
      stepsRemaining--;
    }

    if (stepsRemaining == 0) {
      stepCommandRunning = false;
      Serial.println("OK STEP DONE");
      finishActiveCommand();
    }
  }
}

void serviceContinuousMode() {
  if (!continuousMode || continuousHalfPeriodUs == 0) {
    return;
  }

  unsigned long now = micros();
  if (now - continuousLastStepMicros < continuousHalfPeriodUs) {
    return;
  }

  continuousLastStepMicros = now;

  if (!continuousStepStateHigh) {
    digitalWrite(X_STEP_PIN, HIGH);
    continuousStepStateHigh = true;
  } else {
    digitalWrite(X_STEP_PIN, LOW);
    continuousStepStateHigh = false;
  }
}

void startCommand(const Command& cmd) {
  activeCommand = cmd;
  commandActive = true;

  switch (cmd.type) {
    case CMD_PING:
      Serial.println("PONG");
      finishActiveCommand();
      break;

    case CMD_ENABLE:
      digitalWrite(X_ENABLE_PIN, LOW);
      Serial.println("OK ENABLE");
      finishActiveCommand();
      break;

    case CMD_DISABLE:
      stopContinuousMode();
      digitalWrite(X_ENABLE_PIN, HIGH);
      Serial.println("OK DISABLE");
      finishActiveCommand();
      break;

    case CMD_DIR:
      digitalWrite(X_DIR_PIN, cmd.value ? HIGH : LOW);
      Serial.print("OK DIR ");
      Serial.println(cmd.value);
      finishActiveCommand();
      break;

    case CMD_STATUS:
      printStatus();
      finishActiveCommand();
      break;

    case CMD_STOP:
      stopContinuousMode();
      Serial.println("OK STOP");
      finishActiveCommand();
      break;

    case CMD_SET_SPEED: {
      if (stepCommandRunning) {
        Serial.println("ERR STEP_ACTIVE");
        finishActiveCommand();
        break;
      }

      if (cmd.value == 0) {
        stopContinuousMode();
        Serial.println("OK SPEED 0");
        finishActiveCommand();
        break;
      }

      unsigned long halfPeriodUs = 0;
      if (!speedToHalfPeriodUs((unsigned long)cmd.value, halfPeriodUs)) {
        Serial.println("ERR BAD_SPEED");
        finishActiveCommand();
        break;
      }

      startContinuousMode((unsigned long)cmd.value, halfPeriodUs);
      Serial.print("OK SPEED ");
      Serial.println(cmd.value);
      finishActiveCommand();
      break;
    }

    case CMD_STEP:
      if (continuousMode) {
        Serial.println("ERR STOP_REQUIRED");
        finishActiveCommand();
        break;
      }

      Serial.print("OK STEP START ");
      Serial.println(cmd.value);
      startStepCommand((unsigned long)cmd.value, DEFAULT_STEP_HALF_PERIOD_US);
      break;

    default:
      Serial.println("ERR BAD_CMD");
      finishActiveCommand();
      break;
  }
}

void serviceCommandExecutor() {
  if (commandActive) {
    if (activeCommand.type == CMD_STEP) {
      serviceStepCommand();
    }
    return;
  }

  Command nextCmd;
  if (dequeueCommand(nextCmd)) {
    startCommand(nextCmd);
  }
}

void serviceSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();

    if (c == '\n' || c == '\r') {
      if (lineBuffer.length() > 0) {
        Command cmd = parseCommand(lineBuffer);

        if (cmd.type == CMD_NONE) {
          Serial.print("ERR UNKNOWN ");
          Serial.println(lineBuffer);
        } else {
          if (enqueueCommand(cmd)) {
            Serial.print("OK QUEUED ");
            Serial.println(lineBuffer);
          } else {
            Serial.println("ERR QUEUE_FULL");
          }
        }

        lineBuffer = "";
      }
    } else {
      lineBuffer += c;
    }
  }
}

// ------------------------------
// Arduino setup/loop
// ------------------------------

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_DIR_PIN, OUTPUT);
  pinMode(X_ENABLE_PIN, OUTPUT);

  digitalWrite(X_STEP_PIN, LOW);
  digitalWrite(X_DIR_PIN, LOW);
  digitalWrite(X_ENABLE_PIN, HIGH); // disabled initially

  Serial.println("BOOT");
}

void loop() {
  serviceSerial();
  serviceCommandExecutor();

  // continuous mode runs whenever no finite STEP command is active
  if (!stepCommandRunning) {
    serviceContinuousMode();
  }
}