'''
Gateway script that receives sensor data from the Arduino and sends control data to it.
Arduino sketch: 'simple_nrf24_tx2gateway2rx.ino'
'''
import time
import struct
from RF24 import RF24, RF24_PA_LOW, RF24_250KBPS


# Create and configure the RF24 object
radio = RF24(17, 0)  # CE and CSN pins

# Addresses for the nodes
addressToSensor = b"GW2S1"
addressFromSensor = b"S2GW1"

# Structure to hold the received data
class SensorData:
    def __init__(self):
        self.analogValue = 0
        self.digitalStatus = 0

# Initialize the radio
def setup_radio():
    radio.begin()
    radio.setChannel(80)  # the same channel as the sensor node
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_250KBPS)
    radio.setPayloadSize(3)  # Set payload size to 3 bytes (uint16_t + uint8_t)
    radio.openWritingPipe(addressToSensor)
    radio.openReadingPipe(1, addressFromSensor)
    radio.startListening()
    print("Radio initialized.")

# Receive data from the Arduino
def receive_data():
    if radio.available():
        received_data = SensorData()
        len = radio.getDynamicPayloadSize()
        if len == 3:  # Ensure the buffer is 3 bytes long
            recv_buffer = radio.read(len)
            received_data.analogValue, received_data.digitalStatus = struct.unpack('HB', recv_buffer)
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
                print(f"Received analog value: {data.analogValue}, digital status: {data.digitalStatus}")
                if data.analogValue > 511:
                    if data.digitalStatus == 1:  # Active low (0 -> ON, 1 -> OFF)
                        send_data(1)
                        print("Sent: 1")
                else:
                    if data.digitalStatus == 0:  # Active low (0 -> ON, 1 -> OFF)
                        send_data(0)
                        print("Sent: 0")
            time.sleep(1)
        except KeyboardInterrupt:
            print(" Keyboard Interrupt detected. Exiting...")
            radio.powerDown()
            break

if __name__ == "__main__":
    main()
