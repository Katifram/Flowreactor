#include <Arduino.h>
#include "command.h"
#include "motion.h"

void setup() {
  Serial.begin(115200);
  delay(500);

  motionSetup();
  commandSetup();

  Serial.println("BOOT");
}

void loop() {
  serviceSerial();
  serviceCommandExecutor();
  serviceMotion();
}