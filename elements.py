"""
elements.py — Objetos del mundo: árbol, piedra, farmland, agua, cultivos.
"""
import math
import os
import pygame
import constants


# ── Utilidad: carga segura de imagen ─────────────────────────────────────────
def _load(path, fallback_color=(180, 60, 180), size=None):
    try:
        surf = pygame.image.load(path).convert_alpha()
        if size:
            surf = pygame.transform.scale(surf, size)
        return surf
    except Exception:
        w, h = size if size else (32, 32)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((*fallback_color, 200))
        return s


# ── Árbol ─────────────────────────────────────────────────────────────────────
class Tree:
    def __init__(self, x, y, size=constants.TREE_SIZE):
        self.x = x
        self.y = y
        self.size = size
        self.wood = 5
        self.rect = pygame.Rect(
            int(self.x + constants.TREE_SIZE / 2.5),
            self.y + 7,
            int(constants.TREE_SIZE / 1.5),
            constants.TREE_SIZE - 40
        )
        self.image = _load(
            os.path.join("assets","images","objects","tree.png"),
            (0,120,0),
            (constants.TREE_IMAGE_SIZE, constants.TREE_IMAGE_SIZE)
        )

    def draw(self, screen, camera_x, camera_y):
        sx = self.x - camera_x
        sy = self.y - camera_y
        if -self.size <= sx <= constants.WIDTH and -self.size <= sy <= constants.HEIGHT:
            screen.blit(self.image, (sx, sy + self.size - self.image.get_height()))

    def chop(self, with_axe=False):
        if self.wood > 0:
            self.wood -= 2 if with_axe else 1
            if self.wood <= 0:
                self.wood = 0
                return "destroyed"
            return "chopped"
        return "empty"


# ── Piedra ────────────────────────────────────────────────────────────────────
class SmallStone:
    def __init__(self, x, y, size=constants.SMALL_STONE_SIZE):
        self.x = x
        self.y = y
        self.size = size
        self.stone = 3
        self.rect = pygame.Rect(
            self.x + constants.STONE_IMAGE_SIZE // 3,
            self.y + constants.STONE_IMAGE_SIZE - 10,
            constants.STONE_IMAGE_SIZE // 3,
            10
        )
        self.image = _load(
            os.path.join("assets","images","objects","small_stone.png"),
            (150,150,150),
            (constants.STONE_IMAGE_SIZE, constants.STONE_IMAGE_SIZE)
        )

    def draw(self, screen, camera_x, camera_y):
        sx = self.x - camera_x
        sy = self.y - camera_y
        if -self.size <= sx <= constants.WIDTH and -self.size <= sy <= constants.HEIGHT:
            screen.blit(self.image, (sx, sy + self.size - self.image.get_height()))

    def mine(self):
        if self.stone > 0:
            self.stone -= 1
            return True
        return False


# ── Agua ──────────────────────────────────────────────────────────────────────
class Water:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = constants.WATER_SIZE
        self.rect = pygame.Rect(x, y, self.size, self.size)
        self.animation_frame = 0.0
        self._surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        self._surf.fill(constants.WATER_COLOR)

    def update(self, dt):
        self.animation_frame += dt * 0.003

    def draw(self, screen, camera_x, camera_y):
        sx = self.x - camera_x
        sy = self.y - camera_y
        if -self.size <= sx <= constants.WIDTH and -self.size <= sy <= constants.HEIGHT:
            oy = int(math.sin(self.animation_frame) * 2)
            screen.blit(self._surf, (sx, sy + oy))


