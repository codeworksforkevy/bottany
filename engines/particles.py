import random

WIDTH = 512
HEIGHT = 256

RAIN_COLOR = (200,210,220)
SNOW_COLOR = (240,240,255)


class RainParticle:

    def __init__(self):

        self.x=random.uniform(0,WIDTH)
        self.y=random.uniform(-HEIGHT,0)

        self.vx=random.uniform(-0.5,0.5)
        self.vy=random.uniform(8,12)

        self.length=random.randint(6,10)


    def update(self):

        self.x+=self.vx
        self.y+=self.vy

        if self.y>HEIGHT:
            self.x=random.uniform(0,WIDTH)
            self.y=random.uniform(-100,0)


class SnowParticle:

    def __init__(self):

        self.x=random.uniform(0,WIDTH)
        self.y=random.uniform(-HEIGHT,0)

        self.vx=random.uniform(-1,1)
        self.vy=random.uniform(1,3)


    def update(self):

        self.x+=self.vx
        self.y+=self.vy

        if self.y>HEIGHT:

            self.x=random.uniform(0,WIDTH)
            self.y=random.uniform(-50,0)
