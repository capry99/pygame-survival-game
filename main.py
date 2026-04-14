import pygame
import sys
import constants
from character import Character
from world import World

pygame.init()
screen = pygame.display.set_mode((constants.WIDTH, constants.HEIGHT))
pygame.display.set_caption("Survival Game")


def main():
    clock = pygame.time.Clock()
    font  = pygame.font.SysFont(None, 19)

    world     = World(constants.WIDTH, constants.HEIGHT)
    character = Character(constants.WIDTH // 2, constants.HEIGHT // 2)
    character._world = world

    # Debug: dar semillas al inicio para probar
    character.inventory.add_item(constants.ITEM_CARROT_SEED, 24)

    show_inventory   = False
    show_coordinates = False
    status_update_time = 0

    camera_x = character.x - constants.WIDTH  // 2
    camera_y = character.y - constants.HEIGHT // 2

    while True:
        dt = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    character.interact(world)

                if event.key == pygame.K_e:
                    character.drink_water(world)

                if event.key == pygame.K_r:
                    world     = World(constants.WIDTH, constants.HEIGHT)
                    character = Character(constants.WIDTH // 2, constants.HEIGHT // 2)
                    character._world = world
                    character.inventory.add_item(constants.ITEM_CARROT_SEED, 24)

                if event.key == pygame.K_i:
                    if show_inventory:
                        character.inventory.close_inventory()
                    show_inventory = not show_inventory

                if event.key == pygame.K_f:
                    character.update_food(20)
                if event.key == pygame.K_t:
                    character.update_thirst(20)
                if event.key == pygame.K_c:
                    show_coordinates = not show_coordinates

                if event.key == pygame.K_z and show_inventory:
                    result = character.inventory.attempt_craft()
                    print(f"[craft] {result}" if result else "[craft] sin receta")

                if event.key == pygame.K_h:
                    if character.inventory.has_axe_equipped():
                        character.start_chop(world)
                    else:
                        print("No tenés hacha equipada.")

                if event.key == pygame.K_p:
                    if character.inventory.has_hoe_equipped():
                        character.start_hoe(world)
                    else:
                        print("No tenés pala equipada.")

            if event.type == pygame.MOUSEBUTTONDOWN:
                character.inventory.handle_click(event.pos, event.button, show_inventory)

        # ── Movimiento ────────────────────────────────────────────────────────
        dx = dy = 0
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  dx = -5
        if keys[pygame.K_RIGHT]: dx =  5
        if keys[pygame.K_UP]:    dy = -5
        if keys[pygame.K_DOWN]:  dy =  5

        character.is_running = keys[pygame.K_LSHIFT] and character.stamina > 0
        character.move(dx, dy, world)
        character.update_animation(dt)
        character._world = world

        # Preview del farmland: actualizar cada frame según si P está apretada
        character.update_hoe_preview(keys[pygame.K_p])

        # ── Auto siembra/cosecha al pararse encima del farmland ───────────────
        character.auto_farm_interact(world)

        camera_x = character.x - constants.WIDTH  // 2
        camera_y = character.y - constants.HEIGHT // 2

        world.update_chunks(character.x, character.y)
        world.update_time(dt)
        world.update_water(dt)
        world.update_farms(dt)   # riego automático + crecimiento

        # ── Estado del personaje ──────────────────────────────────────────────
        status_update_time += dt
        if status_update_time >= constants.STATUS_UPDATE_INTERVAL:
            character.update_status(world)
            status_update_time = 0
            if character.energy <= 0 or character.food <= 0 or character.thirst <= 0:
                df  = pygame.font.SysFont(None, 72)
                txt = df.render("¡Has muerto!", True, (255,0,0))
                screen.blit(txt, (constants.WIDTH//2 - txt.get_width()//2,
                                  constants.HEIGHT//2 - txt.get_height()//2))
                pygame.display.flip()
                pygame.time.delay(3000)
                pygame.quit(); sys.exit()

        # ── Render ────────────────────────────────────────────────────────────
        screen.fill((0,0,0))
        world.draw(screen, camera_x, camera_y)

        # Dibujar preview del farmland (tile fantasma semitransparente)
        if character.hoe_preview_tile:
            px, py = character.hoe_preview_tile
            sx = px - camera_x
            sy = py - camera_y
            ts = constants.GRASS_SIZE
            # Fondo marrón semitransparente
            preview_surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
            preview_surf.fill((120, 80, 40, 140))
            screen.blit(preview_surf, (sx, sy))
            # Borde punteado blanco
            pygame.draw.rect(screen, (255, 255, 200), (sx, sy, ts, ts), 2)
            # Texto "P: confirmar"
            ptxt = font.render("P", True, (255, 255, 180))
            screen.blit(ptxt, (sx + ts//2 - ptxt.get_width()//2,
                               sy + ts//2 - ptxt.get_height()//2))

        character.draw(screen, camera_x, camera_y, world)
        character.draw_inventory(screen, show_inventory)

        if show_coordinates:
            ct = font.render(f"X:{int(character.x)}  Y:{int(character.y)}", True, constants.WHITE)
            screen.blit(ct, (10, constants.HEIGHT - 60))

        # ── HUD contextual ────────────────────────────────────────────────────
        if show_inventory:
            hint = font.render(
                "Crafteo: arrastrá → clic Result  |  Z: craftear directo  |  I: cerrar",
                True, (220,220,100))
            screen.blit(hint, (constants.WIDTH//2 - hint.get_width()//2,
                               constants.HEIGHT - 50))
        else:
            # Mostrar semillas disponibles
            seeds = character.inventory.get_quantity(constants.ITEM_CARROT_SEED)
            carrots = character.inventory.get_quantity(constants.ITEM_CARROT)
            info = font.render(
                f"🌱 Semillas: {seeds}   🥕 Zanahorias: {carrots}",
                True, (180,230,120))
            screen.blit(info, (constants.WIDTH//2 - info.get_width()//2, 8))

            # Indicador de farmland bajo el jugador
            cx = character.x + character.width  // 2
            cy = character.y + character.height // 2
            farm = world.get_farmland_at(cx, cy)
            if farm:
                manual_t = getattr(farm, '_manual_water_timer', 0)
                adj_water = world.water_adjacent(farm.x, farm.y)
                water_src = "💧 agua adyacente" if adj_water else (f"🪣 regado ({manual_t//1000}s)" if manual_t>0 else "🏜 sin agua — E para regar")
                remaining = farm.seeds_count if farm.state == "ready" else ""
                state_msgs = {
                    "empty":     "Vacío — caminá encima para sembrar",
                    "planted":   f"Sembrado — {water_src}",
                    "growing":   f"Fase {farm.phase}/4 — {water_src}",
                    "ready":     f"¡Listo para cosechar! ({farm.seeds_count} restantes) — caminá encima",
                    "harvested": "Cosechado — regenerando...",
                }
                msg = state_msgs.get(farm.state, "")
                stxt = font.render(msg, True, (255,255,140))
                screen.blit(stxt, (constants.WIDTH//2 - stxt.get_width()//2,
                                   constants.HEIGHT - 55))

            controls = [
                "P:preparar tierra  ESPACIO:recolectar  H:hacha  E:beber/regar",
                "I:inventario  C:coords  F:+comida  T:+agua  R:reiniciar",
            ]
            for i, line in enumerate(controls):
                ct = font.render(line, True, (160,160,160))
                screen.blit(ct, (constants.WIDTH - ct.get_width() - 8,
                                 constants.HEIGHT - 36 + i*18))

        pygame.display.flip()


if __name__ == "__main__":
    main()