# ============================================================
# constants.py
# ============================================================
import os

CHUNK_SIZE = 512
WIDTH, HEIGHT = 1128, 634
PLAYER = 100
GRASS_SIZE = 50
TREE_SIZE = 70
SMALL_STONE_SIZE = 32
INVENTORY_WIDTH = 300
INVENTORY_HEIGHT = 150

TREE_IMAGE_SIZE = 100
STONE_IMAGE_SIZE = 40

# Animaciones personaje
CUADROS_BASICOS = 6
IDLE_DOWN = 0
IDLE_RIGHT = 1
IDLE_UP = 2
WALK_DOWN = 3
WALK_RIGHT = 4
WALK_UP = 5
FRAME_SIZE = 32
ANIMATION_DELAY = 100
RUNNING_ANIMATION_DELAY = 50

# Colores
WHITE = (255, 255, 255)
BLUE  = (0, 0, 255)
BLACK = (0, 0, 0)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
BROWN = (165, 42, 42)
INVENTORY_COLOR = (0, 0, 0, 128)

# Barras de estado
MAX_ENERGY  = 100
MAX_FOOD    = 100
MAX_THIRST  = 100
MAX_STAMINA = 100

ENERGY_COLOR  = (255, 255, 0)
FOOD_COLOR    = (255, 165, 0)
THIRST_COLOR  = (0, 191, 255)
STAMINA_COLOR = (124, 252, 0)
BAR_BACKGROUND_COLOR = (50, 50, 50)

STATUS_UPDATE_INTERVAL = 1000  # ms

# Día/noche
DAY_LENGTH      = 240000
DAWN_TIME       = 60000
MORNING_TIME    = 80000
DUSK_TIME       = 180000
MIDNIGHT_TIME   = 240000
MAX_DARKNESS    = 180
DAY_COLOR       = (255, 255, 255)
DAWN_DUSK_COLOR = (255, 180, 100)
NIGHT_COLOR     = (20, 20, 50)

# Tasas de estado
FOOD_DECREASE_RATE    = 0.01
THIRST_DECREASE_RATE  = 0.02
ENERGY_DECREASE_RATE  = 0.005
ENERGY_INCREASE_RATE  = 0.01
MOVEMENT_ENERGY_COST  = 0.1

# Velocidad
WALK_SPEED = 5
RUN_SPEED  = 8
STAMINA_DECREASE_RATE = 0.05
STAMINA_INCREASE_RATE = 0.02
RUN_FOOD_DECREASE_MULTIPLIER   = 2.0
RUN_THIRST_DECREASE_MULTIPLIER = 2.0

# Inventario
SLOT_SIZE       = 64
HOTBAR_SLOTS    = 8
INVENTORY_COLS  = 5
INVENTORY_ROWS  = 4
MARGIN          = 10

HOTBAR_X = (WIDTH - (SLOT_SIZE * HOTBAR_SLOTS)) // 2
HOTBAR_Y = HEIGHT - SLOT_SIZE - MARGIN

INVENTORY_X = (WIDTH  - (SLOT_SIZE * INVENTORY_COLS)) // 2
INVENTORY_Y = (HEIGHT - (SLOT_SIZE * INVENTORY_ROWS)) // 2

CRAFTING_GRID_SIZE     = 2
CRAFTING_RESULT_SLOT_X = INVENTORY_X + (SLOT_SIZE * (INVENTORY_COLS + 1))
CRAFTING_RESULT_SLOT_Y = INVENTORY_Y
CRAFTING_GRID_X        = INVENTORY_X + (SLOT_SIZE * (INVENTORY_COLS + 1))
CRAFTING_GRID_Y        = INVENTORY_Y + SLOT_SIZE * 2

LEFT_HAND_SLOT_X  = HOTBAR_X - SLOT_SIZE - MARGIN
LEFT_HAND_SLOT_Y  = HOTBAR_Y
RIGHT_HAND_SLOT_X = HOTBAR_X + (SLOT_SIZE * HOTBAR_SLOTS) + MARGIN
RIGHT_HAND_SLOT_Y = HOTBAR_Y

