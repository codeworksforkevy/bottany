from PIL import Image, ImageDraw
from particles import RainParticle, SnowParticle
from scene_generator import build_scene
import random

WIDTH = 512
HEIGHT = 256

SKY = (20,24,28)
GROUND = (60,70,60)

RAIN = (200,210,220)
SNOW = (240,240,255)


class WeatherEngine:

    def __init__(self, weather="rain"):

        self.weather = weather
        self.scene = build_scene()

        if weather=="rain":
            self.particles=[RainParticle() for _ in range(900)]

        if weather=="snow":
            self.particles=[SnowParticle() for _ in range(400)]

        self.splashes=[]


    def render_frame(self):

        img = Image.new("RGB",(WIDTH,HEIGHT),SKY)
        draw = ImageDraw.Draw(img)

        for sprite,x,y in self.scene:
            img.paste(sprite,(x,y),sprite)

        draw.rectangle(
            [0,HEIGHT-10,WIDTH,HEIGHT],
            fill=GROUND
        )

        for p in self.particles:

            p.update()

            x=int(p.x)
            y=int(p.y)

            if self.weather=="rain":

                for i in range(6):

                    draw.point((x,y-i),fill=RAIN)

            if self.weather=="snow":

                draw.point((x,y),fill=SNOW)

        return img
