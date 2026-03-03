// ============================================================================
// Arduino Dashboard Backend Server
// Real-time serial data to WebSocket streaming
// ============================================================================

const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { SerialPort } = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');
const path = require('path');

// Load environment variables
require('dotenv').config();

// Configuration
const CONFIG = {
  HTTP_PORT: process.env.PORT || 3000,
  WS_PORT: process.env.WS_PORT || 3001,
  SERIAL_PORT: process.env.SERIAL_PORT || '/dev/ttyACM0',
  SERIAL_BAUD_RATE: parseInt(process.env.SERIAL_BAUD_RATE || '9600'),
  NODE_ENV: process.env.NODE_ENV || 'development'
};

console.log('⚙️  Configuration loaded:');
console.log(`   HTTP Port: ${CONFIG.HTTP_PORT}`);
console.log(`   WebSocket Port: ${CONFIG.WS_PORT}`);
console.log(`   Serial Port: ${CONFIG.SERIAL_PORT}`);
console.log(`   Baud Rate: ${CONFIG.SERIAL_BAUD_RATE}`);
console.log(`   Environment: ${CONFIG.NODE_ENV}\n`);

// ============================================================================
// Express HTTP Server Setup
// ============================================================================

const app = express();
const server = http.createServer(app);

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Routes
app.get('/', (req, res) => {
  // Serve dashboard.html from public folder or root
  res.sendFile(path.join(__dirname, 'dashboard.html'));
});

app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    serialConnected: serialPort && serialPort.isOpen,
    connectedClients: wss.clients.size
  });
});

// ============================================================================
// WebSocket Server Setup
// ============================================================================

const wss = new WebSocket.Server({ port: CONFIG.WS_PORT });

// Store all connected clients for broadcasting
const clients = new Set();

wss.on('connection', (ws, req) => {
  const clientIP = req.socket.remoteAddress;
  console.log(`🟢 New WebSocket client connected from ${clientIP}`);
  console.log(`   Total clients: ${wss.clients.size}`);
  
  clients.add(ws);

  // Send connection confirmation
  ws.send(JSON.stringify({
    type: 'connection',
    message: 'Connected to Arduino Dashboard Server',
    timestamp: new Date().toISOString(),
    serialConnected: serialPort && serialPort.isOpen
  }));

  // Handle incoming messages from client
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      console.log(`📨 Received from client: ${data.type}`);
      
      // Handle different message types
      switch (data.type) {
        case 'ping':
          ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
          break;
        case 'request_status':
          ws.send(JSON.stringify({
            type: 'status',
            serialConnected: serialPort && serialPort.isOpen,
            connectedClients: wss.clients.size,
            timestamp: new Date().toISOString()
          }));
          break;
        default:
          console.log(`⚠️  Unknown message type: ${data.type}`);
      }
    } catch (err) {
      console.error('❌ Error parsing client message:', err.message);
    }
  });

  // Handle client disconnect
  ws.on('close', () => {
    console.log(`🔴 Client disconnected from ${clientIP}`);
    clients.delete(ws);
    console.log(`   Remaining clients: ${wss.clients.size}`);
  });

  // Handle WebSocket errors
  ws.on('error', (err) => {
    console.error(`❌ WebSocket error from ${clientIP}:`, err.message);
  });
});

// Broadcast helper function
function broadcast(data) {
  const jsonData = JSON.stringify(data);
  let successCount = 0;

  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(jsonData);
      successCount++;
    }
  });

  return successCount;
}

// ============================================================================
// Serial Port Setup
// ============================================================================

let serialPort;
let parser;

