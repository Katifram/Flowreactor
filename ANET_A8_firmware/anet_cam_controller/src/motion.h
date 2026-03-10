#pragma once

#include <Arduino.h>

void motionSetup();

void motionEnable();
void motionDisable();
void motionSetDirection(bool dirHigh);

bool motionStartStepMove(unsigned long steps, unsigned long halfPeriodUs);
void motionStartContinuous(unsigned long speedStepsPerSec, unsigned long halfPeriodUs);
void motionStopContinuous();

bool motionIsStepRunning();
bool motionIsContinuousRunning();

unsigned long motionGetStepsRemaining();
unsigned long motionGetContinuousSpeed();

bool motionSpeedToHalfPeriodUs(unsigned long speedStepsPerSec, unsigned long& halfPeriodUsOut);

void serviceMotion();