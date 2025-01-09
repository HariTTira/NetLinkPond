import paho.mqtt.client as mqtt

# MQTT server details
MQTT_SERVER = "40.90.169.126"
MQTT_PORT = 1883
MQTT_USERNAME = "dc24"
MQTT_PASSWORD = "kmitl-dc24"

# Topic to subscribe
TOPIC = "hello/NetlinkPond"

# Callback when the client connects to the server
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        client.subscribe(TOPIC)
        print(f"Subscribed to topic: {TOPIC}")
    else:
        print(f"Failed to connect, return code {rc}")

# Callback when a message is received
def on_message(client, userdata, msg):
    print(f"Message received on topic {msg.topic}: {msg.payload.decode('utf-8')}")

# Create MQTT client
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Assign callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connect to the server
print("Connecting to MQTT broker...")
client.connect(MQTT_SERVER, MQTT_PORT, 60)

# Blocking loop to process network traffic and dispatch callbacks
client.loop_forever()
