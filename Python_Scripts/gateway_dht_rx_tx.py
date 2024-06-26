'''
Gateway script to receive data from the sensor node and sends control data to the sensor node.
Arduino sketch: 'simple_nrf24_dht_tx2gateway2rx.ino'
'''
import sys
import time
import struct
from RF24 import RF24, RF24_PA_LOW, RF24_250KBPS


# Create and configure the RF24 object
radio = RF24(17, 0)  # CE and CSN pins

# Addresses for the nodes
addressToSensor = b"GW2S1"
addressFromSensor = b"S2GW1"

# Payload size (float32 + float32 + uint16_t + uint8_t)
PAYLOAD_SIZE = 4 + 4 + 2 + 1  # Set payload size to 11 bytes

# Structure to hold the received data
class SensorData:
    def __init__(self):
        self.temperature = 0
        self.humidity = 0
        self.moisture = 0
        self.digitalStatus = 0

# Initialize the radio
def setup_radio():
    radio.begin()
    radio.setChannel(80)  # the same channel as the sensor node
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_250KBPS)
    radio.setPayloadSize(PAYLOAD_SIZE)  # Set payload size
    radio.openWritingPipe(addressToSensor)
    radio.openReadingPipe(1, addressFromSensor)
    radio.startListening()
    print("Radio initialized.")

# Receive data from the Arduino
def receive_data():
    if radio.available():
        received_data = SensorData()
        len = radio.getDynamicPayloadSize()
        if len == PAYLOAD_SIZE:  # Ensure correct payload size
            recv_buffer = radio.read(len)
            received_data.temperature, received_data.humidity, received_data.moisture, received_data.digitalStatus = struct.unpack('ffHB', recv_buffer)
            return received_data
    return None

# Send control data to the Arduino
def send_data(value):
    radio.stopListening()
    radio.write(struct.pack('B', value))
    radio.startListening()

def main():
    setup_radio()
    while True:
        try:
            data = receive_data()
            if data:
                print(f"Received temperature: {data.temperature}, humidity: {data.humidity}, moisture: {data.moisture}, digital status: {data.digitalStatus}")
                if data.moisture > 511:
                    if data.digitalStatus == 1:
                        send_data(1)
                        print("Sent: 1")
                else:
                    if data.digitalStatus == 0:
                        send_data(0)
                        print("Sent: 0")
            time.sleep(1)
        except KeyboardInterrupt:
            print(" Keyboard Interrupt detected. Exiting...")
            radio.powerDown()
            sys.exit(0)

if __name__ == "__main__":
    main()
