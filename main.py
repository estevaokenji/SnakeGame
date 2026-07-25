import pygame
import random
from enum import Enum
import time

class Item(Enum):
    SNAKE = "O"
    HEAD = "o"
    APPLE = "A"
    WHITE = " "

class Direction(Enum):
    UP    = ( 0,-1)
    DOWN  = ( 0,+1)
    LEFT  = (-1, 0)
    RIGHT = (+1, 0)
    NONE  = ( 0, 0)

def tuple_sum(a,b):
    return tuple(x + y for x, y in zip(a,b))

pygame.init()
screen_size = (720,720)
screen = pygame.display.set_mode(screen_size)
pygame.display.set_caption("Jogo da Cobrinha")
endgame = False
lose = False
score = 0

map = []
snake = []
blocks = []
block_size = 20
map_size = (screen_size[0]//block_size,screen_size[1]//block_size)
for x in range(map_size[0]):
    map.append([])
    for y in range(map_size[1]):
        map[x].append([pygame.Rect(x*block_size,y*block_size,block_size,block_size),Item.WHITE])
head = pygame.Rect(0,0,block_size,block_size)
tail = pygame.Rect(0,0,block_size,block_size)
head_pos = (0,0)
direction = [Direction.NONE,Direction.UP]
last_move = 0
font_size = 20
font = pygame.font.SysFont("Arial", font_size)

def restart_game():
    global score, lose, snake, direction

    score = 0
    lose = False
    snake.clear()
    direction = [Direction.NONE, Direction.UP]

    for x in range(map_size[0]):
        for y in range(map_size[1]):
            map[x][y][1] = Item.WHITE

    random_item(Item.SNAKE)
    random_item(Item.APPLE)

def draw_game():
    screen.fill("#000000")
    for x in range(map_size[0]):
        for y in range(map_size[1]):
            c = map[x][y][1]
            color = "#00a50e" if c == Item.SNAKE else "#ff0000" if c == Item.APPLE else "#dbe5ff" if (x+y) % 2 == 0 else "#d3ddf8"
            pygame.draw.rect(screen, color, map[x][y][0])
    pygame.draw.rect(screen,"#00a50e",head)
    pygame.draw.rect(screen,"#00a50e",tail)
    text_pos = (10,10)
    hud = pygame.Surface((145, text_pos[1]+font_size+5), pygame.SRCALPHA)
    hud.fill((0, 0, 0, 120))
    text = font.render(f"Pontuação: {score:3}", False, "#FFFFFF")
    screen.blit(hud, tuple_sum(text_pos,(-5,-5)))
    screen.blit(text, text_pos)

def add_snake(x,y):
    global score, lose
    if x < 0 or y < 0 or x > map_size[0]-1 or y > map_size[1]-1:
        lose = True
        return True
    square = map[x][y][1]
    if square == Item.SNAKE:
        lose = True
        return True
    map[x][y][1] = Item.HEAD
    if len(snake) > 0:
        map[snake[len(snake)-1][0]][snake[len(snake)-1][1]][1] = Item.SNAKE
    snake.append((x,y))
    if square == Item.APPLE:
        random_item(Item.APPLE)
        score += 1
        return True
    return False

def random_item(item: Item):
    while True:
        x = random.randint(0,map_size[0]-1)
        y = random.randint(0,map_size[1]-1)
        if map[x][y][1] == Item.WHITE:
            break
    if item == Item.SNAKE:
        add_snake(x,map_size[1]-1)
        add_snake(x,map_size[1]-2)
        tail.x, tail.y = x*block_size, (map_size[1]-1)*block_size
        head.x, head.y = x*block_size, (map_size[1]-2)*block_size
    else:
        map[x][y][1] = item
    return x, y

random_item(Item.SNAKE)
random_item(Item.APPLE)

def dir_snake(e):
    global direction
    if e.type == pygame.KEYDOWN:
        d = {pygame.K_UP: Direction.UP, pygame.K_DOWN: Direction.DOWN, pygame.K_LEFT: Direction.LEFT, pygame.K_RIGHT: Direction.RIGHT}
        if e.key in d:
            reverse = {Direction.DOWN: Direction.UP, Direction.UP: Direction.DOWN, Direction.RIGHT: Direction.LEFT, Direction.LEFT: Direction.RIGHT}
            if reverse[d[e.key]] != direction[0]:
                direction[1] = d[e.key]


def move_towards(current, target, speed):
    if current < target:
        return current + 2
    elif current > target:
        return current - 2
    return current

def move_snake():
    global last_move, head_pos
    game_speed = min(14, 10+(score//4))

    head.x = move_towards(head.x, head_pos[0] * block_size, game_speed)
    head.y = move_towards(head.y, head_pos[1] * block_size, game_speed)
    tail.x = move_towards(tail.x, snake[0][0] * block_size, game_speed)
    tail.y = move_towards(tail.y, snake[0][1] * block_size, game_speed)

    if time.time() - last_move > 1/game_speed:
        direction[0] = direction[1]
        head_pos = tuple_sum(tuple(snake[len(snake)-1]),direction[0].value)
        if not add_snake(*head_pos):
            map[snake[0][0]][snake[0][1]][1] = Item.WHITE
            del snake[0]
        last_move = time.time()

while not endgame:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            endgame = True
        dir_snake(e)
    if lose:
        game_over = pygame.Surface(screen_size, pygame.SRCALPHA)
        game_over.fill((0, 0, 0, 120))
        text = font.render(f"  Game Over   ", False, "#FFFFFF")
        score_text = font.render(f"Pontuação: {score:3}", False, "#FFFFFF")
        screen.blit(game_over, (0,0))
        screen.blit(text, (290,340))
        screen.blit(score_text, (290,355))
        if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
            restart_game()
    else:
        move_snake()
        draw_game()
    pygame.display.flip()
    pygame.time.wait(1)
pygame.quit()