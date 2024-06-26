'''
Gateway script to receive data from the sensor node and send it to ThingsBoard.
Also, it receives control data from Thingsboard and sends it to the sensor node.
Arduino sketch: 'simple_nrf24_dht_tx2gateway2rx.ino'
'''
import sys
import time
import struct
import json
import paho.mqtt.client as mqtt
from RF24 import RF24, RF24_PA_LOW, RF24_250KBPS

# Create and configure the RF24 object
radio = RF24(17, 0)  # CE and CSN pins

# Addresses for the nodes
addressToSensor = b"GW2S1"
addressFromSensor = b"S2GW1"

# Payload size (float32 + float32 + uint16_t + uint8_t)
PAYLOAD_SIZE = 4 + 4 + 2 + 1  # Set payload size to 11 bytes

# MQTT settings
THINGSBOARD_HOST = 'demo.thingsboard.io'
PORT = 1883
ACCESS_TOKEN = 'MTCP2024abc123'

# Structure to hold the received data
class SensorData:
    def __init__(self):
        self.temperature = 0
        self.humidity = 0
        self.moisture = 0
        self.digitalStatus = 0

auto_mode = False
pump_status = 1  # Pump is initially off (active low)

# Initialize the radio
def setup_radio():
    if not radio.begin():
        print("RF24 HARDWARE FAIL: Radio not responding, verify pin connections, wiring, etc.")
        return False
    radio.setChannel(80)  # the same channel as the sensor node
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_250KBPS)
    radio.setPayloadSize(PAYLOAD_SIZE)  # Set payload size to 11 bytes
    radio.openWritingPipe(addressToSensor)
    radio.openReadingPipe(1, addressFromSensor)
    radio.startListening()
    print("Radio initialized.")
    return True

# Receive data from the Arduino
def receive_data():
    if radio.available():
        received_data = SensorData()
        len = radio.getDynamicPayloadSize()
        if len == PAYLOAD_SIZE:  # Ensure the buffer is 11 bytes long
            recv_buffer = radio.read(len)
            received_data.temperature, received_data.humidity, received_data.moisture, received_data.digitalStatus = struct.unpack('ffHB', recv_buffer)
            return received_data
    return None

# Send control data to the Arduino
def send_data(value):
    radio.stopListening()
    radio.write(struct.pack('B', value))
    radio.startListening()

# MQTT callback for when a message is received from the server
def on_message(client, userdata, message):
    global auto_mode, pump_status
    payload = str(message.payload.decode("utf-8"))
    print(f"Received message '{payload}' on topic '{message.topic}'")

    try:
        data = json.loads(payload)
        if "rpc/request" in message.topic:
            if data['method'] == "setAutoMode":
                auto_mode = data['params']
                print(f"Auto mode set to {auto_mode}")
                client.publish("v1/devices/me/attributes", json.dumps({"autoMode": auto_mode, 'pumpStatus': pump_status}))

            elif data['method'] == "setPump":
                if not auto_mode:
                    pump_status = data['params']
                    print(f"Pump status set to {pump_status}")
                    client.publish("v1/devices/me/attributes", json.dumps({"pumpStatus": pump_status}))
                    send_data(pump_status)
    except Exception as e:
        print(f"Error: {e}")

def main():
    global auto_mode, pump_status

    if not setup_radio():
        return

    # MQTT client setup
    client = mqtt.Client()
    client.username_pw_set(ACCESS_TOKEN)
    client.on_message = on_message

    client.connect(THINGSBOARD_HOST, PORT, 60)
    client.loop_start()

    pump_status, auto_mode = False, False
    client.publish("v1/devices/me/attributes", json.dumps({"pumpStatus": pump_status, "autoMode": auto_mode}))
    send_data(pump_status)
    client.subscribe("v1/devices/me/rpc/request/+")

    while True:
        try:
            data = receive_data()
            if data:
                print(f"Received temperature: {data.temperature}, humidity: {data.humidity}, moisture: {data.moisture}, digital status: {data.digitalStatus}")
                client.publish("v1/devices/me/telemetry", json.dumps({"temperature": data.temperature, "humidity": data.humidity, "moisture": data.moisture, "digitalStatus": data.digitalStatus}))
                
                if auto_mode:
                    if data.moisture > 511:
                        if data.digitalStatus == 1:
                            pump_status = 1
                            send_data(pump_status)
                    else:
                        if data.digitalStatus == 0:
                            pump_status = 0
                            send_data(pump_status)
                    client.publish("v1/devices/me/attributes", json.dumps({"pumpStatus": pump_status}))
            time.sleep(1)
        except KeyboardInterrupt:
            print(" Keyboard Interrupt detected. Exiting...")
            client.loop_stop()
            client.disconnect()
            radio.powerDown()
            sys.exit(0)

if __name__ == "__main__":
    main()
