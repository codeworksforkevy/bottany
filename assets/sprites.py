from PIL import Image, ImageDraw
import random

TREE = (36,120,60)
TRUNK = (90,60,40)

CABIN = (120,80,50)
ROOF = (90,40,40)


def generate_tree():

    img = Image.new("RGBA",(16,16),(0,0,0,0))
    d = ImageDraw.Draw(img)

    for y in range(10,16):
        d.point((8,y),fill=TRUNK)

    for x in range(3,13):
        for y in range(3,10):
            if random.random()<0.7:
                d.point((x,y),fill=TREE)

    return img


def generate_cabin():

    img = Image.new("RGBA",(20,20),(0,0,0,0))
    d = ImageDraw.Draw(img)

    for x in range(4,16):
        for y in range(10,18):
            d.point((x,y),fill=CABIN)

    for x in range(3,17):
        d.point((x,10),fill=ROOF)

    return img
