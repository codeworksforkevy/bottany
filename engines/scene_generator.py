import random
from sprites import generate_tree, generate_cabin

WIDTH = 512
HEIGHT = 256


def build_scene():

    objects=[]

    for _ in range(random.randint(15,30)):

        tree = generate_tree()

        x = random.randint(0, WIDTH-40)
        y = random.randint(HEIGHT-90, HEIGHT-40)

        objects.append((tree,x,y))

    if random.random() < 0.7:

        cabin = generate_cabin()

        x = random.randint(100, WIDTH-100)
        y = HEIGHT-60

        objects.append((cabin,x,y))

    return objects
