from Common.sharedImports import *
from PIL import Image
from prometheus_client import start_http_server, Counter, Gauge
import paho.mqtt.client as mqtt
from Common.Constants.color import Colors
from Common.Constants.mqtt import Mqtt
from Common.Constants.prometheus import Metrics, Prometheus
from Common.Interfaces.Fish import Fish
import redis

class FishHaven:
    def __init__(self):
        pygame.init()
        self.setupRedis()
        self.WIDTH = 800
        self.HEIGHT = 600
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("NetLink Pond")
        
        self.background = self.loadBackground("NetLinkPhoto/fishbg.jpg")
        
        self.font = pygame.font.Font(None, 36)
        self.smallFont = pygame.font.Font(None, 24)
        
        self.groupFishGif = {
            "NetLink": self.loadGifFrame("NetLinkPhoto/NetLink.gif"),
            "Honey Lemon": self.loadGifFrame("NetLinkPhoto/Honey Lemon.gif"),
            "Parallel": self.loadGifFrame("NetLinkPhoto/Parallel.gif"),
            "DC_Universe": self.loadGifFrame("NetLinkPhoto/DC_Universe.gif"),
        }

        self.frameDuration = 0.1
        
        self.fishes: List[Fish] = []
        self.spawnInterval = 14
        self.lastSpawnTime = time.time()
        
        self.stats = {
            "total_fish": 0,
            "local_fish": 0,
            "visitor_fish": 0
        }
        
        self.topicInput = ""
        self.topicInputActive = False
        self.topicInputRect = pygame.Rect(self.WIDTH - 410, 10, 200, 36)
        self.selectedTopic = Mqtt.TOPIC
        
        self.publishButtonRect = pygame.Rect(self.WIDTH - 200, 10, 190, 36)
        
        self.setupMqtt()

        self.fishSpawned = Counter(Metrics.FISH_SPAWNED["name"], Metrics.FISH_SPAWNED["description"])
        self.fishRemoved = Counter(Metrics.FISH_REMOVED["name"], Metrics.FISH_REMOVED["description"])
        self.activeFish = Gauge(Metrics.ACTIVE_FISH["name"], Metrics.ACTIVE_FISH["description"])
        self.fishLocal = Gauge(Metrics.FISH_LOCAL["name"], Metrics.FISH_LOCAL["description"])
        self.fishVisitors = Gauge(Metrics.FISH_VISITORS["name"], Metrics.FISH_VISITORS["description"])

        start_http_server(Prometheus.PROMETHEUS_SERVER)
        
    def setupRedis(self):
        self.redis_client = redis.StrictRedis(host="localhost", port=6379, decode_responses=True)

    def store_fish_data(self, fish):
        fish_data = {
            "name": fish.name,
            "group_name": fish.group_name,
            "x": fish.x,
            "y": fish.y,
            "lifetime": fish.lifetime,
            "speed": fish.speed
        }
        self.redis_client.set(f"fish:{fish.name}", json.dumps(fish_data))

    def remove_fish_data(self, name):
        self.redis_client.delete(f"fish:{name}")

    def get_fish_data(self, name):
        fish_data = self.redis_client.get(f"fish:{name}")
        print(f"Fetching data for {name}: {fish_data}")  # Debugging line
        return json.loads(fish_data) if fish_data else None

    def loadBackground(self, image_path: str) -> pygame.Surface:
        try:
            background = pygame.image.load(image_path)
            return pygame.transform.scale(background, (self.WIDTH, self.HEIGHT))
        except Exception as e:
            print(f"Error loading background image: {e}")
            surface = pygame.Surface((self.WIDTH, self.HEIGHT))
            surface.fill(Colors.BLUE)
            return surface
    
    def loadGifFrame(self, gif_path: str) -> List[pygame.Surface]:
        frames = []
        try:
            gif = Image.open(gif_path)
            frameCount = 0
            
            while True:
                try:
                    gif.seek(frameCount)
                    frame = gif.convert('RGBA')
                    pygameImage = pygame.image.fromstring(
                        frame.tobytes(), frame.size, frame.mode
                    )
                    pygameImage = pygame.transform.scale(pygameImage, (100, 100))
                    frames.append(pygameImage)
                    frameCount += 1
                except EOFError:
                    break
                
            return frames
        except Exception as e:
            print(f"Error loading GIF: {e}")
            surface = pygame.Surface((30, 20), pygame.SRCALPHA)
            pygame.draw.ellipse(surface, Colors.ORANGE, (0, 0, 20, 20))
            return [surface]
    
    def setupMqtt(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(Mqtt.MQTT_USERNAME, Mqtt.MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(Mqtt.MQTT_SERVER, Mqtt.MQTT_PORT, 60)
        self.client.loop_start()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT broker!")
            topics = [(Mqtt.TOPIC, 0), ("user/NetLink", 0)]
            self.client.subscribe(topics)
            self.sendHello()
        else:
            print(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, message):
        print(f"Message received on topic {message.topic}: {message.payload.decode('utf-8')}")
        
        try:
            data = json.loads(message.payload.decode('utf-8'))
            if all(key in data for key in ["name", "group_name", "lifetime"]) and data["group_name"] != Mqtt.GROUP_NAME:
                self.spawnVisitorFish(data)
                print(f"Spawned visitor fish from {data['group_name']}")
        
        except json.JSONDecodeError:
            print("Error: Received malformed JSON")

    def sendHello(self):
        message = {
            "type": "hello",
            "sender": Mqtt.GROUP_NAME,
            "timestamp": int(time.time()),
            "data": {}
        }
        self.client.publish(Mqtt.TOPIC, json.dumps(message))
    
    def spawnFish(self):
        fish = Fish(
            x=random.randint(50, self.WIDTH - 50),
            y=random.randint(50, self.HEIGHT - 50),
            direction=random.uniform(0, 2 * math.pi),
            group_name=Mqtt.GROUP_NAME,
            lifetime=15.0,
            current_frame=0,
            animation_time=time.time(),
            speed=2.0,
            name=f"{Mqtt.GROUP_NAME}_{time.time()}",
            frames=self.groupFishGif.get(Mqtt.GROUP_NAME, self.groupFishGif["NetLink"]) 
        )
        self.fishes.append(fish)
        self.stats["total_fish"] += 1
        self.stats["local_fish"] += 1
    # Store fish data in Redis
        self.store_fish_data(fish)
        self.fishSpawned.inc()
        self.activeFish.inc()
        self.fishLocal.inc()

    
    def spawnVisitorFish(self, fish_data):
        fish = Fish(
            x=random.randint(50, self.WIDTH - 50),
            y=random.randint(50, self.HEIGHT - 50),
            direction=random.uniform(0, 2 * math.pi),
            group_name=fish_data["group_name"],
            lifetime=fish_data["lifetime"],
            current_frame=0,
            animation_time=time.time(),
            speed=2.0,
            name=fish_data["name"],
            frames=self.groupFishGif.get(fish_data["group_name"], self.groupFishGif["NetLink"])
        )
        self.fishes.append(fish)
        self.stats["total_fish"] += 1
        self.stats["visitor_fish"] += 1

        self.store_fish_data(fish)
        redis_data = self.get_fish_data(fish.name)
        print("redis data: ", redis_data)
        self.fishVisitors.inc()


    def updateFish(self):
        current_time = time.time()

        if current_time - self.lastSpawnTime > self.spawnInterval:
            self.spawnFish()
            self.lastSpawnTime = current_time

        for fish in self.fishes[:]:
            fish.x += math.cos(fish.direction) * fish.speed
            fish.y += math.sin(fish.direction) * fish.speed

            if current_time - fish.animation_time > self.frameDuration:
                fish.current_frame = (fish.current_frame + 1) % len(fish.frames)
                fish.animation_time = current_time

            if fish.x < 0 or fish.x > self.WIDTH:
                fish.direction = math.pi - fish.direction
            if fish.y < 0 or fish.y > self.HEIGHT:
                fish.direction = -fish.direction

            fish.lifetime -= 0.016

            if fish.lifetime <= 0:
                self.fishes.remove(fish)
                # Remove fish from Redis
                self.remove_fish_data(fish.name)
                self.fishRemoved.inc()
                self.activeFish.dec()
                if fish.group_name == Mqtt.GROUP_NAME:
                    self.stats["local_fish"] -= 1
                    self.fishLocal.dec()
                else:
                    self.stats["visitor_fish"] -= 1
                    self.fishVisitors.dec()

            if random.random() < 0.02:
                fish.direction += random.uniform(-0.5, 0.5)

        
    def handleTextInput(self, event):
        if self.topicInputActive:
            if event.key == pygame.K_RETURN:
                if self.topicInput.strip():
                    self.selectedTopic = self.topicInput.strip()
                self.topicInputActive = False
            elif event.key == pygame.K_BACKSPACE:
                self.topicInput = self.topicInput[:-1]
            else:
                self.topicInput += event.unicode
    
    def drawTopicInput(self):
        color = Colors.WHITE if not self.topicInputActive else Colors.LIGHT_BLUE
        pygame.draw.rect(self.screen, color, self.topicInputRect, 2)        
        input_text = self.smallFont.render(self.topicInput or "Enter Topic", True, Colors.BLACK)
        self.screen.blit(input_text, (self.topicInputRect.x + 5, self.topicInputRect.y + 5))
    
    def drawUI(self):
        pygame.draw.rect(self.screen, Colors.LIGHT_BLUE, self.publishButtonRect)
        publish_text = self.font.render("Publish Fish", True, Colors.BLACK)
        self.screen.blit(publish_text, (self.publishButtonRect.x + 10, self.publishButtonRect.y + 10))        
        self.drawTopicInput()
    
    def draw(self):
        self.screen.blit(self.background, (0, 0))

        for fish in self.fishes:
            image = fish.frames[fish.current_frame]
            if math.cos(fish.direction) < 0:
                image = pygame.transform.flip(image, True, False)
            self.screen.blit(image, (fish.x - image.get_width() // 2, fish.y - image.get_height() // 2))

        self.drawStats()
        self.drawUI()

    
    def drawStats(self):
        stats_surface = pygame.Surface((200, 100))
        stats_surface.fill(Colors.WHITE)
        stats_surface.set_alpha(200)
        
        y = 10
        for label, value in self.stats.items():
            text = self.font.render(f"{label.replace('_', ' ').title()}: {value}", True, Colors.BLACK)
            stats_surface.blit(text, (10, y))
            y += 30
        
        self.screen.blit(stats_surface, (10, 10))
    
    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.spawnFish()
                    
                    self.handleTextInput(event)
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.publishButtonRect.collidepoint(event.pos) and self.fishes:
                        for fish in self.fishes:
                            if fish.group_name == Mqtt.GROUP_NAME:
                                fish_msg = {
                                    "name": fish.name,
                                    "group_name": fish.group_name,
                                    "lifetime": fish.lifetime
                                }
                                self.client.publish(self.selectedTopic, json.dumps(fish_msg))
                                print(f"Published fish: {fish_msg} to: {self.selectedTopic}")
                                self.fishes.remove(fish)
                                break

                    if self.topicInputRect.collidepoint(event.pos):
                        self.topicInputActive = True
                    else:
                        self.topicInputActive = False
            
            self.updateFish()
            self.draw()
            pygame.display.flip()
            clock.tick(60)
        
        self.cleanup()
    
    def cleanup(self):
        self.client.loop_stop()
        self.client.disconnect()
        pygame.quit()

if __name__ == "__main__":
    game = FishHaven()
    game.run()