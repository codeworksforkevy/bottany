import random
from PIL import Image, ImageDraw

WIDTH = 1280
HEIGHT = 640
TILE = 16

WORLD_W = 80
WORLD_H = 40

WEATHER = ["clear","drizzle","rain","storm","snow"]

class Particle:

    def __init__(self,weather):

        self.weather=weather
        self.reset()

    def reset(self):

        self.x=random.uniform(0,WIDTH)
        self.y=random.uniform(-HEIGHT,0)

        if self.weather=="snow":

            self.vy=random.uniform(2,4)
            self.vx=random.uniform(-1.2,1.2)

        else:

            self.vy=random.uniform(12,18)
            self.vx=random.uniform(-1.5,1.5)

    def update(self):

        self.x+=self.vx
        self.y+=self.vy

        if self.y>HEIGHT:

            splash=(self.x,HEIGHT-2)

            self.reset()

            return splash

        return None


class PixelWeatherEngineV10:

    def __init__(self):

        self.weather=random.choice(WEATHER)

        self.world=self.generate_world()

        self.wind=random.uniform(-1.5,1.5)

        self.splashes=[]

        if self.weather=="drizzle":
            count=600
        elif self.weather=="rain":
            count=1500
        elif self.weather=="storm":
            count=3500
        elif self.weather=="snow":
            count=800
        else:
            count=0

        self.particles=[Particle(self.weather) for _ in range(count)]

    def generate_world(self):

        world=[]

        for y in range(WORLD_H):

            row=[]

            for x in range(WORLD_W):

                if y>25:
                    tile="dirt"
                else:
                    tile="grass"

                if random.random()<0.03:
                    tile="stone"

                row.append(tile)

            world.append(row)

        return world


    def update(self):

        new=[]

        for p in self.particles:

            p.vx=self.wind

            s=p.update()

            if s:
                new.append([s[0],s[1],3])

        self.splashes+=new

        for s in self.splashes:
            s[2]-=1

        self.splashes=[s for s in self.splashes if s[2]>0]


    def render(self):

        sky=(90,120,160)

        img=Image.new("RGB",(WIDTH,HEIGHT),sky)

        draw=ImageDraw.Draw(img)

        for y,row in enumerate(self.world):

            for x,tile in enumerate(row):

                px=x*TILE
                py=y*TILE

                if tile=="grass":
                    color=(70,140,70)

                elif tile=="dirt":
                    color=(100,80,50)

                elif tile=="stone":
                    color=(120,120,120)

                draw.rectangle([px,py,px+TILE,py+TILE],fill=color)

        for _ in range(80):

            x=random.randint(0,WIDTH)

            draw.rectangle([x,HEIGHT-70,x+6,HEIGHT-20],fill=(90,60,40))
            draw.rectangle([x-10,HEIGHT-100,x+14,HEIGHT-70],fill=(40,120,60))

        for p in self.particles:

            x=int(p.x)
            y=int(p.y)

            if self.weather=="snow":
                draw.point((x,y),fill=(255,255,255))
            else:
                draw.line((x,y,x,y-5),fill=(220,220,230))

        for s in self.splashes:

            draw.point((int(s[0]),int(s[1])),fill=(230,230,240))

        return img