# ── Farmland con sistema de cultivo ───────────────────────────────────────────
class Farmland:
    """
    Tile de tierra cultivable (GRASS_SIZE × GRASS_SIZE).

    Estados de cada tile:
      - empty      : farmland vacío, espera semillas
      - planted    : sembrado (fase 0), necesita agua para crecer
      - growing    : fases 1-4 de crecimiento (se pausa sin agua cerca)
      - ready      : fase 5, listo para cosechar
      - harvested  : cosechado, vuelve a 'empty' tras un momento
    """

    # Imágenes compartidas entre todas las instancias (cargadas 1 sola vez)
    _img_base   = None   # fondo farmland
    _img_sign   = None   # cartel zanahoria
    _img_phases = None   # lista de 4 superficies (fases 1-4)
    _img_wet    = None   # overlay húmedo
    _img_dry    = None   # overlay seco

    @classmethod
    def _ensure_images(cls):
        if cls._img_base is not None:
            return
        ts = constants.GRASS_SIZE   # 50 px

        cls._img_base = _load(constants.IMG_FARMLAND,     (120,80,40),  (ts, ts))

        # Cartel: dibujarlo más grande encima del tile (ancho=tile, alto proporcional)
        sign_raw = _load(constants.IMG_CROP_SIGN_CARROT, (80,60,20))
        sw, sh   = sign_raw.get_size()
        ratio    = sh / sw if sw > 0 else 1
        sign_w   = ts
        sign_h   = max(12, int(sign_w * ratio))
        cls._img_sign = pygame.transform.scale(sign_raw, (sign_w, sign_h))

        # 4 fases de crecimiento — caben 4 columnas × 2 filas dentro del tile
        cell_w = ts // constants.FARM_GRID_COLS   # 12 px
        cell_h = ts // constants.FARM_GRID_ROWS   # 25 px
        cls._img_phases = []
        for path in constants.IMG_CARROT_PHASES:
            raw = _load(path, (0, 200, 80))
            cls._img_phases.append(
                pygame.transform.scale(raw, (cell_w, cell_h))
            )

        # Overlays de humedad
        cls._img_wet = pygame.Surface((ts, ts), pygame.SRCALPHA)
        cls._img_wet.fill(constants.FARM_WET_COLOR)
        cls._img_dry = pygame.Surface((ts, ts), pygame.SRCALPHA)
        cls._img_dry.fill(constants.FARM_DRY_COLOR)

    def __init__(self, x, y):
        Farmland._ensure_images()
        self.x    = x
        self.y    = y
        self.size = constants.GRASS_SIZE

        # ── Estado del cultivo ────────────────────────────────────────────────
        self.crop_type   = "carrot"          # extensible a otros cultivos
        self.state       = "empty"           # empty | planted | growing | ready | harvested
        self.phase       = 0                 # 0-5
        self.seeds_count = 0                 # semillas sembradas (0-8)
        self.is_watered  = False             # ¿tiene agua cerca ahora mismo?
        self._growth_timer = 0               # ms acumulados desde último riego

        # Timer para volver de 'harvested' a 'empty'
        self._harvest_reset_timer = 0
        self._manual_water_timer = 0    # ms restantes de riego manual (tecla E)

    # ── Siembra ──────────────────────────────────────────────────────────────
    def plant(self, seeds_available: int) -> int:
        """
        Siembra seeds_available semillas (hasta FARM_SEEDS_PER_TILE).
        Devuelve cuántas semillas se usaron.
        """
        if self.state != "empty":
            return 0
        to_plant = min(seeds_available, constants.FARM_SEEDS_PER_TILE)
        if to_plant <= 0:
            return 0
        self.seeds_count = to_plant
        self.state       = "planted"
        self.phase       = constants.FARM_PHASE_PLANTED
        self._growth_timer = 0
        return to_plant

    # ── Cosecha ───────────────────────────────────────────────────────────────
    def harvest_one(self) -> int:
        """
        Cosecha 1 zanahoria del tile. El tile sigue en 'ready' hasta agotar las 8.
        Devuelve 1 si cosechó, 0 si no había nada.
        """
        if self.state != "ready":
            return 0
        self.seeds_count -= 1
        if self.seeds_count <= 0:
            # Tile completamente cosechado
            self.seeds_count          = 0
            self.state                = "harvested"
            self._harvest_reset_timer = 2000   # 2 s y vuelve a empty
            self.phase                = 0
        return 1

    def harvest(self) -> int:
        """Alias: cosecha todo el tile de una vez (para compatibilidad)."""
        total = 0
        while self.state == "ready":
            total += self.harvest_one()
        return total

    # ── Actualización ─────────────────────────────────────────────────────────
    def update(self, dt: int, water_nearby: bool):
        """
        dt: milisegundos desde el último frame.
        water_nearby: True si hay un tile de agua dentro del radio definido.
        """
        self.is_watered = water_nearby

        # Reset a empty tras cosecha
        if self.state == "harvested":
            self._harvest_reset_timer -= dt
            if self._harvest_reset_timer <= 0:
                self.state = "empty"
            return

        if self.state not in ("planted", "growing"):
            return

        # Solo crece si hay agua cerca
        if not self.is_watered:
            return

        self._growth_timer += dt
        if self._growth_timer >= constants.FARM_GROWTH_TIME_MS:
            self._growth_timer -= constants.FARM_GROWTH_TIME_MS
            self.phase += 1
            if self.phase >= constants.FARM_PHASE_READY:
                self.phase = constants.FARM_PHASE_READY
                self.state = "ready"
            else:
                self.state = "growing"

    # ── Dibujado ─────────────────────────────────────────────────────────────
    def draw(self, screen, camera_x, camera_y):
        sx = self.x - camera_x
        sy = self.y - camera_y
        ts = constants.GRASS_SIZE
        if sx + ts < 0 or sx > constants.WIDTH or sy + ts < 0 or sy > constants.HEIGHT:
            return

        # 1. Fondo farmland
        screen.blit(self._img_base, (sx, sy))

        # 2. Overlay húmedo/seco (solo si hay algo sembrado)
        if self.state in ("planted", "growing", "ready"):
            screen.blit(self._img_wet if self.is_watered else self._img_dry, (sx, sy))

        # 3. Plantas en la grilla 4×2
        if self.state in ("growing", "ready") and self.phase >= 1:
            phase_idx   = min(self.phase - 1, len(self._img_phases) - 1)
            plant_surf  = self._img_phases[phase_idx]
            cell_w      = ts // constants.FARM_GRID_COLS
            cell_h      = ts // constants.FARM_GRID_ROWS
            for i in range(self.seeds_count):
                col = i % constants.FARM_GRID_COLS
                row = i // constants.FARM_GRID_COLS
                px  = sx + col * cell_w + (cell_w - plant_surf.get_width())  // 2
                py  = sy + row * cell_h + (cell_h - plant_surf.get_height()) // 2
                screen.blit(plant_surf, (px, py))

        # 4. Cartel cuando hay cultivo activo (encima del tile, desplazado hacia arriba)
        if self.state in ("planted", "growing", "ready"):
            sign_x = sx + (ts - self._img_sign.get_width()) // 2
            sign_y = sy - self._img_sign.get_height() - 2
            screen.blit(self._img_sign, (sign_x, sign_y))

        # 5. Barra de progreso de crecimiento (debajo del tile)
        if self.state in ("planted", "growing") and self.is_watered:
            bar_w   = ts - 4
            bar_h   = 4
            bx      = sx + 2
            by      = sy + ts + 2
            # progreso dentro de la fase actual
            progress = self._growth_timer / constants.FARM_GROWTH_TIME_MS
            pygame.draw.rect(screen, (50, 50, 50),   (bx, by, bar_w, bar_h))
            pygame.draw.rect(screen, (80, 220, 80),  (bx, by, int(bar_w * progress), bar_h))

        # 6. Indicador "LISTO" cuando está para cosechar
        if self.state == "ready":
            font = pygame.font.SysFont(None, 16)
            txt  = font.render("✓", True, (255, 255, 80))
            screen.blit(txt, (sx + ts // 2 - txt.get_width() // 2, sy - 14))