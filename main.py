import game
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    map_size: int = 20              # células por lado de cada tabuleiro
    cell_size: int = 260            # tamanho (px) de cada mini-tabuleiro na janela
    board_gap: int = 4              # espaço (px) entre os tabuleiros
    game_count: int = 16            # quantidade de jogos simultâneos
    grid_columns: Optional[int] = None  # None = calculado automaticamente (quase quadrado)
    fps_cap: int = 240              # limite de quadros DESENHADOS por segundo
    instant_play_again: bool = True

    ai_enabled: bool = True         # cobra controlada pela IA (Dijkstra)
    show_ai_path: bool = False      # pinta no mapa o caminho calculado pela IA (custa mais caro)

    steps_per_frame: int = 200      # passos de lógica por quadro desenhado (velocidade principal)
    alt_steps_per_frame: int = 1    # velocidade alternativa (tecla espaço)
    animate_movement: bool = False  # anima suavemente célula a célula (desative p/ velocidade máxima)
    animation_step_px: int = 3      # pixels por quadro na animação (só usado se animate_movement=True)

    max_step_seconds_per_frame: float = 1 / 30  # teto de tempo gasto processando passos por quadro;
                                                 # garante que a janela nunca pareça travada, mesmo
                                                 # se o tabuleiro estiver cheio e a IA ficar mais lenta
    ai_apple_recheck_interval: int = 15         # quando a maçã está inacessível (tabuleiro cheio), só
                                                 # tenta de novo a cada N passos em vez de todo passo —
                                                 # provar que não há caminho é o pior caso do Dijkstra

    color_bg: str = "#000000"
    color_snake_body: str = "#00a50e"
    color_apple: str = "#ff0000"
    color_ai_path: str = "#c0cdf0"
    color_tile_light: str = "#dbe5ff"
    color_tile_dark: str = "#d3ddf8"
    color_hud_text: str = "#ffffff"
    color_hud_bg: tuple = (0, 0, 0, 120)

    @property
    def block_size(self) -> int:
        return self.cell_size // self.map_size

    @property
    def columns(self) -> int:
        return self.grid_columns or math.ceil(math.sqrt(self.game_count))

    @property
    def rows(self) -> int:
        return math.ceil(self.game_count / self.columns)

    @property
    def window_width(self) -> int:
        return self.columns * self.cell_size + (self.columns + 1) * self.board_gap

    @property
    def window_height(self) -> int:
        return self.rows * self.cell_size + (self.rows + 1) * self.board_gap

def start():
    game.Manager(Config()).run()

if __name__ == "__main__":
    start()