async function initializeSerialPort() {
  try {
    console.log(`🔌 Attempting to connect to serial port: ${CONFIG.SERIAL_PORT} at ${CONFIG.SERIAL_BAUD_RATE} baud...\n`);

    serialPort = new SerialPort({
      path: CONFIG.SERIAL_PORT,
      baudRate: CONFIG.SERIAL_BAUD_RATE,
      autoOpen: true
    });

    // Create line parser (reads data until newline)
    parser = serialPort.pipe(new ReadlineParser({ delimiter: '\n' }));

    // Handle successful connection
    serialPort.on('open', () => {
      console.log('✅ Serial port connected successfully\n');
      console.log('📊 Waiting for Arduino data...\n');

      // Notify all connected WebSocket clients
      broadcast({
        type: 'serial_connected',
        message: 'Arduino serial port connected',
        timestamp: new Date().toISOString()
      });
    });

    // Handle incoming data from Arduino
    parser.on('data', (line) => {
      const trimmedLine = line.trim();
      
      // Skip empty lines
      if (!trimmedLine) return;

      // Parse Arduino data format: time_ms,temperature,ph,voltage
      const data = parseArduinoData(trimmedLine);
      
      if (data) {
        // Broadcast to all connected WebSocket clients
        const clientsNotified = broadcast({
          type: 'sensor_data',
          payload: data,
          timestamp: new Date().toISOString()
        });

        // Log to console
        console.log(`📈 Data received (sent to ${clientsNotified} clients):`);
        console.log(`   Time: ${data.time}ms | Temp: ${data.temperature}°C | pH: ${data.ph} | Voltage: ${data.voltage}V`);
      } else {
        console.log(`⚠️  Invalid format: "${trimmedLine}"`);
      }
    });

    // Handle serial port errors
    serialPort.on('error', (err) => {
      console.error('❌ Serial port error:', err.message);
      broadcast({
        type: 'serial_error',
        message: err.message,
        timestamp: new Date().toISOString()
      });
    });

    // Handle serial port close
    serialPort.on('close', () => {
      console.log('⚠️  Serial port closed');
      broadcast({
        type: 'serial_disconnected',
        message: 'Arduino serial port disconnected',
        timestamp: new Date().toISOString()
      });
    });

  } catch (err) {
    console.error('❌ Failed to open serial port:', err.message);
    console.error('\n💡 Troubleshooting:');
    console.error('   1. Check Arduino is connected via USB');
    console.error('   2. Verify serial port path in .env file');
    console.error('   3. On Windows: Check Device Manager for COM port');
    console.error('   4. On Mac: Run: ls /dev/tty.*');
    console.error('   5. On Linux: Run: ls /dev/tty*\n');

    // Try to reconnect after 5 seconds
    console.log('🔄 Retrying in 5 seconds...\n');
    setTimeout(initializeSerialPort, 5000);
  }
}

/**
 * Parse Arduino data in format: time_ms,temperature,ph,voltage
 * Example: 120675,25.437,14.575,4.1642
 * @param {string} line - Raw data line from Arduino
 * @returns {object|null} Parsed data object or null if invalid
 */
function parseArduinoData(line) {
  try {
    const parts = line.split(',');

    // Validate format
    if (parts.length !== 4) {
      return null;
    }

    const [timeStr, tempStr, phStr, voltageStr] = parts;

    // Parse values
    const time = parseFloat(timeStr);
    const temperature = parseFloat(tempStr);
    const ph = parseFloat(phStr);
    const voltage = parseFloat(voltageStr);

    // Validate all values are numbers
    if (isNaN(time) || isNaN(temperature) || isNaN(ph) || isNaN(voltage)) {
      return null;
    }

    return {
      time,
      temperature,
      ph,
      voltage
    };
  } catch (err) {
    return null;
  }
}

// ============================================================================
// Server Startup
// ============================================================================

server.listen(CONFIG.HTTP_PORT, () => {
  console.log(`🌐 HTTP Server listening on http://localhost:${CONFIG.HTTP_PORT}`);
  console.log(`📡 WebSocket Server listening on ws://localhost:${CONFIG.WS_PORT}\n`);
});

wss.on('listening', () => {
  console.log('✅ WebSocket server is ready for connections\n');
});

// Initialize serial port connection
initializeSerialPort();

// ============================================================================
// Graceful Shutdown
// ============================================================================

process.on('SIGINT', () => {
  console.log('\n\n⏹️  Shutting down gracefully...\n');

  // Close serial port
  if (serialPort && serialPort.isOpen) {
    serialPort.close(() => {
      console.log('✅ Serial port closed');
    });
  }

  // Close WebSocket connections
  wss.clients.forEach((client) => {
    client.close(1001, 'Server shutting down');
  });

  // Close HTTP server
  server.close(() => {
    console.log('✅ HTTP server closed');
    console.log('✅ Server shutdown complete\n');
    process.exit(0);
  });

  // Force exit after 10 seconds
  setTimeout(() => {
    console.error('❌ Forced shutdown');
    process.exit(1);
  }, 10000);
});

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
  console.error('❌ Uncaught exception:', err);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Unhandled rejection at:', promise, 'reason:', reason);
  process.exit(1);
});
