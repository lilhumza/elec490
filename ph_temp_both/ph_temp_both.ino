#include <OneWire.h>
#include <DallasTemperature.h>

// ----- Pin assignments -----
#define ONE_WIRE_BUS 13    // DS18B20 data pin
const int PH_PIN = A0;     // Gravity pH sensor analog output

// ----- OneWire + DS18B20 objects -----
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);

// ----- Temperature offset - NOT NEEDED -----
// Default = 0.0 (no correction).
float tempOffset = 0.0;

// ----- pH calibration parameters -----
// Use calibration across buffer solution to retrieve values.
float phSlope  = 3.5;   // pH per volt (example rough value)
float phOffset = 0.0;   // pH offset

bool headerPrinted = false;

void setup() {
  Serial.begin(9600);
  delay(1000); // allow Serial to come up

  tempSensor.begin();
  pinMode(PH_PIN, INPUT);
}

void loop() {
  // Print CSV header once
  if (!headerPrinted) {
    Serial.println("time_ms,temp_c,ph,ph_voltage");
    headerPrinted = true;
  }

  // ----- Timestamp -----
  unsigned long t = millis();

  // ----- Read temperature (DS18B20) -----
  tempSensor.requestTemperatures();           // blocking read, ~750ms at 12-bit
  float rawTempC = tempSensor.getTempCByIndex(0);
  float correctedTempC = rawTempC + tempOffset;

  // ----- Read pH (analog) -----
  int phRaw = analogRead(PH_PIN);            // 0–1023
  float phVoltage = phRaw * (5.0 / 1023.0);  // assuming 5V reference
  float phValue = phSlope * phVoltage + phOffset;

  // ----- CSV output: time_ms,temp_c,ph,ph_voltage -----
  Serial.print(t);
  Serial.print(",");

  // Temp (handle DS18B20 disconnect)
  if (rawTempC == DEVICE_DISCONNECTED_C) {
    Serial.print("NaN");
  } else {
    Serial.print(correctedTempC, 3);
  }
  Serial.print(",");

  // pH and voltage
  Serial.print(phValue, 3);
  Serial.print(",");
  Serial.println(phVoltage, 4);

  // 1 reading per second
  delay(1000);
}
