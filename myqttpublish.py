import paho.mqtt.client as mqtt
import time
import json

# MQTT server details
MQTT_SERVER = "40.90.169.126"
MQTT_PORT = 1883
MQTT_USERNAME = "dc24"
MQTT_PASSWORD = "kmitl-dc24"

# Group name
GROUP_NAME = "NetLink"

# Topic to publish
TOPIC = "hello/NetlinkPond"

# Function to create the "hello" message
def create_hello_message():
    return {
        "type": "hello",
        "sender": GROUP_NAME,
        "timestamp": int(time.time()),  # Current UNIX timestamp
        "data": {}
    }

# Create MQTT client
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Connect to the server
print("Connecting to MQTT broker...")
client.connect(MQTT_SERVER, MQTT_PORT, 60)

# Publish the "hello" message
hello_message = create_hello_message()
client.publish(TOPIC, json.dumps(hello_message))
print(f"Published message: {json.dumps(hello_message)}")

# Disconnect
client.disconnect()
print("Disconnected from MQTT broker.")
