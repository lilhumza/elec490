# PH and Temp Sensors Subsystem Code

This project provides four Arduino sketches for reading:

- A **DS18B20 waterproof temperature sensor**
- A **Gravity analog pH sensor**
- Both sensors together in one synchronized CSV stream
- A dedicated **pH calibration mode**

All sketches run on an **Arduino Uno** at **9600 baud**, streaming data to USB serial once per second.

---

## 📦 Sketch Summary

### **1. `temp_sensor_only.ino`**
Reads the **DS18B20** on digital pin **13** and outputs temperature once per second in CSV format.

### **2. `ph_sensor_only.ino`**
Reads the **Gravity Analog pH Sensor** on **A0** and outputs voltage and (optionally) computed pH.

### **3. `ph_temp_both.ino`**
Reads **both sensors** once per second and prints a unified CSV line:

```
time_ms,temp_c,ph,ph_voltage
```

### **4. `ph_calibration.ino`**
Used to obtain accurate calibration constants (`phSlope` and `phOffset`).  
Prints raw ADC and voltage values while probe is placed in known buffer solutions.

---

## 🔌 Hardware & Pinout Details

### **DS18B20 Temperature Sensor**
A breakout board version is used, which **already includes the required 4.7kΩ pull-up resistor**.  
No additional components are needed.

| DS18B20 Pin | Arduino Uno |
|-------------|-------------|
| VCC         | 5V          |
| GND         | GND         |
| DATA        | **D13**     |

---

### **Gravity Analog pH Sensor**

| Gravity pH Board | Arduino Uno |
|------------------|-------------|
| V+               | 5V          |
| GND              | GND         |
| Po (Signal Out)  | **A0**      |

Ensure that **all grounds are common** between sensors and the Arduino.

---

## ⏱ Sampling Rate & Serial Output

All sketches send **one reading per second** using:

```cpp
delay(1000);
```

All output is streamed as **CSV over serial** at:

- **9600 baud**
- Simple comma-separated values
- Only one header line printed once

Example combined output:

```
time_ms,temp_c,ph,ph_voltage
1012,22.375,6.512,2.3112
2014,22.406,6.498,2.3109
```

This format is compatible with:

- Python data ingestion (pyserial)
- CSV loggers
- Node-RED
- Grafana/InfluxDB pipelines
- Custom dashboards

---

## 🎯 pH Calibration Overview

The pH sensor behaves approximately linearly:

```
pH = phSlope * voltage + phOffset
```

To compute calibration constants:

1. Run **`ph_calibration.ino`**
2. Place the probe into **pH 7.00 buffer** → measure `V7`
3. Place the probe into **pH 4.00 buffer** (or pH 10.00) → measure `V4`
4. Compute:

```
phSlope  = (pH2 - pH1) / (V2 - V1)
phOffset = pH1 - phSlope * V1
```

Example (fake numbers):

```
V7 = 2.50 V
V4 = 3.00 V

phSlope  = (4 - 7) / (3.00 - 2.50) = -6.0
phOffset = 7 - (-6.0 × 2.50) = 22.0
```

Then place those values into:

```cpp
float phSlope  = <your_value>;
float phOffset = <your_value>;
```

inside the pH-enabled sketches.

---


