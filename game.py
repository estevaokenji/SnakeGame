import pygame, random, heapq
from enum import Enum
from main import Config

class Tile(Enum):
    EMPTY = " "
    BODY = "O"
    HEAD = "o"
    APPLE = "A"

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)
    NONE = (0, 0)

OPPOSITE_DIRECTION = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}

KEY_TO_DIRECTION = {
    pygame.K_UP: Direction.UP,
    pygame.K_DOWN: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT,
}

def tuple_add(a: tuple, b: tuple) -> tuple:
    return (a[0] + b[0], a[1] + b[1])

class SnakeGame:
    """Uma partida independente. Não possui janela própria: recebe uma
    posição (`origin`) dentro de uma janela compartilhada e desenha ali."""

    def __init__(self, config: Config, game_id: int, origin: tuple[int, int], font: pygame.font.Font):
        self.config = config
        self.game_id = game_id
        self.origin = origin
        self.font = font

        self.map_size = config.map_size
        self.block_size = config.block_size

        self.score = 0
        self.game_over = False
        self.snake_body: list[tuple[int, int]] = []
        self.apple_pos: tuple[int, int] = (0, 0)
        self.grid: list[list[Tile]] = []

        self.current_direction = Direction.NONE
        self.next_direction = Direction.UP

        self.ai_enabled = config.ai_enabled
        self.show_ai_path = config.show_ai_path
        self.ai_path: list[tuple[int, int]] = []
        self._apple_reachable = True
        self._steps_since_apple_check = 0
        self.instant_play_again = config.instant_play_again

        # posições (relativas ao próprio tabuleiro) da cabeça/cauda,
        # usadas só quando animate_movement=True
        self.head_rect = pygame.Rect(0, 0, self.block_size, self.block_size)
        self.tail_rect = pygame.Rect(0, 0, self.block_size, self.block_size)
        self.head_target_cell = (0, 0)

        # controle de redesenho: evita redesenhar células que não mudaram
        self.dirty_cells: set[tuple[int, int]] = set()
        self.needs_full_redraw = True

        # HUD pré-renderizado uma única vez (evita criar Surface por quadro)
        self._hud_bg = pygame.Surface((40, 20), pygame.SRCALPHA)
        self._hud_bg.fill(config.color_hud_bg)

        self.reset()
        self.log("Novo jogo iniciado.")

    def log(self, message: str):
        print(f"[Jogo #{self.game_id}] {message}")

    def reset(self):
        self.score = 0
        self.game_over = False
        self.snake_body = []
        self.current_direction = Direction.NONE
        self.next_direction = Direction.UP
        self.ai_path = []
        self._apple_reachable = True
        self._steps_since_apple_check = 0
        self.grid = [[Tile.EMPTY for _ in range(self.map_size)] for _ in range(self.map_size)]
        self.dirty_cells.clear()
        self.needs_full_redraw = True
        self._spawn_snake()
        self._spawn_apple()

    # --------------------------------------------------------
    # Criação de elementos no mapa
    # --------------------------------------------------------
    def _random_empty_cell(self) -> tuple[int, int]:
        while True:
            x = random.randint(0, self.map_size - 1)
            y = random.randint(0, self.map_size - 1)
            if self.grid[x][y] == Tile.EMPTY:
                return x, y

    def _cell_to_local_pixels(self, cell: tuple[int, int]) -> tuple[int, int]:
        return (cell[0] * self.block_size, cell[1] * self.block_size)

    def _place_initial_segment(self, x: int, y: int):
        self.grid[x][y] = Tile.HEAD
        if self.snake_body:
            prev_x, prev_y = self.snake_body[-1]
            self.grid[prev_x][prev_y] = Tile.BODY
        self.snake_body.append((x, y))

    def _spawn_snake(self):
        x, _ = self._random_empty_cell()
        tail_cell = (x, self.map_size - 1)
        head_cell = (x, self.map_size - 2)
        self._place_initial_segment(*tail_cell)
        self._place_initial_segment(*head_cell)
        self.tail_rect.topleft = self._cell_to_local_pixels(tail_cell)
        self.head_rect.topleft = self._cell_to_local_pixels(head_cell)
        self.head_target_cell = head_cell

    def _spawn_apple(self):
        x, y = self._random_empty_cell()
        self.grid[x][y] = Tile.APPLE
        self.apple_pos = (x, y)
        self.dirty_cells.add((x, y))

    # --------------------------------------------------------
    # Lógica de movimento (um passo discreto, sem relação com tempo real)
    # --------------------------------------------------------
    def _advance_head(self, x: int, y: int) -> bool:
        """Move a cabeça para (x, y). Retorna True se uma maçã foi comida
        (nesse caso a cauda não deve ser removida neste passo)."""
        if not (0 <= x < self.map_size and 0 <= y < self.map_size):
            self._end_game("colidiu com a borda do mapa")
            return False

        tile = self.grid[x][y]
        moving_into_own_tail = bool(self.snake_body) and (x, y) == self.snake_body[0]
        if tile == Tile.BODY and not moving_into_own_tail:
            self._end_game("colidiu com o próprio corpo")
            return False

        ate_apple = tile == Tile.APPLE
        self.grid[x][y] = Tile.HEAD
        self.dirty_cells.add((x, y))
        if self.snake_body:
            prev_x, prev_y = self.snake_body[-1]
            self.grid[prev_x][prev_y] = Tile.BODY
            self.dirty_cells.add((prev_x, prev_y))
        self.snake_body.append((x, y))

        if ate_apple:
            self.score += 1
            if self.score+2 == self.map_size**2:
                self._end_game("ganhou")
            if not self.game_over:
                self._spawn_apple()

        return ate_apple

    def _end_game(self, reason: str):
        self.game_over = True
        self.log(f"Fim de jogo ({reason}). Pontuação final: {self.score}")

    def _decide_next_head_position(self) -> tuple[int, int]:
        if self.ai_enabled or self.show_ai_path:
            self.ai_path = self.find_path(self.snake_body[-1], self.apple_pos)
            if not self.ai_path:
                # Sem caminho até a maçã: persegue a própria cauda para
                # ganhar espaço em vez de travar.
                self.ai_path = self.find_path(self.snake_body[-1], self.snake_body[0])

        if self.ai_path and self.ai_enabled:
            return self.ai_path[0]
        return tuple_add(self.snake_body[-1], self.current_direction.value)

    def step(self):
        """Executa exatamente um passo de lógica (sem gatilho de tempo real
        e sem animação — isso é o que permite rodar centenas de passos por
        segundo independente da taxa de quadros desenhados)."""
        if self.game_over:
            if self.instant_play_again:
                self.reset()
            return

        self.current_direction = self.next_direction

        if self.show_ai_path and self.ai_path:
            self.dirty_cells.update(self.ai_path)  # apaga highlight antigo
        self.head_target_cell = self._decide_next_head_position()
        if self.show_ai_path and self.ai_path:
            self.dirty_cells.update(self.ai_path)  # pinta highlight novo

        ate_apple = self._advance_head(*self.head_target_cell)

        if not self.game_over and not ate_apple:
            old_tail = self.snake_body.pop(0)
            self.grid[old_tail[0]][old_tail[1]] = Tile.EMPTY
            self.dirty_cells.add(old_tail)

    def _lerp(self, current: int, target: int, step: int) -> int:
        if current < target:
            return min(current + step, target)
        if current > target:
            return max(current - step, target)
        return current

    def animate(self):
        """Interpola suavemente a posição visual da cabeça/cauda. Só chamar
        quando Config.animate_movement=True (custa uma redraw completa)."""
        step = self.config.animation_step_px
        self.head_rect.x = self._lerp(self.head_rect.x, self.head_target_cell[0] * self.block_size, step)
        self.head_rect.y = self._lerp(self.head_rect.y, self.head_target_cell[1] * self.block_size, step)
        self.tail_rect.x = self._lerp(self.tail_rect.x, self.snake_body[0][0] * self.block_size, step)
        self.tail_rect.y = self._lerp(self.tail_rect.y, self.snake_body[0][1] * self.block_size, step)

    # --------------------------------------------------------
    # IA (Dijkstra)
    # --------------------------------------------------------
    def _neighbor_candidates(self, x: int, y: int) -> list[tuple[int, int]]:
        """Vizinhos de uma célula. Com IA ativa, retorna só 2 candidatos
        numa ordem que favorece um padrão de varredura em zigue-zague,
        reduzindo a chance de a cobra se prender em becos sem saída."""
        if not self.ai_enabled:
            return [(x, y + 1), (x, y - 1), (x - 1, y), (x + 1, y)]
        vertical = (x, y + 1) if x % 2 == 0 else (x, y - 1)
        horizontal = (x - 1, y) if y % 2 == 0 else (x + 1, y)
        return [vertical, horizontal]

    def find_path(self, start: tuple[int, int], target: tuple[int, int]) -> list[tuple[int, int]]:
        """Dijkstra em grade simples para encontrar o caminho até `target`."""
        distances = {start: 0}
        previous = {}
        queue = [(0, start)]

        while queue:
            cost, current = heapq.heappop(queue)
            if current == target:
                break
            for nx, ny in self._neighbor_candidates(*current):
                if not (0 <= nx < self.map_size and 0 <= ny < self.map_size):
                    continue
                # Só é permitido pisar numa célula ocupada pelo corpo se ela for
                # exatamente o alvo (usado para perseguir a própria cauda, que
                # se move/libera a célula no mesmo instante). Qualquer outra
                # célula do corpo continua intransponível.
                if self.grid[nx][ny] == Tile.BODY and (nx, ny) != target:
                    continue
                new_cost = cost + 1
                neighbor = (nx, ny)
                if neighbor not in distances or new_cost < distances[neighbor]:
                    distances[neighbor] = new_cost
                    previous[neighbor] = current
                    heapq.heappush(queue, (new_cost, neighbor))

        if target not in previous and target != start:
            return []

        path = []
        current = target
        while current != start:
            path.append(current)
            current = previous[current]
        path.reverse()
        return path

    # --------------------------------------------------------
    # Entrada do usuário
    # --------------------------------------------------------
    def handle_key(self, key: int):
        direction = KEY_TO_DIRECTION.get(key)
        if direction and OPPOSITE_DIRECTION[direction] != self.current_direction:
            self.next_direction = direction

    # --------------------------------------------------------
    # Desenho (tudo relativo a self.origin, dentro da janela compartilhada)
    # --------------------------------------------------------
    def _tile_color(self, tile: Tile, x: int, y: int, use_flat_head_color: bool) -> str:
        if tile == Tile.BODY or (use_flat_head_color and tile == Tile.HEAD):
            return self.config.color_snake_body
        if tile == Tile.APPLE:
            return self.config.color_apple
        if self.show_ai_path and (x, y) in self.ai_path:
            return self.config.color_ai_path
        return self.config.color_tile_light if (x + y) % 2 == 0 else self.config.color_tile_dark

    def draw(self, surface: pygame.Surface):
        ox, oy = self.origin
        if self.config.animate_movement:
            self._draw_all_cells(surface, ox, oy, use_flat_head_color=False)
            head = self.head_rect.move(ox, oy)
            tail = self.tail_rect.move(ox, oy)
            pygame.draw.rect(surface, self.config.color_snake_body, head)
            pygame.draw.rect(surface, self.config.color_snake_body, tail)
        else:
            self._draw_dirty_cells(surface, ox, oy)
        self._draw_hud(surface, ox, oy)

    def _draw_all_cells(self, surface, ox, oy, use_flat_head_color: bool):
        for x in range(self.map_size):
            for y in range(self.map_size):
                self._draw_cell(surface, ox, oy, x, y, use_flat_head_color)

    def _draw_dirty_cells(self, surface, ox, oy):
        if self.needs_full_redraw:
            self._draw_all_cells(surface, ox, oy, use_flat_head_color=True)
            self.needs_full_redraw = False
        else:
            for x, y in self.dirty_cells:
                self._draw_cell(surface, ox, oy, x, y, use_flat_head_color=True)
        self.dirty_cells.clear()

    def _draw_cell(self, surface, ox, oy, x, y, use_flat_head_color):
        rect = pygame.Rect(ox + x * self.block_size, oy + y * self.block_size, self.block_size, self.block_size)
        color = self._tile_color(self.grid[x][y], x, y, use_flat_head_color)
        pygame.draw.rect(surface, color, rect)

    def _draw_hud(self, surface: pygame.Surface, ox: int, oy: int):
        text = self.font.render(f"{self.score:3}", False, self.config.color_hud_text)
        surface.blit(self._hud_bg, (ox + 3, oy + 3))
        surface.blit(text, (ox + 6, oy + 5))

