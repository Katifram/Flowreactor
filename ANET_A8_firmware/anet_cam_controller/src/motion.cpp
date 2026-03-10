#include "motion.h"
#include "pins.h"

// finite STEP command state
static bool stepCommandRunning = false;
static bool stepStateHigh = false;
static unsigned long stepsRemaining = 0;
static unsigned long lastStepMicros = 0;
static unsigned long activeHalfPeriodUs = 1000;

// continuous speed mode state
static bool continuousMode = false;
static bool continuousStepStateHigh = false;
static unsigned long continuousLastStepMicros = 0;
static unsigned long continuousHalfPeriodUs = 0;
static unsigned long continuousSpeedStepsPerSec = 0;

// safe limits
static const unsigned long MIN_SPEED_STEPS_PER_SEC = 1;
static const unsigned long MAX_SPEED_STEPS_PER_SEC = 3000;

void motionSetup() {
  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_DIR_PIN, OUTPUT);
  pinMode(X_ENABLE_PIN, OUTPUT);

  digitalWrite(X_STEP_PIN, LOW);
  digitalWrite(X_DIR_PIN, LOW);
  digitalWrite(X_ENABLE_PIN, HIGH); // disabled initially
}

void motionEnable() {
  digitalWrite(X_ENABLE_PIN, LOW);
}

void motionDisable() {
  motionStopContinuous();
  digitalWrite(X_ENABLE_PIN, HIGH);
}

void motionSetDirection(bool dirHigh) {
  digitalWrite(X_DIR_PIN, dirHigh ? HIGH : LOW);
}

bool motionStartStepMove(unsigned long steps, unsigned long halfPeriodUs) {
  if (continuousMode || stepCommandRunning || steps == 0 || halfPeriodUs == 0) {
    return false;
  }

  stepsRemaining = steps;
  stepStateHigh = false;
  stepCommandRunning = true;
  activeHalfPeriodUs = halfPeriodUs;
  lastStepMicros = micros();
  digitalWrite(X_STEP_PIN, LOW);

  return true;
}

void motionStartContinuous(unsigned long speedStepsPerSec, unsigned long halfPeriodUs) {
  continuousMode = true;
  continuousSpeedStepsPerSec = speedStepsPerSec;
  continuousHalfPeriodUs = halfPeriodUs;
  continuousStepStateHigh = false;
  continuousLastStepMicros = micros();
  digitalWrite(X_STEP_PIN, LOW);
}

void motionStopContinuous() {
  continuousMode = false;
  continuousSpeedStepsPerSec = 0;
  continuousHalfPeriodUs = 0;
  continuousStepStateHigh = false;
  digitalWrite(X_STEP_PIN, LOW);
}

bool motionIsStepRunning() {
  return stepCommandRunning;
}

bool motionIsContinuousRunning() {
  return continuousMode;
}

unsigned long motionGetStepsRemaining() {
  return stepsRemaining;
}

unsigned long motionGetContinuousSpeed() {
  return continuousSpeedStepsPerSec;
}

bool motionSpeedToHalfPeriodUs(unsigned long speedStepsPerSec, unsigned long& halfPeriodUsOut) {
  if (speedStepsPerSec < MIN_SPEED_STEPS_PER_SEC || speedStepsPerSec > MAX_SPEED_STEPS_PER_SEC) {
    return false;
  }

  unsigned long hp = 500000UL / speedStepsPerSec;
  if (hp == 0) {
    hp = 1;
  }

  halfPeriodUsOut = hp;
  return true;
}

static void serviceStepMove() {
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
    }
  }
}

static void serviceContinuousMode() {
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

void serviceMotion() {
  if (stepCommandRunning) {
    serviceStepMove();
  } else {
    serviceContinuousMode();
  }
}