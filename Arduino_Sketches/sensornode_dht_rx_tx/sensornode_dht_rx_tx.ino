/*
Arduino sketch to send data to gateway.
Also, it receives control data from gateway to control a digital output (D4).
Gateway Python script: 'gateway_dht_rx_tx.py'
Gateway Python script with Thingsboard: 'gateway_thingsboard_dht_rx_tx.py'
*/
#include <SPI.h>
#include <RF24.h>
#include <DHT.h>

// Define the CE and CSN pins for the NRF24L01
#define CE_PIN 7
#define CSN_PIN 8
// Create an RF24 object
RF24 radio(CE_PIN, CSN_PIN);

#define DHTPIN 2 // Digital pin connected to the DHT sensor
#define DHTTYPE DHT22   // DHT 22
// Initialize DHT sensor.
DHT dht(DHTPIN, DHTTYPE);

// Define the addresses for the communication
const uint8_t addressToGateway[6] = "S2GW1";  // Sensor to Gateway
const uint8_t addressFromGateway[6] = "GW2S1";  // Gateway to Sensor

// Pin definitions
const int analogSensorPin = A0;
const int digitalOutputPin = 4;

// Structure to hold the data sent to the gateway
struct SensorData {
  float temperature;
  float humidity;
  uint16_t moisture;  // Analog sensor value (0-1023)
  uint8_t digitalStatus;  // Digital output status (0 or 1)
};

// Variable to store received data
uint8_t receivedValue;

void setup() {
  // Initialize the Serial Monitor
  Serial.begin(115200);
  
  // Initialize the digital output pin
  pinMode(digitalOutputPin, OUTPUT);

  // Start DHT sensor
  dht.begin();
  
  // Initialize the RF24 module
  if (!radio.begin()) {
    Serial.println(F("Radio hardware is not responding!"));
    while (1) {}
  }
  
  // Set the RF24 module configuration
  radio.setChannel(80); // the same channel as the sensor node
  radio.setPALevel(RF24_PA_LOW);
  radio.setDataRate(RF24_250KBPS);
  radio.setPayloadSize(sizeof(SensorData));  // Set payload size to 3 bytes

  // Open the writing and reading pipes
  radio.openWritingPipe(addressToGateway);
  radio.openReadingPipe(1, addressFromGateway);
  
  // Start listening for incoming data
  radio.startListening();
  
  Serial.println(F("Setup complete."));
}

void loop() {
  // Read the analog sensor value
  uint16_t moisture = analogRead(analogSensorPin);
  
  // Read the digital output status
  uint8_t digitalStatus = digitalRead(digitalOutputPin);

  // Read humidity
  float h = dht.readHumidity();
  // Read temperature as Celsius (the default)
  float t = dht.readTemperature();  

  // Check if any reads failed and exit early (to try again).
  if (isnan(h) || isnan(t)) {
    Serial.println(F("Failed to read from DHT sensor!"));
    h = -1.0;
    t = -1.0;
  }

  // Create a SensorData structure to hold the data
  SensorData dataToSend = { t, h, moisture, digitalStatus };
  
  // Stop listening, send the data, and start listening again
  radio.stopListening();
  if (radio.write(&dataToSend, sizeof(dataToSend))) {
    Serial.print(F("Temperature: "));
    Serial.print(dataToSend.temperature);
    Serial.print(F(", humidity: "));
    Serial.print(dataToSend.humidity);    
    Serial.print(F(", moisture: "));
    Serial.print(dataToSend.moisture);
    Serial.print(F(", digital status: "));
    Serial.println(dataToSend.digitalStatus);
  } else {
    Serial.println(F("Failed to send data."));
  }
  radio.startListening();
  
  // Check if there is any data available to read
  if (radio.available()) {
    // Read the data
    radio.read(&receivedValue, sizeof(receivedValue));
    
    // Print the received value
    Serial.print(F("Received value: "));
    Serial.println(receivedValue);
    
    // Control the digital output pin based on the received value
    if (receivedValue == 0) {
      digitalWrite(digitalOutputPin, HIGH);  // Relay is active low (0 -> ON, 1 -> OFF)
      Serial.println(F("Digital output set to HIGH."));
    } else {
      digitalWrite(digitalOutputPin, LOW);  // Relay is active low (0 -> ON, 1 -> OFF)
      Serial.println(F("Digital output set to LOW."));
    }
  }
  
  // Add a small delay
  delay(1000);
}
