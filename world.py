"""
world.py — Gestión de chunks, generación de objetos, agua y agricultura.
"""
import os
import random
import pygame
import constants
from elements import Tree, SmallStone, Farmland, Water


class World:
    def __init__(self, width, height, start_x=0, start_y=0):
        self.view_width  = width
        self.view_height = height
        self.chunk_size  = constants.CHUNK_SIZE
        self.active_chunks   = {}
        self.inactive_chunks = {}
        self.current_time    = constants.MORNING_TIME

        grass_path = os.path.join('assets','images','objects','grass.png')
        try:
            img = pygame.image.load(grass_path).convert_alpha()
            self.grass_image = pygame.transform.scale(
                img, (constants.GRASS_SIZE, constants.GRASS_SIZE))
        except Exception:
            self.grass_image = pygame.Surface(
                (constants.GRASS_SIZE, constants.GRASS_SIZE), pygame.SRCALPHA)
            self.grass_image.fill((34,139,34))

        self.day_overlay = pygame.Surface((width, height), pygame.SRCALPHA)

        sc = self.get_chunk_coords(start_x, start_y)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                self.generate_chunk(sc[0]+dx, sc[1]+dy)

    # ── Tiempo ────────────────────────────────────────────────────────────────
    def update_time(self, dt):
        self.current_time = (self.current_time + dt) % constants.DAY_LENGTH

    # ── Chunks ────────────────────────────────────────────────────────────────
    def get_chunk_coords(self, x, y):
        return (int(x) // self.chunk_size, int(y) // self.chunk_size)

    def generate_chunk(self, cx, cy):
        key = (cx, cy)
        if key in self.active_chunks:
            return self.active_chunks[key]
        if key in self.inactive_chunks:
            chunk = self.inactive_chunks.pop(key)
            self.active_chunks[key] = chunk
            return chunk
        chunk = Chunk(cx, cy)
        self.active_chunks[key] = chunk
        return chunk

    def update_chunks(self, px, py, radius=2):
        pc = self.get_chunk_coords(px, py)
        needed = {(pc[0]+dx, pc[1]+dy)
                  for dx in range(-radius, radius+1)
                  for dy in range(-radius, radius+1)}
        for c in needed:
            if c not in self.active_chunks:
                self.generate_chunk(*c)
        for c in [k for k in list(self.active_chunks) if k not in needed]:
            self.inactive_chunks[c] = self.active_chunks.pop(c)

    # ── Agua ──────────────────────────────────────────────────────────────────
    def update_water(self, dt):
        for chunk in self.active_chunks.values():
            for w in chunk.water_tiles.values():
                w.update(dt)

    def is_water_at(self, x, y) -> bool:
        tx = (int(x) // constants.GRASS_SIZE) * constants.GRASS_SIZE
        ty = (int(y) // constants.GRASS_SIZE) * constants.GRASS_SIZE
        coords = self.get_chunk_coords(tx, ty)
        chunk  = self.active_chunks.get(coords)
        return chunk is not None and (tx, ty) in chunk.water_tiles

    def water_adjacent(self, tile_x, tile_y) -> bool:
        """
        True si alguno de los 4 tiles directamente adyacentes al farmland es agua.
        tile_x, tile_y: coordenadas ya alineadas a la grilla (múltiplos de GRASS_SIZE).
        """
        step = constants.GRASS_SIZE
        for dx, dy in ((step,0),(-step,0),(0,step),(0,-step)):
            if self.is_water_at(tile_x + dx, tile_y + dy):
                return True
        return False

    def water_nearby(self, x, y, radius=None) -> bool:
        """Mantener por compatibilidad — usa adjacency."""
        tx = (int(x) // constants.GRASS_SIZE) * constants.GRASS_SIZE
        ty = (int(y) // constants.GRASS_SIZE) * constants.GRASS_SIZE
        return self.water_adjacent(tx, ty)

    # ── Agricultura ───────────────────────────────────────────────────────────
    def update_farms(self, dt):
        """
        Actualiza todos los farmlands.
        Regado = tile adyacente a agua O jugador lo regó manualmente (fl.is_watered_by_player).
        """
        for chunk in self.active_chunks.values():
            for fl in chunk.farmlands:
                adj_water = self.water_adjacent(fl.x, fl.y)
                # is_watered_by_player se setea en character.water_farmland()
                # y dura FARM_MANUAL_WATER_DURATION ms
                manual = getattr(fl, '_manual_water_timer', 0) > 0
                if manual:
                    fl._manual_water_timer = max(0, fl._manual_water_timer - dt)
                has_water = adj_water or manual
                fl.update(dt, has_water)

    def add_farmland(self, x, y) -> bool:
        """Crea un tile de farmland en la posición alineada a la grilla."""
        tx = (int(x) // constants.GRASS_SIZE) * constants.GRASS_SIZE
        ty = (int(y) // constants.GRASS_SIZE) * constants.GRASS_SIZE
        coords = self.get_chunk_coords(tx, ty)
        if coords not in self.active_chunks:
            self.generate_chunk(*coords)
        chunk = self.active_chunks[coords]
        key   = (tx, ty)
        # No crear sobre agua
        if key in chunk.water_tiles:
            return False
        for f in chunk.farmlands:
            if f.x == tx and f.y == ty:
                return False   # ya existe
        chunk.farmlands.append(Farmland(tx, ty))
        return True

    def get_farmland_at(self, x, y):
        """Devuelve el Farmland en la posición (x,y) o None."""
        tx = (int(x) // constants.GRASS_SIZE) * constants.GRASS_SIZE
        ty = (int(y) // constants.GRASS_SIZE) * constants.GRASS_SIZE
        coords = self.get_chunk_coords(tx, ty)
        chunk  = self.active_chunks.get(coords)
        if chunk is None:
            return None
        for f in chunk.farmlands:
            if f.x == tx and f.y == ty:
                return f
        return None

    # ── Dibujado ──────────────────────────────────────────────────────────────
    def draw(self, screen, camera_x, camera_y):
        # 1. Pasto continuo cubriendo toda la pantalla
        tile   = constants.GRASS_SIZE
        cam_ix = int(camera_x)
        cam_iy = int(camera_y)
        for tx in range(cam_ix // tile, (cam_ix + constants.WIDTH)  // tile + 2):
            for ty in range(cam_iy // tile, (cam_iy + constants.HEIGHT) // tile + 2):
                screen.blit(self.grass_image, (tx*tile - cam_ix - 1, ty*tile - cam_iy - 1))

        # 2. Objetos de chunks
        for chunk in self.active_chunks.values():
            chunk.draw(screen, camera_x, camera_y)

        # 3. Overlay día/noche
        t = self.current_time
        if constants.MORNING_TIME <= t < constants.DUSK_TIME:
            pass
        elif constants.DAWN_TIME <= t < constants.MORNING_TIME:
            prog  = (t-constants.DAWN_TIME)/(constants.MORNING_TIME-constants.DAWN_TIME)
            alpha = int(constants.MAX_DARKNESS*(1-prog))
            self.day_overlay.fill((*constants.DAWN_DUSK_COLOR, alpha))
            screen.blit(self.day_overlay, (0,0))
        elif constants.DUSK_TIME <= t < constants.MIDNIGHT_TIME:
            prog  = (t-constants.DUSK_TIME)/(constants.MIDNIGHT_TIME-constants.DUSK_TIME)
            alpha = int(constants.MAX_DARKNESS*prog)
            self.day_overlay.fill((*constants.DAWN_DUSK_COLOR, alpha))
            screen.blit(self.day_overlay, (0,0))
        else:
            self.day_overlay.fill((*constants.BLACK, constants.MAX_DARKNESS))
            screen.blit(self.day_overlay, (0,0))


class Chunk:
    def __init__(self, chunk_x, chunk_y):
        self.chunk_x     = chunk_x
        self.chunk_y     = chunk_y
        self.trees        = []
        self.small_stones = []
        self.farmlands    = []
        self.water_tiles  = {}   # (wx, wy) → Water

        bx  = chunk_x * constants.CHUNK_SIZE
        by  = chunk_y * constants.CHUNK_SIZE
        w = h = constants.CHUNK_SIZE
        rng = random.Random(hash((chunk_x, chunk_y)))

        # Agua (lago circular)
        if rng.random() < constants.WATER_GENERATION_PROBABILITY:
            cx = bx + rng.randint(0, w)
            cy = by + rng.randint(0, h)
            radius = rng.randint(3, 8) * constants.GRASS_SIZE
            step   = constants.GRASS_SIZE
            for yo in range(-int(radius), int(radius)+1, step):
                for xo in range(-int(radius), int(radius)+1, step):
                    if xo**2 + yo**2 <= radius**2:
                        gx = ((cx+xo) // step) * step
                        gy = ((cy+yo) // step) * step
                        if bx <= gx < bx+w and by <= gy < by+h:
                            self.water_tiles[(gx, gy)] = Water(gx, gy)

        def _tiles_for(ox, oy, size):
            """Devuelve todos los tiles de grilla que cubre un objeto de tamaño 'size'."""
            step = constants.GRASS_SIZE
            tiles = set()
            for dx in range(0, size + step, step):
                for dy in range(0, size + step, step):
                    gx = ((ox + dx) // step) * step
                    gy = ((oy + dy) // step) * step
                    tiles.add((gx, gy))
            return tiles

        def _overlaps_water(ox, oy, size):
            return bool(_tiles_for(ox, oy, size) & self.water_tiles.keys())

        # Árboles (evitan TODOS los tiles de agua que cubrirían)
        for _ in range(rng.randint(2, 5)):
            for _ in range(50):
                tx = bx + rng.randint(0, w - constants.TREE_SIZE)
                ty = by + rng.randint(0, h - constants.TREE_SIZE)
                if not _overlaps_water(tx, ty, constants.TREE_SIZE):
                    self.trees.append(Tree(tx, ty))
                    break

        # Piedras (evitan TODOS los tiles de agua que cubrirían)
        for _ in range(rng.randint(1, 3)):
            for _ in range(50):
                sx = bx + rng.randint(0, w - constants.SMALL_STONE_SIZE)
                sy = by + rng.randint(0, h - constants.SMALL_STONE_SIZE)
                if not _overlaps_water(sx, sy, constants.SMALL_STONE_SIZE):
                    self.small_stones.append(SmallStone(sx, sy))
                    break

    def draw(self, screen, camera_x, camera_y, grass_image=None):
        # Farmlands (reemplazan pasto)
        for fl in self.farmlands:
            fl.draw(screen, camera_x, camera_y)
        # Agua
        for w in self.water_tiles.values():
            w.draw(screen, camera_x, camera_y)
        # Sólidos
        for tree in self.trees:
            tree.draw(screen, camera_x, camera_y)
        for stone in self.small_stones:
            stone.draw(screen, camera_x, camera_y)