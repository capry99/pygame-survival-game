import os
import math
import pygame
import constants
from constants import *
from inventory import Inventory
from typing import Optional


class Character:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.inventory = Inventory()

        image_path = os.path.join("assets", "images", "character", "Player.png")
        try:
            self.sprite_sheet = pygame.image.load(image_path).convert_alpha()
        except Exception:
            self.sprite_sheet = pygame.Surface((FRAME_SIZE * CUADROS_BASICOS, FRAME_SIZE * 6), pygame.SRCALPHA)

        action_path = os.path.join("assets", "images", "character", "Player_Actions.png")
        try:
            self.action_sprite_sheet = pygame.image.load(action_path).convert_alpha()
        except Exception:
            self.action_sprite_sheet = pygame.Surface((FRAME_SIZE * 2, FRAME_SIZE * 12), pygame.SRCALPHA)

        self.frame_size      = FRAME_SIZE
        self.animation_frame = 0
        self.animation_timer = 0
        self.current_state   = IDLE_DOWN
        self.moving          = False
        self.facing_left     = False
        self.is_running      = False

        # Herramientas
        self.is_chopping  = False
        self.chop_timer   = 0
        self.chop_frame   = 0
        self._chop_cycles = 0

        self.is_hoeing   = False
        self.hoe_frame   = 0
        self.hoe_timer   = 0
        self._hoe_cycles = 0

        self._action_target             = None
        self._action_type: Optional[str] = None

        # Estados
        self.energy  = constants.MAX_ENERGY
        self.food    = constants.MAX_FOOD
        self.thirst  = constants.MAX_THIRST
        self.stamina = constants.MAX_STAMINA

        self.width  = constants.PLAYER
        self.height = constants.PLAYER
        self.rect   = pygame.Rect(self.x, self.y, self.width, self.height)

        self.animations     = self.load_animation()
        self.axe_animations = self.load_axe_animations()
        self.hoe_animations = self.load_hoe_animations()

        self._world = None
        self._last_farm_tile  = None   # evita re-sembrar/cosechar cada frame
        self.hoe_preview_tile = None   # (tx,ty) del tile preview mientras P está apretado

    # ── Sprites ───────────────────────────────────────────────────────────────
    def load_animation(self):
        anims = {}
        for state in range(6):
            frames = []
            for frame in range(CUADROS_BASICOS):
                surf = pygame.Surface((self.frame_size, self.frame_size), pygame.SRCALPHA)
                surf.blit(self.sprite_sheet, (0, 0),
                          (frame * self.frame_size, state * self.frame_size,
                           self.frame_size, self.frame_size))
                frames.append(pygame.transform.scale(surf, (self.width, self.height)))
            anims[state] = frames
        return anims

    def _load_tool_animation(self, row_mapping, total_cols):
        anims = {}
        fw = max(1, self.action_sprite_sheet.get_width()  // total_cols)
        fh = max(1, self.action_sprite_sheet.get_height() // 12)
        for state, row in row_mapping.items():
            frames = []
            for col in range(total_cols):
                src  = pygame.Rect(col * fw, row * fh, fw, fh)
                tmp  = pygame.Surface((fw, fh), pygame.SRCALPHA)
                tmp.blit(self.action_sprite_sheet, (0, 0), src)
                norm = pygame.Surface((self.frame_size, self.frame_size), pygame.SRCALPHA)
                norm.blit(tmp, ((self.frame_size - fw) // 2, (self.frame_size - fh) // 2))
                frames.append(pygame.transform.scale(norm, (self.width, self.height)))
            anims[state] = frames
        return anims

    def load_axe_animations(self):
        return self._load_tool_animation({IDLE_RIGHT: 3, IDLE_DOWN: 4, IDLE_UP: 5}, AXE_COLS)

    def load_hoe_animations(self):
        return self._load_tool_animation({IDLE_RIGHT: 6, IDLE_DOWN: 7, IDLE_UP: 8}, HOE_COLS)

    # ── Animación ─────────────────────────────────────────────────────────────
    def update_animation(self, dt):
        now = pygame.time.get_ticks()

        if self.is_chopping:
            if now - self.chop_timer > AXE_ANIMATION_DELAY:
                self.chop_timer  = now
                self.chop_frame += 1
                if self.chop_frame >= AXE_FRAMES:
                    self.chop_frame    = 0
                    self._chop_cycles += 1
                    if self._action_target is not None:
                        self._execute_action('chop')
                    if self._action_target is None:
                        self.is_chopping  = False
                        self._action_type = None
                        self._chop_cycles = 0

        elif self.is_hoeing:
            if now - self.hoe_timer > HOE_ANIMATION_DELAY:
                self.hoe_timer  = now
                self.hoe_frame += 1
                if self.hoe_frame >= HOE_FRAMES:
                    self.hoe_frame    = 0
                    self._hoe_cycles += 1
                    if self._action_target is not None:
                        self._execute_action('hoe')
                    self.is_hoeing    = False
                    self._action_type = None
                    self._hoe_cycles  = 0
                    self._action_target = None

        else:
            speed = RUNNING_ANIMATION_DELAY if self.is_running else ANIMATION_DELAY
            if now - self.animation_timer > speed:
                self.animation_timer  = now
                self.animation_frame  = (self.animation_frame + 1) % CUADROS_BASICOS

    # ── Dibujo ────────────────────────────────────────────────────────────────
    def _get_tool_frame(self, anim_dict, frame_idx, frames_count):
        safe = frame_idx % frames_count
        st   = self.current_state
        if st in (IDLE_RIGHT, WALK_RIGHT):
            f = anim_dict[IDLE_RIGHT][safe]
            return pygame.transform.flip(f, True, False) if self.facing_left else f
        elif st in (IDLE_UP, WALK_UP):
            return anim_dict[IDLE_UP][safe]
        else:
            return anim_dict[IDLE_DOWN][safe]

    def draw(self, screen, camera_x, camera_y, world=None):
        sx = self.x - camera_x
        sy = self.y - camera_y

        if self.is_chopping:
            frame = self._get_tool_frame(self.axe_animations, self.chop_frame, AXE_FRAMES)
        elif self.is_hoeing:
            frame = self._get_tool_frame(self.hoe_animations, self.hoe_frame, HOE_FRAMES)
        else:
            frame = self.animations[self.current_state][self.animation_frame]
            if self.facing_left:
                frame = pygame.transform.flip(frame, True, False)

        screen.blit(frame, (sx, sy))
        self.draw_status_bars(screen, world)

    # ── Movimiento ────────────────────────────────────────────────────────────
    def is_in_water(self, world) -> bool:
        if world is None:
            return False
        # Comprobar el centro del personaje
        cx = self.x + self.width  // 2
        cy = self.y + self.height // 2
        return world.is_water_at(cx, cy)

    def move(self, dx: float, dy: float, world):
        old_x, old_y = self.x, self.y
        speed = RUN_SPEED if self.is_running and self.stamina > 0 else WALK_SPEED

        # FIX recolección izquierda: multiplicar siempre antes de aplicar
        dx *= speed / WALK_SPEED
        dy *= speed / WALK_SPEED

        # Reducir velocidad en agua
        if self.is_in_water(world):
            dx *= constants.WATER_MOVEMENT_MULTIPLIER
            dy *= constants.WATER_MOVEMENT_MULTIPLIER

        def _collides():
            for chunk in world.active_chunks.values():
                for obj in chunk.trees + chunk.small_stones:
                    if self.rect.colliderect(obj.rect):
                        return True
            return False

        self.x += dx
        self.rect.topleft = (self.x, self.y)
        if _collides():
            self.x = old_x
            self.rect.topleft = (self.x, self.y)

        self.y += dy
        self.rect.topleft = (self.x, self.y)
        if _collides():
            self.y = old_y
            self.rect.topleft = (self.x, self.y)

        if dx != 0 or dy != 0:
            self.moving = True
            if   dx < 0: self.current_state = WALK_RIGHT; self.facing_left = True
            elif dx > 0: self.current_state = WALK_RIGHT; self.facing_left = False
            elif dy < 0: self.current_state = WALK_UP;    self.facing_left = False
            elif dy > 0: self.current_state = WALK_DOWN;  self.facing_left = False
        else:
            self.moving = False
            if   self.current_state in (WALK_DOWN,  IDLE_DOWN):  self.current_state = IDLE_DOWN
            elif self.current_state in (WALK_UP,    IDLE_UP):    self.current_state = IDLE_UP
            elif self.current_state in (WALK_RIGHT, IDLE_RIGHT): self.current_state = IDLE_RIGHT

        if self.moving:
            if self.is_running and self.stamina > 0:
                self.update_stamina(-constants.STAMINA_DECREASE_RATE)
                self.update_energy(-MOVEMENT_ENERGY_COST * 2)
            else:
                self.update_energy(-MOVEMENT_ENERGY_COST)
                self.update_stamina(STAMINA_INCREASE_RATE)

    # ── Interacciones ─────────────────────────────────────────────────────────
    def is_near(self, obj, radius: int = 100) -> bool:
        """
        Compara el centro del personaje con el centro del objeto.
        Usa obj.rect si existe (más preciso), si no usa obj.x/y + size/2.
        Radio 100 cubre el personaje de 100px en cualquier dirección.
        """
        cx = self.x + self.width  // 2
        cy = self.y + self.height // 2
        if hasattr(obj, 'rect'):
            ox = obj.rect.centerx
            oy = obj.rect.centery
        elif hasattr(obj, 'size'):
            ox = obj.x + obj.size // 2
            oy = obj.y + obj.size // 2
        else:
            ox, oy = obj.x, obj.y
        return abs(cx - ox) <= radius and abs(cy - oy) <= radius

    def _target_tile(self):
        """Tile frente al personaje según su dirección."""
        step = constants.GRASS_SIZE
        cx   = self.x + self.width  // 2
        cy   = self.y + self.height // 2
        if self.current_state in (WALK_UP, IDLE_UP):
            tx, ty = cx, cy - self.height
        elif self.current_state in (WALK_DOWN, IDLE_DOWN):
            tx, ty = cx, cy + step
        elif self.current_state in (WALK_RIGHT, IDLE_RIGHT):
            tx = (cx - self.width - step) if self.facing_left else (cx + self.width // 2)
            ty = cy
        else:
            tx, ty = cx, cy + step
        # Alinear a la grilla
        return (tx // step) * step, (ty // step) * step

    def update_hoe_preview(self, p_held: bool):
        """
        Llama cada frame con p_held=True si la tecla P está apretada.
        Actualiza hoe_preview_tile para mostrar dónde irá el farmland.
        Si la pala no está equipada o P no está apretada, limpia el preview.
        """
        if p_held and self.inventory.has_hoe_equipped():
            self.hoe_preview_tile = self._target_tile()
        else:
            self.hoe_preview_tile = None

    def start_hoe(self, world):
        if self.is_hoeing:
            return
        self.is_hoeing     = True
        self.hoe_timer     = pygame.time.get_ticks()
        self.hoe_frame     = 0
        self._hoe_cycles   = 0
        self._action_target = self._target_tile()
        self._action_type  = 'hoe'

    def start_chop(self, world):
        if self.is_chopping:
            return
        for chunk in world.active_chunks.values():
            for tree in chunk.trees:
                if self.is_near(tree):
                    self.is_chopping   = True
                    self.chop_timer    = pygame.time.get_ticks()
                    self.chop_frame    = 0
                    self._chop_cycles  = 0
                    self._action_target = tree
                    self._action_type  = 'chop'
                    return

    def interact(self, world):
        """ESPACIO: recolectar árboles y piedras."""
        # Beber agua (E)
        if self.is_in_water(world):
            self.update_thirst(constants.WATER_THIRST_RECOVERY)
            print(f"[interact] Bebiste agua. Sed: {int(self.thirst)}")
            return

        # Árboles
        for chunk in world.active_chunks.values():
            for tree in chunk.trees:
                if self.is_near(tree):
                    has_axe = self.inventory.has_axe_equipped()
                    if has_axe and not self.is_chopping:
                        self.is_chopping    = True
                        self.chop_timer     = pygame.time.get_ticks()
                        self.chop_frame     = 0
                        self._chop_cycles   = 0
                        self._action_target = tree
                        self._action_type   = 'chop'
                    elif not has_axe:
                        self._action_target = tree
                        self._execute_action('chop')
                    return

        # Piedras
        for chunk in world.active_chunks.values():
            for stone in chunk.small_stones:
                if self.is_near(stone):
                    self._action_target = stone
                    self._execute_action('mine')
                    return

    def _execute_action(self, action_kind: str):
        target = self._action_target
        if target is None:
            return
        world = self._world
        if world is None:
            print("[_execute_action] ERROR: _world no seteado")
            return

        if action_kind == 'chop' and hasattr(target, 'chop'):
            result = target.chop(with_axe=self.inventory.has_axe_equipped())
            if result in ("chopped", "destroyed"):
                self.inventory.add_item("wood", 1)
                print(f"[chop] +1 madera (total {self.inventory.get_quantity('wood')})")
            if result == "destroyed":
                for chunk in world.active_chunks.values():
                    if target in chunk.trees:
                        chunk.trees.remove(target)
                        break
                self._action_target = None

        elif action_kind == 'mine' and hasattr(target, 'mine'):
            if target.mine():
                self.inventory.add_item("stone", 1)
                print(f"[mine] +1 piedra (total {self.inventory.get_quantity('stone')})")
            if getattr(target, 'stone', 0) == 0:
                for chunk in world.active_chunks.values():
                    if target in chunk.small_stones:
                        chunk.small_stones.remove(target)
                        break
                self._action_target = None

        elif action_kind == 'hoe' and isinstance(target, tuple):
            world.add_farmland(target[0], target[1])
            self._action_target = None

    # ── HUD ───────────────────────────────────────────────────────────────────
    def draw_inventory(self, screen, show_inventory=False):
        self.inventory.draw(screen, show_inventory)
        if show_inventory:
            font = pygame.font.Font(None, 22)
            txt  = font.render("I: cerrar inventario", True, constants.WHITE)
            screen.blit(txt, (constants.WIDTH // 2 - txt.get_width() // 2, constants.HEIGHT - 36))

    def update_energy(self, a):  self.energy  = max(0, min(MAX_ENERGY,  self.energy  + a))
    def update_food(self, a):    self.food    = max(0, min(MAX_FOOD,    self.food    + a))
    def update_thirst(self, a):  self.thirst  = max(0, min(MAX_THIRST,  self.thirst  + a))
    def update_stamina(self, a): self.stamina = max(0, min(MAX_STAMINA, self.stamina + a))

    def draw_status_bars(self, screen, world=None):
        bw, bh, sp = 100, 10, 10
        x, y = 10, 10
        font = pygame.font.SysFont(None, 20)

        in_water = self.is_in_water(world)

        for label, val, maxval, color in [
            ("Energía", self.energy,  MAX_ENERGY,  constants.ENERGY_COLOR),
            ("Comida",  self.food,    MAX_FOOD,    constants.FOOD_COLOR),
            ("Sed",     self.thirst,  MAX_THIRST,  constants.THIRST_COLOR),
            ("Stamina", self.stamina, MAX_STAMINA, constants.STAMINA_COLOR),
        ]:
            pygame.draw.rect(screen, constants.BAR_BACKGROUND_COLOR, (x, y, bw, bh))
            pygame.draw.rect(screen, color, (x, y, int(bw * val / maxval), bh))
            screen.blit(font.render(f"{label}: {int(val)}", True, constants.WHITE), (x + bw + 5, y))
            y += bh + sp

        if world is not None:
            tod = (world.current_time / constants.DAY_LENGTH) * 24
            screen.blit(font.render(f"Hora: {int(tod):02d}:00", True, constants.WHITE), (x, y))
            y += bh + sp

        # Indicador agua
        if in_water:
            screen.blit(font.render("En agua — E: beber", True, (100, 200, 255)), (x, y))

    def update_status(self, world=None, dt_seconds: float = 1.0):
        fr = constants.FOOD_DECREASE_RATE   * (RUN_FOOD_DECREASE_MULTIPLIER   if self.is_running else 1)
        tr = constants.THIRST_DECREASE_RATE * (RUN_THIRST_DECREASE_MULTIPLIER if self.is_running else 1)
        self.update_food(-fr * dt_seconds)
        self.update_thirst(-tr * dt_seconds)
        if self.food < MAX_FOOD * 0.2 or self.thirst < MAX_THIRST * 0.2:
            self.update_energy(-constants.ENERGY_DECREASE_RATE * dt_seconds)
        else:
            self.update_energy(constants.ENERGY_INCREASE_RATE * dt_seconds)
        if self.is_running and self.stamina > 0:
            self.update_stamina(-constants.STAMINA_DECREASE_RATE * dt_seconds)
        else:
            self.update_stamina(constants.STAMINA_INCREASE_RATE * dt_seconds)

    # ── Proximidad (FIX: usa centro del personaje, no esquina) ────────────────
    def water_farmland(self, world) -> bool:
        """
        Tecla E cerca de un farmland: riega manualmente ese tile.
        Si hay agua cerca (lago adyacente) bebe; si hay farmland cerca riega.
        """
        # Primero, beber si está en agua
        if self.is_in_water(world):
            self.update_thirst(constants.WATER_THIRST_RECOVERY)
            print(f"[drink] +{constants.WATER_THIRST_RECOVERY} sed")
            return True

        # Regar farmland más cercano dentro de 1 tile de distancia
        step = constants.GRASS_SIZE
        cx   = self.x + self.width  // 2
        cy   = self.y + self.height // 2
        for dx in (-step, 0, step):
            for dy in (-step, 0, step):
                farm = world.get_farmland_at(cx + dx, cy + dy)
                if farm and farm.state in ("planted", "growing"):
                    farm._manual_water_timer = constants.FARM_MANUAL_WATER_DURATION
                    print(f"[water] farmland regado en ({farm.x},{farm.y})")
                    return True
        return False

    def auto_farm_interact(self, world):
        """
        Se llama cada frame desde main.py.
        Si el jugador está parado sobre un farmland:
          - Si está vacío y tiene semillas en inventario → siembra
          - Si está listo → cosecha
        Usa _last_farm_tile para no repetir la acción cada frame.
        """
        # Tile bajo el centro del personaje
        cx = self.x + self.width  // 2
        cy = self.y + self.height // 2
        farm = world.get_farmland_at(cx, cy)

        # Si no hay farmland o es el mismo que el último frame → nada
        current_key = (farm.x, farm.y) if farm else None
        if current_key == self._last_farm_tile:
            return
        self._last_farm_tile = current_key

        if farm is None:
            return

        # Cosechar 1 zanahoria al pararse encima
        if farm.state == "ready":
            count = farm.harvest_one()
            if count > 0:
                self.inventory.add_item(constants.ITEM_CARROT, count)
                remaining = farm.seeds_count
                print(f"[farm] +1 zanahoria cosechada (quedan {remaining} en el tile)")
                # Resetear _last_farm_tile para que el siguiente paso cosecha otra
                self._last_farm_tile = None
            return

        # Sembrar si está vacío y el jugador tiene semillas
        if farm.state == "empty":
            seed_qty = self.inventory.get_quantity(constants.ITEM_CARROT_SEED)
            if seed_qty > 0:
                used = farm.plant(seed_qty)
                if used > 0:
                    # Descontar semillas del inventario
                    self._consume_item(constants.ITEM_CARROT_SEED, used)
                    print(f"[farm] sembradas {used} semillas")

    def _consume_item(self, item_name: str, quantity: int):
        """Consume 'quantity' unidades de item_name del inventario/hotbar."""
        remaining = quantity
        # Hotbar primero
        for slot in self.inventory.hotbar:
            if slot and slot.name == item_name and remaining > 0:
                take = min(slot.quantity, remaining)
                slot.quantity -= take
                remaining    -= take
        # Inventario principal
        for row in self.inventory.inventory:
            for slot in row:
                if slot and slot.name == item_name and remaining > 0:
                    take = min(slot.quantity, remaining)
                    slot.quantity -= take
                    remaining    -= take
        # Limpiar slots vacíos
        for i, slot in enumerate(self.inventory.hotbar):
            if slot and slot.quantity <= 0:
                self.inventory.hotbar[i] = None
        for r, row in enumerate(self.inventory.inventory):
            for c, slot in enumerate(row):
                if slot and slot.quantity <= 0:
                    self.inventory.inventory[r][c] = None

    def is_near(self, obj, radius: int = 90) -> bool:
        """
        FIX: compara usando el CENTRO del personaje vs el CENTRO del objeto.
        Antes usaba self.x (esquina superior izquierda), por eso fallaba
        cuando el jugador estaba a la derecha del objeto.
        """
        cx = self.x + self.width  // 2
        cy = self.y + self.height // 2
        ox = obj.x + (obj.size if hasattr(obj, 'size') else 32) // 2
        oy = obj.y + (obj.size if hasattr(obj, 'size') else 32) // 2
        return abs(cx - ox) <= radius and abs(cy - oy) <= radius

    def is_in_water(self, world) -> bool:
        cx = self.x + self.width  // 2
        cy = self.y + self.height // 2
        return world.is_water_at(cx, cy)

    # ── Tile objetivo de la pala ──────────────────────────────────────────────
    def _target_tile(self):
        """
        FIX: calcula el tile frente al personaje usando su CENTRO,
        alineado a GRASS_SIZE.
        """
        tile = constants.GRASS_SIZE
        cx = self.x + self.width  // 2
        cy = self.y + self.height // 2

        if self.current_state in (WALK_UP, IDLE_UP):
            tx, ty = cx, cy - self.height // 2 - tile
        elif self.current_state in (WALK_DOWN, IDLE_DOWN):
            tx, ty = cx, cy + self.height // 2 + tile // 2
        elif self.current_state in (WALK_RIGHT, IDLE_RIGHT):
            if self.facing_left:
                tx, ty = cx - self.width // 2 - tile, cy
            else:
                tx, ty = cx + self.width // 2 + tile // 2, cy
        else:
            tx, ty = cx, cy + self.height // 2 + tile // 2

        tx = (int(tx) // tile) * tile
        ty = (int(ty) // tile) * tile
        return tx, ty

    # ── Acciones ──────────────────────────────────────────────────────────────
    def update_hoe_preview(self, p_held: bool):
        """
        Llama cada frame con p_held=True si la tecla P está apretada.
        Actualiza hoe_preview_tile para mostrar dónde irá el farmland.
        Si la pala no está equipada o P no está apretada, limpia el preview.
        """
        if p_held and self.inventory.has_hoe_equipped():
            self.hoe_preview_tile = self._target_tile()
        else:
            self.hoe_preview_tile = None

    def start_hoe(self, world):
        if self.is_hoeing:
            return
        self.is_hoeing      = True
        self.hoe_timer      = pygame.time.get_ticks()
        self.hoe_frame      = 0
        self._hoe_cycles    = 0
        self._action_target = self._target_tile()
        self._action_type   = 'hoe'

    def start_chop(self, world):
        if self.is_chopping:
            return
        for chunk in world.active_chunks.values():
            for tree in chunk.trees:
                if self.is_near(tree):
                    self.is_chopping    = True
                    self.chop_timer     = pygame.time.get_ticks()
                    self.chop_frame     = 0
                    self._chop_cycles   = 0
                    self._action_target = tree
                    self._action_type   = 'chop'
                    return

    def interact(self, world):
        """ESPACIO: recolectar árboles y piedras (con o sin herramienta)."""
        for chunk in world.active_chunks.values():
            for tree in chunk.trees:
                if self.is_near(tree):
                    has_axe = self.inventory.has_axe_equipped()
                    if has_axe and not self.is_chopping:
                        self.is_chopping    = True
                        self.chop_timer     = pygame.time.get_ticks()
                        self.chop_frame     = 0
                        self._chop_cycles   = 0
                        self._action_target = tree
                        self._action_type   = 'chop'
                    elif not has_axe:
                        self._action_target = tree
                        self._execute_action('chop')
                    return
        for chunk in world.active_chunks.values():
            for stone in chunk.small_stones:
                if self.is_near(stone):
                    self._action_target = stone
                    self._execute_action('mine')
                    return

    def drink_water(self, world):
        """Tecla E: beber agua o regar farmland cercano."""
        return self.water_farmland(world)

    def _execute_action(self, action_kind: str):
        target = self._action_target
        if target is None:
            return
        world = self._world
        if world is None:
            return

        if action_kind == 'chop' and hasattr(target, 'chop'):
            result = target.chop(with_axe=self.inventory.has_axe_equipped())
            if result in ("chopped", "destroyed"):
                self.inventory.add_item("wood", 1)
                print(f"[chop] +1 madera (total {self.inventory.get_quantity('wood')})")
            if result == "destroyed":
                for chunk in world.active_chunks.values():
                    if target in chunk.trees:
                        chunk.trees.remove(target)
                        break
                self._action_target = None

        elif action_kind == 'mine' and hasattr(target, 'mine'):
            if target.mine():
                self.inventory.add_item("stone", 1)
                print(f"[mine] +1 piedra (total {self.inventory.get_quantity('stone')})")
            if getattr(target, 'stone', 0) == 0:
                for chunk in world.active_chunks.values():
                    if target in chunk.small_stones:
                        chunk.small_stones.remove(target)
                        break
                self._action_target = None

        elif action_kind == 'hoe' and isinstance(target, tuple):
            world.add_farmland(target[0], target[1])
            print(f"[hoe] farmland en {target}")
            self._action_target = None

    # ── HUD ───────────────────────────────────────────────────────────────────
    def draw_inventory(self, screen, show_inventory=False):
        self.inventory.draw(screen, show_inventory)
        if show_inventory:
            font = pygame.font.Font(None, 22)
            txt = font.render("I: cerrar inventario", True, constants.WHITE)
            screen.blit(txt, (constants.WIDTH//2 - txt.get_width()//2, constants.HEIGHT - 30))

    def update_energy(self, a):  self.energy  = max(0, min(MAX_ENERGY,  self.energy  + a))
    def update_food(self, a):    self.food    = max(0, min(MAX_FOOD,    self.food    + a))
    def update_thirst(self, a):  self.thirst  = max(0, min(MAX_THIRST,  self.thirst  + a))
    def update_stamina(self, a): self.stamina = max(0, min(MAX_STAMINA, self.stamina + a))

    def draw_status_bars(self, screen, world=None):
        bw, bh, sp, x, y = 100, 10, 10, 10, 10
        font = pygame.font.SysFont(None, 19)
        for label, val, maxv, color in [
            ("Energía", self.energy,  MAX_ENERGY,  constants.ENERGY_COLOR),
            ("Comida",  self.food,    MAX_FOOD,    constants.FOOD_COLOR),
            ("Sed",     self.thirst,  MAX_THIRST,  constants.THIRST_COLOR),
            ("Stamina", self.stamina, MAX_STAMINA, constants.STAMINA_COLOR),
        ]:
            pygame.draw.rect(screen, constants.BAR_BACKGROUND_COLOR, (x, y, bw, bh))
            pygame.draw.rect(screen, color, (x, y, int(bw * val / maxv), bh))
            screen.blit(font.render(f"{label}: {int(val)}", True, constants.WHITE),
                        (x + bw + 5, y))
            y += bh + sp

        if world is not None:
            tod = (world.current_time / constants.DAY_LENGTH) * 24
            screen.blit(font.render(f"Hora: {int(tod):02d}:00", True, constants.WHITE), (x, y))
            y += bh + sp
            if self.is_in_water(world):
                screen.blit(
                    font.render("~ En agua ~ (E: beber)", True, (100, 180, 255)),
                    (x, y))

    def update_status(self, world=None, dt_seconds: float = 1.0):
        fr = constants.FOOD_DECREASE_RATE   * (RUN_FOOD_DECREASE_MULTIPLIER   if self.is_running else 1)
        tr = constants.THIRST_DECREASE_RATE * (RUN_THIRST_DECREASE_MULTIPLIER if self.is_running else 1)
        self.update_food(-fr * dt_seconds)
        self.update_thirst(-tr * dt_seconds)
        if self.food < MAX_FOOD * 0.2 or self.thirst < MAX_THIRST * 0.2:
            self.update_energy(-constants.ENERGY_DECREASE_RATE * dt_seconds)
        else:
            self.update_energy(constants.ENERGY_INCREASE_RATE * dt_seconds)
        if self.is_running and self.stamina > 0:
            self.update_stamina(-constants.STAMINA_DECREASE_RATE * dt_seconds)
        else:
            self.update_stamina(constants.STAMINA_INCREASE_RATE * dt_seconds)