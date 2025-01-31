import pygame
import random
import time
import json
import paho.mqtt.client as mqtt
from dataclasses import dataclass
from typing import List, Tuple
import math
from PIL import Image
import os

# MQTT Configuration
MQTT_SERVER = "40.90.169.126"
MQTT_PORT = 1883
MQTT_USERNAME = "dc24"
MQTT_PASSWORD = "kmitl-dc24"
TOPIC = "fishhaven/stream"
GROUP_NAME = "NetLink"

# Colors
BLUE = (0, 105, 148)
LIGHT_BLUE = (135, 206, 235)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
ORANGE = (255, 165, 0)

@dataclass
class Fish:
    x: float
    y: float
    direction: float
    genesis_pond: str
    lifetime: float
    current_frame: int
    animation_time: float
    speed: float
    id: str
    frames: List[pygame.Surface]  # Add frames attribute

class FishHaven:
    def __init__(self):
        pygame.init()
        self.WIDTH = 800
        self.HEIGHT = 600
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("NetLink Pond")
        
        # Load and scale background image
        self.background = self.load_background("NetLinkPhoto/fishbg.jpg")
        
        # Initialize font
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Load GIF frames
        self.group_fish_gifs = {
            "NetLink": self.load_gif_frames("NetLinkPhoto/lanturn2.gif"),
            "HoneyBee": self.load_gif_frames("NetLinkPhoto/Ariel.gif"),
        }

        self.frame_duration = 0.1
        
        # Fish settings
        self.fishes: List[Fish] = []
        self.SPAWN_INTERVAL = 14
        self.last_spawn_time = time.time()
        
        # Pond stats
        self.stats = {
            "total_fish": 0,
            "local_fish": 0,
            "visitor_fish": 0
        }
        
        # Topic input
        self.topic_input = ""
        self.topic_input_active = False
        self.topic_input_rect = pygame.Rect(self.WIDTH - 410, 10, 200, 36)
        self.selected_topic = TOPIC
        
        # Publish button
        self.publish_button_rect = pygame.Rect(self.WIDTH - 200, 10, 190, 36)
        
        # MQTT setup
        self.setup_mqtt()
    
    def load_background(self, image_path: str) -> pygame.Surface:
        """Load and scale background image to screen size"""
        try:
            background = pygame.image.load(image_path)
            return pygame.transform.scale(background, (self.WIDTH, self.HEIGHT))
        except Exception as e:
            print(f"Error loading background image: {e}")
            # Create a fallback surface if image loading fails
            surface = pygame.Surface((self.WIDTH, self.HEIGHT))
            surface.fill(BLUE)
            return surface
    
    def load_gif_frames(self, gif_path: str) -> List[pygame.Surface]:
        """Load and convert GIF frames to Pygame surfaces"""
        frames = []
        try:
            gif = Image.open(gif_path)
            frame_count = 0
            
            while True:
                try:
                    gif.seek(frame_count)
                    frame = gif.convert('RGBA')
                    pygame_image = pygame.image.fromstring(
                        frame.tobytes(), frame.size, frame.mode
                    )
                    # Scale the image if needed (adjust size as necessary)
                    pygame_image = pygame.transform.scale(pygame_image, (100, 100))
                    frames.append(pygame_image)
                    frame_count += 1
                except EOFError:
                    break
                
            return frames
        except Exception as e:
            print(f"Error loading GIF: {e}")
            # Create a fallback surface if GIF loading fails
            surface = pygame.Surface((30, 20), pygame.SRCALPHA)
            pygame.draw.ellipse(surface, ORANGE, (0, 0, 20, 20))
            return [surface]
    
    def setup_mqtt(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_SERVER, MQTT_PORT, 60)
        self.client.loop_start()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT broker!")
            self.client.subscribe(TOPIC)
            self.send_hello_message()
        else:
            print(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, message):
        print(f"Message received on topic {message.topic}: {message.payload.decode('utf-8')}")
        
        try:
            data = json.loads(message.payload.decode('utf-8'))
            
            # Ensure the message contains necessary fish data and is from another pond
            if all(key in data for key in ["id", "genesis_pond", "lifetime"]) and data["genesis_pond"] != GROUP_NAME:
                self.spawn_visitor_fish(data)  # Spawn the visitor fish
                print(f"Spawned visitor fish from {data['genesis_pond']}")
        
        except json.JSONDecodeError:
            print("Error: Received malformed JSON")

    def send_hello_message(self):
        message = {
            "type": "hello",
            "sender": GROUP_NAME,
            "timestamp": int(time.time()),
            "data": {}
        }
        self.client.publish(TOPIC, json.dumps(message))
    
    def create_fish_message(self, fish):
        """Create MQTT message for a specific fish"""
        return {
            "id": fish.id,
            "genesis_pond": fish.genesis_pond,
            "lifetime": fish.lifetime
        }
    
    def spawn_fish(self):
        fish = Fish(
            x=random.randint(50, self.WIDTH - 50),
            y=random.randint(50, self.HEIGHT - 50),
            direction=random.uniform(0, 2 * math.pi),
            genesis_pond=GROUP_NAME,
            lifetime=15.0,
            current_frame=0,
            animation_time=time.time(),
            speed=2.0,
            id=f"{GROUP_NAME}_{time.time()}",
            frames=self.group_fish_gifs.get(GROUP_NAME, self.group_fish_gifs["NetLink"])  # Assign frames
        )
        self.fishes.append(fish)
        self.stats["total_fish"] += 1
        self.stats["local_fish"] += 1

    
    def spawn_visitor_fish(self, fish_data):
        fish = Fish(
            x=random.randint(50, self.WIDTH - 50),
            y=random.randint(50, self.HEIGHT - 50),
            direction=random.uniform(0, 2 * math.pi),
            genesis_pond=fish_data["genesis_pond"],
            lifetime=fish_data["lifetime"],
            current_frame=0,
            animation_time=time.time(),
            speed=2.0,
            id=fish_data["id"],
            frames=self.group_fish_gifs.get(fish_data["genesis_pond"], self.group_fish_gifs["NetLink"])  # Assign frames
        )
        self.fishes.append(fish)
        self.stats["total_fish"] += 1
        self.stats["visitor_fish"] += 1


    def update_fishes(self):
        current_time = time.time()

        # Spawn new fish if needed
        if current_time - self.last_spawn_time > self.SPAWN_INTERVAL:
            self.spawn_fish()
            self.last_spawn_time = current_time

        # Update existing fish
        for fish in self.fishes[:]:
            # Update position
            fish.x += math.cos(fish.direction) * fish.speed
            fish.y += math.sin(fish.direction) * fish.speed

            # Update animation frame
            if current_time - fish.animation_time > self.frame_duration:
                fish.current_frame = (fish.current_frame + 1) % len(fish.frames)
                fish.animation_time = current_time

            # Bounce off walls
            if fish.x < 0 or fish.x > self.WIDTH:
                fish.direction = math.pi - fish.direction
            if fish.y < 0 or fish.y > self.HEIGHT:
                fish.direction = -fish.direction

            # Update lifetime
            fish.lifetime -= 0.016

            # Remove dead fish
            if fish.lifetime <= 0:
                self.fishes.remove(fish)
                if fish.genesis_pond == GROUP_NAME:
                    self.stats["local_fish"] -= 1
                else:
                    self.stats["visitor_fish"] -= 1

            # Randomly change direction
            if random.random() < 0.02:
                fish.direction += random.uniform(-0.5, 0.5)

        
    def handle_text_input(self, event):
        """Handle text input for topic selection"""
        if self.topic_input_active:
            if event.key == pygame.K_RETURN:
                # Confirm topic input
                if self.topic_input.strip():
                    self.selected_topic = self.topic_input.strip()
                self.topic_input_active = False
            elif event.key == pygame.K_BACKSPACE:
                self.topic_input = self.topic_input[:-1]
            else:
                self.topic_input += event.unicode
    
    def draw_topic_input(self):
        """Draw topic input box"""
        color = WHITE if not self.topic_input_active else LIGHT_BLUE
        pygame.draw.rect(self.screen, color, self.topic_input_rect, 2)
        
        # Render input text
        input_text = self.small_font.render(self.topic_input or "Enter Topic", True, BLACK)
        self.screen.blit(input_text, (self.topic_input_rect.x + 5, self.topic_input_rect.y + 5))
    
    def draw_publish_ui(self):
        """Draw publish button and topic input"""
        # Publish fish button
        pygame.draw.rect(self.screen, LIGHT_BLUE, self.publish_button_rect)
        publish_text = self.font.render("Publish Fish", True, BLACK)
        self.screen.blit(publish_text, (self.publish_button_rect.x + 10, self.publish_button_rect.y + 10))
        
        # Draw topic input box
        self.draw_topic_input()
    
    def draw(self):
        # Draw background image
        self.screen.blit(self.background, (0, 0))

        # Draw fish
        for fish in self.fishes:
            image = fish.frames[fish.current_frame]  # Use fish's assigned animation frames
            if math.cos(fish.direction) < 0:  # Flip image if fish is moving left
                image = pygame.transform.flip(image, True, False)
            self.screen.blit(image, (fish.x - image.get_width() // 2, fish.y - image.get_height() // 2))

        # Draw stats and UI elements
        self.draw_stats()
        self.draw_publish_ui()

    
    def draw_stats(self):
        stats_surface = pygame.Surface((200, 100))
        stats_surface.fill(WHITE)
        stats_surface.set_alpha(200)
        
        y = 10
        for label, value in self.stats.items():
            text = self.font.render(f"{label.replace('_', ' ').title()}: {value}", True, BLACK)
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
                        self.spawn_fish()
                    
                    # Handle text input for topic
                    self.handle_text_input(event)
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Check publish fish button
                    if self.publish_button_rect.collidepoint(event.pos) and self.fishes:
                        # Find a local fish to publish
                        for fish in self.fishes:
                            if fish.genesis_pond == GROUP_NAME:
                                fish_msg = self.create_fish_message(fish)
                                self.client.publish(self.selected_topic, json.dumps(fish_msg))
                                print(f"Published fish: {fish_msg}")
                                self.fishes.remove(fish)
                                break  # Stop after publishing one fish

                    # Check topic input box
                    if self.topic_input_rect.collidepoint(event.pos):
                        self.topic_input_active = True
                    else:
                        self.topic_input_active = False
            
            self.update_fishes()
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