# Herramientas
AXE_COLS            = 2
AXE_FRAMES          = 2
AXE_ANIMATION_DELAY = 180

HOE_COLS            = 2
HOE_FRAMES          = 2
HOE_ANIMATION_DELAY = 200

# Colores inventario
SLOT_COLOR  = (139, 139, 139)
SLOT_BORDER = (100, 100, 100)
SLOT_HOVER  = (160, 160, 160)

# ── AGUA ──────────────────────────────────────────────────────────────────────
WATER_COLOR                  = (30, 100, 200, 180)
WATER_SIZE                   = 50
WATER_GENERATION_PROBABILITY = 0.25
WATER_MOVEMENT_MULTIPLIER    = 0.5
WATER_THIRST_RECOVERY        = 20
# Radio en px para considerar "cerca del agua" (riego automático)
WATER_AUTO_IRRIGATE_RADIUS   = 200

# ── AGRICULTURA ───────────────────────────────────────────────────────────────
# Semillas por tile de farmland (grilla 4×2)
FARM_SEEDS_PER_TILE   = 8
FARM_GRID_COLS        = 4
FARM_GRID_ROWS        = 2

# Fases de crecimiento: 0=sembrado, 1-4=creciendo, 5=listo
FARM_PHASE_PLANTED    = 0
FARM_PHASE_READY      = 5
FARM_TOTAL_PHASES     = 6   # 0..5

# Tiempo (ms) que tarda en avanzar una fase CUANDO está regado
FARM_GROWTH_TIME_MS   = 30_000   # 30 segundos por fase

# El tile se pausa si no hay agua cerca (no muere, no crece)
# Duración del riego manual (ms) — cuánto tiempo dura cada regado con E
FARM_MANUAL_WATER_DURATION = 60_000   # 60 segundos por regada manual
# Zanahorias cosechadas que da un tile completo al cosechar
FARM_YIELD_PER_TILE   = 8

# ── RUTAS DE IMÁGENES DE AGRICULTURA (definidas aquí para centralizar) ────────
_IMG = os.path.join("assets", "images")

# Fondo farmland
IMG_FARMLAND          = os.path.join(_IMG, "objects", "FarmLand.png")

# Cartel que aparece encima del farmland cuando hay plantas
IMG_CROP_SIGN_CARROT  = os.path.join(_IMG, "zanahoria","zanahoria_cartel_2.png")

# Fases visuales del cultivo (índices 0-3 → fases 1-4 de crecimiento)
IMG_CARROT_PHASES = [
    os.path.join(_IMG,"zanahoria", "zanahoria_fase_3.png"),   # fase 1 (recién brotó)
    os.path.join(_IMG, "zanahoria","zanahoria_fase_4.png"),   # fase 2
    os.path.join(_IMG, "zanahoria","zanahoria_fase_5.png"),   # fase 3
    os.path.join(_IMG,"zanahoria", "zanahoria_fase_6.png"),   # fase 4 (lista)
]

# Ícono de semilla de zanahoria (para inventario)
IMG_CARROT_SEED       = os.path.join(_IMG, "zanahoria","zanahoria_icono_0.png")
# Ícono de zanahoria cosechada (para inventario)
IMG_CARROT_HARVESTED  = os.path.join(_IMG, "zanahoria","zanahoria_icono_1.png")

# ── INDICADORES VISUALES DE RIEGO ─────────────────────────────────────────────
FARM_WET_COLOR   = (60, 130, 220, 120)   # overlay azulado cuando está regado
FARM_DRY_COLOR   = (180, 140, 80,  80)   # overlay marrón cuando está seco

# Nombre de ítems (para inventario)
ITEM_CARROT_SEED      = "carrot_seed"
ITEM_CARROT           = "carrot"