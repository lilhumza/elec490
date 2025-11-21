/*
  ----- pH Calibration Notes -----

  Assume a linear model:

      pH = phSlope * voltage + phOffset

  To find phSlope and phOffset:

  1. Upload and run the pH calibration sketch.
  2. Measure voltage in pH 7.00 buffer:
       V7 = <measured voltage at pH 7>
  3. Measure voltage in pH 4.00 buffer (or 10.00):
       V4 = <measured voltage at pH 4>

  Now compute:

      phSlope  = (pH2 - pH1) / (V2 - V1)
               = (4.00 - 7.00) / (V4 - V7)

      phOffset = pH1 - phSlope * V1
               = 7.00 - phSlope * V7

  Example (fake numbers!):
      V7 = 2.50 V at pH 7
      V4 = 3.00 V at pH 4

      phSlope  = (4.00 - 7.00) / (3.00 - 2.50)
               = -3.00 / 0.50
               = -6.0

      phOffset = 7.00 - (-6.0 * 2.50)
               = 7.00 + 15.0
               = 22.0

      So:
        phSlope  = -6.0
        phOffset = 22.0

  Then plug those into the variables below.
*/

const int PH_PIN = A0;

void setup() {
  Serial.begin(9600);
  delay(1000);

  Serial.println("=== pH Calibration Mode ===");
  Serial.println("Rinse probe, place in pH 7 buffer, wait for stable voltage.");
  Serial.println("Record voltage as V7.");
  Serial.println("Then place in pH 4 buffer, wait, and record voltage as V4.");
  Serial.println("--------------------------------------------------------");
}

void loop() {
  // Read raw analog value (0–1023)
  int rawValue = analogRead(PH_PIN);

  // Convert ADC reading to voltage (assuming 5.00V reference)
  float voltage = rawValue * (5.0 / 1023.0);

  Serial.print("Raw ADC: ");
  Serial.print(rawValue);
  Serial.print("  |  Voltage: ");
  Serial.print(voltage, 4);  // 4 decimal places for accuracy
  Serial.println(" V");

  delay(1000);   // 1 reading per second
}
