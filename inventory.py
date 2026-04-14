import os
import pygame
import constants

pygame.font.init()


class InventoryItems:
    def __init__(self, name, image_path, quantity=1):
        self.name = name
        self.quantity = quantity
        try:
            surf = pygame.image.load(image_path).convert_alpha()
            self.image = pygame.transform.scale(surf, (constants.SLOT_SIZE - 10, constants.SLOT_SIZE - 10))
        except Exception:
            self.image = pygame.Surface((constants.SLOT_SIZE - 10, constants.SLOT_SIZE - 10), pygame.SRCALPHA)
            self.image.fill((180, 180, 180))
            txt = pygame.font.SysFont(None, 14).render(name[:3].upper(), True, (0, 0, 0))
            self.image.blit(txt, (4, 4))
        self.dragging = False
        self.drag_offset = (0, 0)


class Inventory:
    def __init__(self):
        self.left_hand = None
        self.right_hand = None
        self.hotbar = [None] * constants.HOTBAR_SLOTS
        self.inventory = [[None for _ in range(constants.INVENTORY_COLS)]
                          for _ in range(constants.INVENTORY_ROWS)]
        self.crafting_grid = [[None for _ in range(constants.CRAFTING_GRID_SIZE)]
                              for _ in range(constants.CRAFTING_GRID_SIZE)]
        self.crafting_result = None
        self._last_recipe = None
        self.dragged_item = None

        self.title_font = pygame.font.SysFont(None, 18)
        self.qty_font = pygame.font.SysFont(None, 16)

        self.item_images = {
            "wood":        os.path.join("assets", "images", "objects", "wood.png"),
            "stone":       os.path.join("assets", "images", "objects", "small_stone.png"),
            "axe":         os.path.join("assets", "images", "objects", "axe.png"),
            "hoe":         os.path.join("assets", "images", "objects", "hoe.png"),
            "carrot_seed": constants.IMG_CARROT_SEED,
            "carrot":      constants.IMG_CARROT_HARVESTED,
        }

        # -------------------------------------------------------
        # Recetas — grilla 2×2:
        #   [fila0_col0, fila0_col1]
        #   [fila1_col0, fila1_col1]
        #
        # FIX: patrones simples con 1 ítem por celda.
        # hacha  → wood en [0,0]  y  stone en [0,1]
        # pala   → stone en [0,0] y  wood  en [0,1]
        # nueva  → wood + carrot -> 4 carrot_seed
        # -------------------------------------------------------
        self.recipes = {
            'axe': {
                'pattern': [['wood', 'stone'],
                            [None,  None   ]],
                'result': 'axe',
                'result_qty': 1
            },
            'hoe': {
                'pattern': [['stone', 'wood'],
                            [None,   None  ]],
                'result': 'hoe',
                'result_qty': 1
            },
            'carrot_to_seeds': {
                'pattern': [['wood', 'carrot'],
                            [None,   None  ]],
                'result': 'carrot_seed',
                'result_qty': 4
            },
        }
        print("[Inventory] initialized")

    # -----------------------
    # Item management
    # -----------------------
    def add_item(self, item_name, quantity=1):
        print(f"[add_item] {item_name} x{quantity}")
        for r in range(constants.INVENTORY_ROWS):
            for c in range(constants.INVENTORY_COLS):
                slot = self.inventory[r][c]
                if slot and slot.name == item_name:
                    slot.quantity += quantity
                    return True
        for i, slot in enumerate(self.hotbar):
            if slot and slot.name == item_name:
                slot.quantity += quantity
                return True
        for r in range(constants.INVENTORY_ROWS):
            for c in range(constants.INVENTORY_COLS):
                if self.inventory[r][c] is None:
                    self.inventory[r][c] = InventoryItems(item_name, self.item_images.get(item_name, ""), quantity)
                    return True
        for i in range(constants.HOTBAR_SLOTS):
            if self.hotbar[i] is None:
                self.hotbar[i] = InventoryItems(item_name, self.item_images.get(item_name, ""), quantity)
                return True
        print(f"[add_item] No space for {item_name}")
        return False

    def get_quantity(self, item_name):
        total = 0
        for slot in self.hotbar:
            if slot and slot.name == item_name:
                total += slot.quantity
        for r in range(constants.INVENTORY_ROWS):
            for c in range(constants.INVENTORY_COLS):
                slot = self.inventory[r][c]
                if slot and slot.name == item_name:
                    total += slot.quantity
        return total

    # -----------------------
    # Drawing
    # -----------------------
    def draw(self, screen, show_inventory=False):
        # Hotbar
        for i in range(constants.HOTBAR_SLOTS):
            x = constants.HOTBAR_X + i * constants.SLOT_SIZE
            y = constants.HOTBAR_Y
            pygame.draw.rect(screen, constants.SLOT_BORDER, (x, y, constants.SLOT_SIZE, constants.SLOT_SIZE))
            pygame.draw.rect(screen, constants.SLOT_COLOR,  (x+2, y+2, constants.SLOT_SIZE-4, constants.SLOT_SIZE-4))
            if self.hotbar[i]:
                self._draw_item(screen, self.hotbar[i], x, y)

        # Manos
        for slot_x, slot_y, item, label in [
            (constants.LEFT_HAND_SLOT_X,  constants.LEFT_HAND_SLOT_Y,  self.left_hand,  "L.Hand"),
            (constants.RIGHT_HAND_SLOT_X, constants.RIGHT_HAND_SLOT_Y, self.right_hand, "R.Hand"),
        ]:
            pygame.draw.rect(screen, constants.SLOT_BORDER, (slot_x, slot_y, constants.SLOT_SIZE, constants.SLOT_SIZE))
            pygame.draw.rect(screen, constants.SLOT_COLOR,  (slot_x+2, slot_y+2, constants.SLOT_SIZE-4, constants.SLOT_SIZE-4))
            lbl = self.title_font.render(label, True, constants.WHITE)
            screen.blit(lbl, (slot_x, slot_y - lbl.get_height() - 2))
            if item:
                self._draw_item(screen, item, slot_x, slot_y)

        if show_inventory:
            # Panel de fondo
            panel_w = constants.SLOT_SIZE * constants.INVENTORY_COLS + 20
            panel_h = constants.SLOT_SIZE * constants.INVENTORY_ROWS + 50
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 200))
            screen.blit(panel, (constants.INVENTORY_X, constants.INVENTORY_Y))

            lbl = self.title_font.render("Inventory", True, constants.WHITE)
            screen.blit(lbl, (constants.INVENTORY_X + 8, constants.INVENTORY_Y + 6))

            # FIX: calcular start_y del grid del inventario igual que en handle_click
            inv_grid_start_y = constants.INVENTORY_Y + 6 + lbl.get_height() + 6
            for row in range(constants.INVENTORY_ROWS):
                for col in range(constants.INVENTORY_COLS):
                    sx = constants.INVENTORY_X + 10 + col * constants.SLOT_SIZE
                    sy = inv_grid_start_y + row * constants.SLOT_SIZE
                    pygame.draw.rect(screen, constants.SLOT_BORDER, (sx, sy, constants.SLOT_SIZE, constants.SLOT_SIZE))
                    pygame.draw.rect(screen, constants.SLOT_COLOR,  (sx+2, sy+2, constants.SLOT_SIZE-4, constants.SLOT_SIZE-4))
                    if self.inventory[row][col]:
                        self._draw_item(screen, self.inventory[row][col], sx, sy)

            # Grilla de crafteo
            craft_title = self.title_font.render("Crafting  (wood+stone → axe  |  stone+wood → hoe)", True, constants.WHITE)
            screen.blit(craft_title, (constants.CRAFTING_GRID_X, constants.CRAFTING_GRID_Y - craft_title.get_height() - 6))
            for r in range(constants.CRAFTING_GRID_SIZE):
                for c in range(constants.CRAFTING_GRID_SIZE):
                    sx = constants.CRAFTING_GRID_X + c * constants.SLOT_SIZE
                    sy = constants.CRAFTING_GRID_Y + r * constants.SLOT_SIZE
                    pygame.draw.rect(screen, constants.SLOT_BORDER, (sx, sy, constants.SLOT_SIZE, constants.SLOT_SIZE))
                    pygame.draw.rect(screen, constants.SLOT_COLOR,  (sx+2, sy+2, constants.SLOT_SIZE-4, constants.SLOT_SIZE-4))
                    if self.crafting_grid[r][c]:
                        self._draw_item(screen, self.crafting_grid[r][c], sx, sy)

            # Slot resultado
            res_title = self.title_font.render("Result", True, constants.WHITE)
            screen.blit(res_title, (constants.CRAFTING_RESULT_SLOT_X, constants.CRAFTING_RESULT_SLOT_Y - res_title.get_height() - 6))
            pygame.draw.rect(screen, constants.SLOT_BORDER,
                             (constants.CRAFTING_RESULT_SLOT_X, constants.CRAFTING_RESULT_SLOT_Y,
                              constants.SLOT_SIZE, constants.SLOT_SIZE))
            pygame.draw.rect(screen, constants.SLOT_COLOR,
                             (constants.CRAFTING_RESULT_SLOT_X+2, constants.CRAFTING_RESULT_SLOT_Y+2,
                              constants.SLOT_SIZE-4, constants.SLOT_SIZE-4))
            if self.crafting_result:
                self._draw_item(screen, self.crafting_result,
                                constants.CRAFTING_RESULT_SLOT_X, constants.CRAFTING_RESULT_SLOT_Y)

            help_txt = self.title_font.render("I: cerrar  •  Drag: mover items  •  Click Result: craftear", True, constants.WHITE)
            screen.blit(help_txt, (constants.INVENTORY_X + 8,
                                   constants.INVENTORY_Y + panel_h - help_txt.get_height() - 8))

        # Ítem arrastrado (siempre encima de todo)
        if self.dragged_item and self.dragged_item.image:
            mx, my = pygame.mouse.get_pos()
            img = self.dragged_item.image
            screen.blit(img, (mx - img.get_width() // 2, my - img.get_height() // 2))
            if self.dragged_item.quantity > 1:
                qty_text = self.qty_font.render(str(self.dragged_item.quantity), True, constants.WHITE)
                screen.blit(qty_text, (mx + img.get_width()//2 - qty_text.get_width(),
                                       my + img.get_height()//2 - qty_text.get_height()))

    def _draw_item(self, screen, item, x, y):
        ix = x + (constants.SLOT_SIZE - item.image.get_width()) // 2
        iy = y + (constants.SLOT_SIZE - item.image.get_height()) // 2
        screen.blit(item.image, (ix, iy))
        if item.quantity > 1:
            text = self.qty_font.render(str(item.quantity), True, constants.WHITE)
            screen.blit(text, (x + constants.SLOT_SIZE - text.get_width() - 5,
                               y + constants.SLOT_SIZE - text.get_height() - 5))

    # -----------------------
    # Clicks
    # -----------------------
    def handle_click(self, pos, button, show_inventory=False):
        mx, my = pos

        # Manos
        if (constants.LEFT_HAND_SLOT_X <= mx <= constants.LEFT_HAND_SLOT_X + constants.SLOT_SIZE and
                constants.LEFT_HAND_SLOT_Y <= my <= constants.LEFT_HAND_SLOT_Y + constants.SLOT_SIZE):
            self._handle_hand_slot_click(button, 'left')
            return True
        if (constants.RIGHT_HAND_SLOT_X <= mx <= constants.RIGHT_HAND_SLOT_X + constants.SLOT_SIZE and
                constants.RIGHT_HAND_SLOT_Y <= my <= constants.RIGHT_HAND_SLOT_Y + constants.SLOT_SIZE):
            self._handle_hand_slot_click(button, 'right')
            return True

        # Hotbar
        if constants.HOTBAR_Y <= my <= constants.HOTBAR_Y + constants.SLOT_SIZE:
            slot_index = (mx - constants.HOTBAR_X) // constants.SLOT_SIZE
            if 0 <= slot_index < constants.HOTBAR_SLOTS:
                self._handle_slot_click(button, self.hotbar, slot_index,
                                        constants.HOTBAR_X + slot_index * constants.SLOT_SIZE,
                                        constants.HOTBAR_Y)
                return True

        if show_inventory:
            # FIX: calcular inv_grid_start_y igual que en draw()
            lbl_h = self.title_font.size("Inventory")[1]
            inv_grid_start_y = constants.INVENTORY_Y + 6 + lbl_h + 6
            inv_grid_start_x = constants.INVENTORY_X + 10

            # Grid inventario
            inv_grid_end_x = inv_grid_start_x + constants.INVENTORY_COLS * constants.SLOT_SIZE
            inv_grid_end_y = inv_grid_start_y + constants.INVENTORY_ROWS * constants.SLOT_SIZE
            if inv_grid_start_x <= mx < inv_grid_end_x and inv_grid_start_y <= my < inv_grid_end_y:
                col = (mx - inv_grid_start_x) // constants.SLOT_SIZE
                row = (my - inv_grid_start_y) // constants.SLOT_SIZE
                if 0 <= row < constants.INVENTORY_ROWS and 0 <= col < constants.INVENTORY_COLS:
                    self._handle_grid_slot_click(button, row, col,
                                                 inv_grid_start_x + col * constants.SLOT_SIZE,
                                                 inv_grid_start_y + row * constants.SLOT_SIZE)
                    return True

            # Grid crafteo
            cg_x1 = constants.CRAFTING_GRID_X
            cg_y1 = constants.CRAFTING_GRID_Y
            cg_x2 = cg_x1 + constants.CRAFTING_GRID_SIZE * constants.SLOT_SIZE
            cg_y2 = cg_y1 + constants.CRAFTING_GRID_SIZE * constants.SLOT_SIZE
            if cg_x1 <= mx < cg_x2 and cg_y1 <= my < cg_y2:
                col = (mx - cg_x1) // constants.SLOT_SIZE
                row = (my - cg_y1) // constants.SLOT_SIZE
                if 0 <= row < constants.CRAFTING_GRID_SIZE and 0 <= col < constants.CRAFTING_GRID_SIZE:
                    self._handle_crafting_grid_click(button, row, col)
                    return True

            # Slot resultado
            rx1 = constants.CRAFTING_RESULT_SLOT_X
            ry1 = constants.CRAFTING_RESULT_SLOT_Y
            if rx1 <= mx <= rx1 + constants.SLOT_SIZE and ry1 <= my <= ry1 + constants.SLOT_SIZE:
                self._handle_crafting_result_click(button)
                return True

        # Soltar fuera: devolver al inventario
        if self.dragged_item and button == 1:
            self._return_dragged_item()
            return False

    def _handle_slot_click(self, button, slot_list, index, slot_x, slot_y):
        if button != 1:
            return
        mx, my = pygame.mouse.get_pos()
        if self.dragged_item:
            if slot_list[index] is None:
                slot_list[index] = self.dragged_item
                self.dragged_item = None
            elif slot_list[index].name == self.dragged_item.name:
                slot_list[index].quantity += self.dragged_item.quantity
                self.dragged_item = None
            else:
                slot_list[index], self.dragged_item = self.dragged_item, slot_list[index]
        elif slot_list[index]:
            self.dragged_item = slot_list[index]
            slot_list[index] = None
            r = self.dragged_item.image.get_rect()
            self.dragged_item.drag_offset = (mx - r.centerx, my - r.centery)

    def _handle_grid_slot_click(self, button, row, col, slot_x, slot_y):
        if button != 1:
            return
        mx, my = pygame.mouse.get_pos()
        if self.dragged_item:
            if self.inventory[row][col] is None:
                self.inventory[row][col] = self.dragged_item
                self.dragged_item = None
            elif self.inventory[row][col].name == self.dragged_item.name:
                self.inventory[row][col].quantity += self.dragged_item.quantity
                self.dragged_item = None
            else:
                self.inventory[row][col], self.dragged_item = self.dragged_item, self.inventory[row][col]
        elif self.inventory[row][col]:
            self.dragged_item = self.inventory[row][col]
            self.inventory[row][col] = None
            r = self.dragged_item.image.get_rect()
            self.dragged_item.drag_offset = (mx - r.centerx, my - r.centery)

    def _handle_hand_slot_click(self, button, hand):
        if button != 1:
            return
        if hand == 'left':
            if self.dragged_item:
                if self.dragged_item.name in ['axe', 'hoe']:
                    self.left_hand, self.dragged_item = self.dragged_item, self.left_hand
            elif self.left_hand:
                self.dragged_item = self.left_hand
                self.left_hand = None
        else:
            if self.dragged_item:
                if self.dragged_item.name in ['axe', 'hoe']:
                    self.right_hand, self.dragged_item = self.dragged_item, self.right_hand
            elif self.right_hand:
                self.dragged_item = self.right_hand
                self.right_hand = None

    def _return_dragged_item(self):
        if not self.dragged_item:
            return
        name, qty = self.dragged_item.name, self.dragged_item.quantity
        for r in range(constants.INVENTORY_ROWS):
            for c in range(constants.INVENTORY_COLS):
                if self.inventory[r][c] and self.inventory[r][c].name == name:
                    self.inventory[r][c].quantity += qty
                    self.dragged_item = None
                    return
        for i in range(constants.HOTBAR_SLOTS):
            if self.hotbar[i] and self.hotbar[i].name == name:
                self.hotbar[i].quantity += qty
                self.dragged_item = None
                return
        for r in range(constants.INVENTORY_ROWS):
            for c in range(constants.INVENTORY_COLS):
                if self.inventory[r][c] is None:
                    self.inventory[r][c] = self.dragged_item
                    self.dragged_item = None
                    return
        for i in range(constants.HOTBAR_SLOTS):
            if self.hotbar[i] is None:
                self.hotbar[i] = self.dragged_item
                self.dragged_item = None
                return
        print("[RETURN_DRAGGED] No space, discarding")
        self.dragged_item = None

    # -----------------------
    # Crafteo
    # -----------------------
    def _handle_crafting_grid_click(self, button, row, col):
        if button != 1:
            return
        if self.dragged_item:
            if self.crafting_grid[row][col] is None:
                self.crafting_grid[row][col] = self.dragged_item
                self.dragged_item = None
            elif self.crafting_grid[row][col].name == self.dragged_item.name:
                self.crafting_grid[row][col].quantity += self.dragged_item.quantity
                self.dragged_item = None
            else:
                self.crafting_grid[row][col], self.dragged_item = self.dragged_item, self.crafting_grid[row][col]
            self._check_recipe()
            return
        if self.crafting_grid[row][col]:
            self.dragged_item = self.crafting_grid[row][col]
            self.crafting_grid[row][col] = None
            self._check_recipe()

    def _check_recipe(self):
        """Comparación exacta posición a posición en la grilla 2×2."""
        size = constants.CRAFTING_GRID_SIZE
        current = [
            [self.crafting_grid[r][c].name if self.crafting_grid[r][c] else None
             for c in range(size)]
            for r in range(size)
        ]
        self.crafting_result = None
        self._last_recipe = None

        print("[_check_recipe] grilla actual:", current)

        for recipe_name, recipe in self.recipes.items():
            pattern = recipe['pattern']
            # La grilla es 2×2 y el patrón también, comparación directa celda a celda
            match = all(
                pattern[r][c] == current[r][c]
                for r in range(size)
                for c in range(size)
            )
            print(f"  receta '{recipe_name}' -> {'✓ MATCH' if match else 'no match'}")
            if match:
                # crear resultado con la cantidad definida en la receta (por defecto 1)
                result_name = recipe['result']
                result_qty = recipe.get('result_qty', 1)
                self.crafting_result = InventoryItems(
                    result_name,
                    self.item_images.get(result_name, ""),
                    result_qty
                )
                self._last_recipe = {'name': recipe_name, 'pattern': pattern}
                print(f"[RECIPE] ¡Encontrada! {recipe_name} -> {result_name} x{result_qty}")
                return

    def _handle_crafting_result_click(self, button):
        if button != 1 or not self.crafting_result or not self._last_recipe:
            return
        pattern = self._last_recipe['pattern']
        size = constants.CRAFTING_GRID_SIZE
        # Consumir 1 unidad de cada celda que el patrón requiere
        for r in range(size):
            for c in range(size):
                if pattern[r][c] is not None:
                    cell = self.crafting_grid[r][c]
                    if cell:
                        cell.quantity -= 1
                        if cell.quantity <= 0:
                            self.crafting_grid[r][c] = None
        # Entregar el resultado (puede ser >1)
        self.dragged_item = self.crafting_result
        print(f"[CRAFT RESULT] crafteo exitoso: {self.dragged_item.name} x{self.dragged_item.quantity}")
        self.crafting_result = None
        self._last_recipe = None
        self._check_recipe()

    def attempt_craft(self):
        """Llamado desde main.py con tecla C."""
        self._check_recipe()
        if not self._last_recipe:
            print("[MAIN] No hay receta válida en la grilla")
            return None
        recipe_name = self._last_recipe['name']
        pattern = self._last_recipe['pattern']
        size = constants.CRAFTING_GRID_SIZE
        # Consumir ingredientes
        for r in range(size):
            for c in range(size):
                if pattern[r][c] is not None:
                    cell = self.crafting_grid[r][c]
                    if cell:
                        cell.quantity -= 1
                        if cell.quantity <= 0:
                            self.crafting_grid[r][c] = None
        # Resultado y cantidad
        recipe = self.recipes[recipe_name]
        result_name = recipe['result']
        result_qty = recipe.get('result_qty', 1)
        # Intentar añadir al inventario la cantidad completa
        if not self.add_item(result_name, result_qty):
            # si no hay espacio, dejar como dragged_item con la cantidad
            self.dragged_item = InventoryItems(result_name, self.item_images.get(result_name, ""), result_qty)
            print(f"[attempt_craft] crafted {result_name} x{result_qty} (as dragged_item)")
        else:
            print(f"[attempt_craft] crafted {result_name} x{result_qty} and added to inventory")
        self._check_recipe()
        return result_name

    def close_inventory(self):
        if self.dragged_item:
            self._return_dragged_item()
        # Devolver items de la grilla al inventario
        for r in range(constants.CRAFTING_GRID_SIZE):
            for c in range(constants.CRAFTING_GRID_SIZE):
                cell = self.crafting_grid[r][c]
                if cell:
                    self.add_item(cell.name, cell.quantity)
                    self.crafting_grid[r][c] = None
        self._check_recipe()

    # -----------------------
    # Utilidades
    # -----------------------
    def has_axe_equipped(self):
        return ((self.left_hand  and self.left_hand.name  == 'axe') or
                (self.right_hand and self.right_hand.name == 'axe'))

    def has_hoe_equipped(self):
        return ((self.left_hand  and self.left_hand.name  == 'hoe') or
                (self.right_hand and self.right_hand.name == 'hoe'))