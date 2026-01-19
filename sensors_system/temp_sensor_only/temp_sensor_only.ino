#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 13  // DS18B20 data pin

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

bool headerPrinted = false;

// Optional temperature offset (°C).
// Default = 0.0 (no correction). Sensor does not need calibration according to spec.
// You can adjust after comparing against a reference thermometer.
float tempOffset = 0.0;

void setup() {
  Serial.begin(9600);
  sensors.begin();
}

void loop() {
  // Print CSV header once
  if (!headerPrinted) {
    Serial.println("time_ms,temp_c");
    headerPrinted = true;
  }

  // Request temperature conversion
  sensors.requestTemperatures();
  float tempC = sensors.getTempCByIndex(0);

  // Apply optional offset
  float correctedTemp = tempC + tempOffset;

  // Get timestamp (ms since Arduino start)
  unsigned long t = millis();

  // CSV line: time_ms,temp_c
  Serial.print(t);
  Serial.print(",");

  if (tempC == DEVICE_DISCONNECTED_C) {
    Serial.println("NaN");  // Output NaN if sensor fails
  } else {
    Serial.println(correctedTemp, 3);
  }

  delay(1000);  // 1 reading per second
}
