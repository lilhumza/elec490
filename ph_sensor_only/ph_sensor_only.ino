// Gravity Analog pH Sensor on Arduino Uno
// Signal connected to analog pin A0

const int PH_PIN = A0;

// Calibration parameters for pH calculation.
float phSlope  = 3.5;   // pH per volt (example rough value)
float phOffset = 0.0;   // pH offset (example, tweak after calibration)

bool headerPrinted = false;

void setup() {
  Serial.begin(9600);
  delay(1000); // give Serial a moment

  // If you want, you can print a small comment line here
  // but keep actual data as CSV only.
  // Serial.println("# Gravity pH Sensor CSV Output");

  pinMode(PH_PIN, INPUT);
}

void loop() {
  // Print CSV header once
  if (!headerPrinted) {
    Serial.println("time_ms,ph,voltage");
    headerPrinted = true;
  }

  // Read raw analog value (0–1023)
  int phRaw = analogRead(PH_PIN);

  // Convert ADC value to voltage (assuming 5V reference)
  float voltage = phRaw * (5.0 / 1023.0);

  // Compute pH (very rough until calibrated)
  float phValue = phSlope * voltage + phOffset;

  // Timestamp in ms since reset
  unsigned long t = millis();

  // CSV line: time_ms,ph,voltage
  Serial.print(t);
  Serial.print(",");
  Serial.print(phValue, 3);   // pH to 3 decimal places
  Serial.print(",");
  Serial.println(voltage, 4); // voltage to 4 decimal places

  delay(1000);  // 1 reading per second
}
