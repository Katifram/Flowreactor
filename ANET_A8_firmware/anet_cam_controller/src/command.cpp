#include "command.h"
#include "motion.h"

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
static const unsigned long DEFAULT_STEP_HALF_PERIOD_US = 1000;

static Command commandQueue[QUEUE_SIZE];
static uint8_t queueHead = 0;
static uint8_t queueTail = 0;
static uint8_t queueCount = 0;

static bool commandActive = false;
static Command activeCommand = {CMD_NONE, 0};
static bool stepCompletionReported = false;

static String lineBuffer;

static bool enqueueCommand(const Command& cmd) {
  if (queueCount >= QUEUE_SIZE) {
    return false;
  }

  commandQueue[queueTail] = cmd;
  queueTail = (queueTail + 1) % QUEUE_SIZE;
  queueCount++;
  return true;
}

static bool dequeueCommand(Command& cmd) {
  if (queueCount == 0) {
    return false;
  }

  cmd = commandQueue[queueHead];
  queueHead = (queueHead + 1) % QUEUE_SIZE;
  queueCount--;
  return true;
}

static void finishActiveCommand() {
  commandActive = false;
  activeCommand.type = CMD_NONE;
  activeCommand.value = 0;
  stepCompletionReported = false;
}

static void printStatus() {
  Serial.print("OK STATUS Q=");
  Serial.print(queueCount);
  Serial.print(" ACTIVE=");
  Serial.print(commandActive ? 1 : 0);
  Serial.print(" STEP_RUNNING=");
  Serial.print(motionIsStepRunning() ? 1 : 0);
  Serial.print(" STEPS_LEFT=");
  Serial.print(motionGetStepsRemaining());
  Serial.print(" CONT=");
  Serial.print(motionIsContinuousRunning() ? 1 : 0);
  Serial.print(" SPEED=");
  Serial.println(motionGetContinuousSpeed());
}

static Command parseCommand(const String& line) {
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

static void startCommand(const Command& cmd) {
  activeCommand = cmd;
  commandActive = true;

  switch (cmd.type) {
    case CMD_PING:
      Serial.println("PONG");
      finishActiveCommand();
      break;

    case CMD_ENABLE:
      motionEnable();
      Serial.println("OK ENABLE");
      finishActiveCommand();
      break;

    case CMD_DISABLE:
      motionDisable();
      Serial.println("OK DISABLE");
      finishActiveCommand();
      break;

    case CMD_DIR:
      motionSetDirection(cmd.value != 0);
      Serial.print("OK DIR ");
      Serial.println(cmd.value);
      finishActiveCommand();
      break;

    case CMD_STATUS:
      printStatus();
      finishActiveCommand();
      break;

    case CMD_STOP:
      motionStopContinuous();
      Serial.println("OK STOP");
      finishActiveCommand();
      break;

    case CMD_SET_SPEED: {
      if (motionIsStepRunning()) {
        Serial.println("ERR STEP_ACTIVE");
        finishActiveCommand();
        break;
      }

      if (cmd.value == 0) {
        motionStopContinuous();
        Serial.println("OK SPEED 0");
        finishActiveCommand();
        break;
      }

      unsigned long halfPeriodUs = 0;
      if (!motionSpeedToHalfPeriodUs((unsigned long)cmd.value, halfPeriodUs)) {
        Serial.println("ERR BAD_SPEED");
        finishActiveCommand();
        break;
      }

      motionStartContinuous((unsigned long)cmd.value, halfPeriodUs);
      Serial.print("OK SPEED ");
      Serial.println(cmd.value);
      finishActiveCommand();
      break;
    }

    case CMD_STEP:
      if (motionIsContinuousRunning()) {
        Serial.println("ERR STOP_REQUIRED");
        finishActiveCommand();
        break;
      }

      if (!motionStartStepMove((unsigned long)cmd.value, DEFAULT_STEP_HALF_PERIOD_US)) {
        Serial.println("ERR STEP_START");
        finishActiveCommand();
        break;
      }

      Serial.print("OK STEP START ");
      Serial.println(cmd.value);
      stepCompletionReported = false;
      break;

    default:
      Serial.println("ERR BAD_CMD");
      finishActiveCommand();
      break;
  }
}

void commandSetup() {
  lineBuffer.reserve(64);
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

void serviceCommandExecutor() {
  if (commandActive) {
    if (activeCommand.type == CMD_STEP) {
      if (!motionIsStepRunning()) {
        if (!stepCompletionReported) {
          Serial.println("OK STEP DONE");
          stepCompletionReported = true;
        }
        finishActiveCommand();
      }
    }
    return;
  }

  Command nextCmd;
  if (dequeueCommand(nextCmd)) {
    startCommand(nextCmd);
  }
}