class Manager:
    """Dona da ÚNICA janela pygame. Cria e roda várias instâncias de
    SnakeGame lado a lado, num grid, dentro dessa janela."""

    def __init__(self, config: Config):
        self.config = config
        self.steps_per_frame = config.steps_per_frame
        self._alt_steps_per_frame = config.alt_steps_per_frame

        pygame.init()
        self.screen = pygame.display.set_mode((config.window_width, config.window_height))
        pygame.display.set_caption(f"Jogo da Cobrinha - {config.game_count} partidas")
        self.screen.fill(config.color_bg)  # preenchido 1x: os espaços entre tabuleiros não mudam mais
        font = pygame.font.SysFont("Arial", 14)

        self.games: list[SnakeGame] = []
        for i in range(config.game_count):
            col = i % config.columns
            row = i // config.columns
            origin = (
                config.board_gap + col * (config.cell_size + config.board_gap),
                config.board_gap + row * (config.cell_size + config.board_gap),
            )
            self.games.append(SnakeGame(config, i, origin, font))

        print(
            f"[Main] {config.game_count} jogos numa janela {config.window_width}x{config.window_height} "
            f"({config.columns}x{config.rows} tabuleiros de {config.cell_size}px)."
        )
        print(f"[Main] steps_per_frame inicial: {self.steps_per_frame}")

    def _toggle_speed(self):
        self.steps_per_frame, self._alt_steps_per_frame = self._alt_steps_per_frame, self.steps_per_frame
        print(f"[Main] steps_per_frame alternado para {self.steps_per_frame}.")

    def _handle_key(self, key: int):
        if key == pygame.K_SPACE:
            self._toggle_speed()
        elif key == pygame.K_RETURN:
            for game in self.games:
                if game.game_over:
                    game.reset()
        else:
            for game in self.games:
                game.handle_key(key)

    def run(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_key(event.key)

            for _ in range(self.steps_per_frame):
                for game in self.games:
                    game.step()

            if self.config.animate_movement:
                for game in self.games:
                    game.animate()

            for game in self.games:
                game.draw(self.screen)
            pygame.display.flip()

            clock.tick(self.config.fps_cap)

        pygame.quit()
        print("[Main] Encerrado.")