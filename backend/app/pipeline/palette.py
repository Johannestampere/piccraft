import numpy as np


# Convert (N, 3) float32 RBG to (N, 3) LAB.
def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    c = np.clip(rgb, 0, 255) / 255.0       # normalize

    # sRGB gamma -> linear light
    linear = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)

    # Linear RGB -> XYZ
    M = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ], dtype=np.float32)
    xyz = linear @ M.T      # matrix multiply

    # Normalize by D65 white point
    xyz /= np.array([0.95047, 1.00000, 1.08883], dtype=np.float32)

    # XYZ -> LAB
    f = np.where(xyz > 0.008856, xyz ** (1.0 / 3.0), (903.3 * xyz + 16.0) / 116.0)
    L = 116.0 * f[:, 1] - 16.0
    a = 500.0 * (f[:, 0] - f[:, 1])
    b = 200.0 * (f[:, 1] - f[:, 2])
    return np.stack([L, a, b], axis=1)

# (R, G, B, block_id)
BLOCK_PALETTE: list[tuple[int, int, int, str]] = [
    # --- Concrete (vivid, saturated) ---
    (207, 213, 214, "minecraft:white_concrete"),
    (224, 97, 1, "minecraft:orange_concrete"),
    (169, 48, 159, "minecraft:magenta_concrete"),
    (36, 137, 199, "minecraft:light_blue_concrete"),
    (241, 175, 21, "minecraft:yellow_concrete"),
    (94, 169, 25, "minecraft:lime_concrete"),
    (214, 101, 143, "minecraft:pink_concrete"),
    (55, 58, 62, "minecraft:gray_concrete"),
    (125, 125, 115, "minecraft:light_gray_concrete"),
    (21, 119, 136, "minecraft:cyan_concrete"),
    (100, 32, 156, "minecraft:purple_concrete"),
    (45, 47, 143, "minecraft:blue_concrete"),
    (96, 60, 32, "minecraft:brown_concrete"),
    (73, 91, 36, "minecraft:green_concrete"),
    (142, 33, 33, "minecraft:red_concrete"),
    (8, 10, 15, "minecraft:black_concrete"),

    # --- Wool (softer, lighter) ---
    (234, 236, 236, "minecraft:white_wool"),
    (241, 118, 20, "minecraft:orange_wool"),
    (189, 68, 179, "minecraft:magenta_wool"),
    (58, 175, 217, "minecraft:light_blue_wool"),
    (249, 198, 40, "minecraft:yellow_wool"),
    (112, 185, 26, "minecraft:lime_wool"),
    (238, 141, 172, "minecraft:pink_wool"),
    (63, 68, 72, "minecraft:gray_wool"),
    (142, 142, 135, "minecraft:light_gray_wool"),
    (21, 138, 145, "minecraft:cyan_wool"),
    (122, 42, 173, "minecraft:purple_wool"),
    (53, 57, 157, "minecraft:blue_wool"),
    (114, 72, 41, "minecraft:brown_wool"),
    (85, 110, 28, "minecraft:green_wool"),
    (161, 39, 35, "minecraft:red_wool"),
    (20, 21, 26, "minecraft:black_wool"),

    # --- Terracotta (muted, earthy — great for skin/natural tones) ---
    (210, 178, 161, "minecraft:white_terracotta"),
    (162, 84, 38, "minecraft:orange_terracotta"),
    (150, 88, 109, "minecraft:magenta_terracotta"),
    (113, 109, 138, "minecraft:light_blue_terracotta"),
    (186, 133, 35, "minecraft:yellow_terracotta"),
    (103, 118, 53, "minecraft:lime_terracotta"),
    (162, 78, 79, "minecraft:pink_terracotta"),
    (58, 42, 36, "minecraft:gray_terracotta"),
    (135, 107, 98, "minecraft:light_gray_terracotta"),
    (87, 91, 91, "minecraft:cyan_terracotta"),
    (118, 70, 86, "minecraft:purple_terracotta"),
    (74, 60, 91, "minecraft:blue_terracotta"),
    (77, 51, 36, "minecraft:brown_terracotta"),
    (76, 83, 42, "minecraft:green_terracotta"),
    (143, 61, 47, "minecraft:red_terracotta"),
    (37, 23, 16, "minecraft:black_terracotta"),

    # --- Glazed Terracotta (vivid, patterned — unique saturated hues) ---
    (237, 237, 237, "minecraft:white_glazed_terracotta"),
    (228, 129, 57, "minecraft:orange_glazed_terracotta"),
    (202, 75, 186, "minecraft:magenta_glazed_terracotta"),
    (76, 175, 213, "minecraft:light_blue_glazed_terracotta"),
    (235, 229, 57, "minecraft:yellow_glazed_terracotta"),
    (141, 206, 85, "minecraft:lime_glazed_terracotta"),
    (237, 155, 183, "minecraft:pink_glazed_terracotta"),
    (85, 91, 91, "minecraft:gray_glazed_terracotta"),
    (154, 161, 161, "minecraft:light_gray_glazed_terracotta"),
    (57, 196, 197, "minecraft:cyan_glazed_terracotta"),
    (102, 56, 157, "minecraft:purple_glazed_terracotta"),
    (50, 69, 166, "minecraft:blue_glazed_terracotta"),
    (154, 109, 77, "minecraft:brown_glazed_terracotta"),
    (103, 145, 61, "minecraft:green_glazed_terracotta"),
    (188, 74, 74, "minecraft:red_glazed_terracotta"),
    (22, 22, 32, "minecraft:black_glazed_terracotta"),

    # --- Skin tones (using smooth stone, sandstone, and wood variants) ---
    (255, 220, 185, "minecraft:birch_planks"),       # very light peach
    (242, 196, 154, "minecraft:oak_planks"),          # light skin / peach
    (210, 158, 109, "minecraft:jungle_planks"),       # medium tan
    (181, 124, 75,  "minecraft:acacia_planks"),       # medium-dark tan
    (143, 89, 49,   "minecraft:spruce_planks"),       # warm brown skin
    (101, 57, 28,   "minecraft:dark_oak_planks"),     # deep brown skin
    (76,  40, 18,   "minecraft:mangrove_planks"),     # very dark brown
    (236, 188, 168, "minecraft:cherry_planks"),       # pinkish light skin

    # --- Stone / grey spectrum ---
    (200, 200, 200, "minecraft:diorite"),
    (170, 170, 170, "minecraft:andesite"),
    (150, 122, 108, "minecraft:granite"),
    (128, 128, 128, "minecraft:stone"),
    (100, 100, 100, "minecraft:cobblestone"),
    (72,  72,  72,  "minecraft:deepslate"),
    (50,  50,  50,  "minecraft:polished_deepslate"),

    # --- Earth / natural ---
    (245, 220, 130, "minecraft:sand"),
    (200, 175, 100, "minecraft:sandstone"),
    (160, 140, 80,  "minecraft:smooth_sandstone"),
    (134, 96,  67,  "minecraft:dirt"),
    (110, 81,  51,  "minecraft:coarse_dirt"),
    (90,  60,  30,  "minecraft:podzol"),
    (61,  43,  31,  "minecraft:mud"),

    # --- Greens (foliage spectrum) ---
    (106, 144, 50,  "minecraft:oak_leaves"),
    (80,  120, 30,  "minecraft:spruce_leaves"),
    (60,  100, 20,  "minecraft:dark_oak_leaves"),
    (45,  80,  15,  "minecraft:jungle_leaves"),
    (120, 180, 60,  "minecraft:lime_concrete_powder"),

    # --- Warm reds / oranges / pinks ---
    (255, 100, 80,  "minecraft:red_concrete_powder"),
    (255, 153, 51,  "minecraft:orange_concrete_powder"),
    (255, 210, 100, "minecraft:yellow_concrete_powder"),
    (240, 120, 160, "minecraft:pink_concrete_powder"),

    # --- Blues / purples / cyans ---
    (100, 180, 220, "minecraft:light_blue_concrete_powder"),
    (50,  100, 200, "minecraft:blue_concrete_powder"),
    (30,  60,  150, "minecraft:blue_ice"),
    (180, 100, 220, "minecraft:purple_concrete_powder"),
    (140, 60,  200, "minecraft:magenta_concrete_powder"),
    (0,   200, 200, "minecraft:cyan_concrete_powder"),
    (150, 230, 240, "minecraft:packed_ice"),

    # --- Blacks / very darks ---
    (20,  15,  25,  "minecraft:obsidian"),
    (30,  25,  35,  "minecraft:crying_obsidian"),
    (15,  15,  15,  "minecraft:coal_block"),

    # --- Whites / near-whites ---
    (250, 250, 250, "minecraft:snow_block"),
    (220, 240, 255, "minecraft:white_concrete_powder"),
    (245, 245, 220, "minecraft:quartz_block"),
    (235, 225, 200, "minecraft:bone_block"),

    # --- Metallic / special ---
    (220, 180, 50,  "minecraft:gold_block"),
    (180, 180, 185, "minecraft:iron_block"),
    (100, 200, 190, "minecraft:diamond_block"),
    (100, 60,  160, "minecraft:amethyst_block"),
    (60,  160, 80,  "minecraft:emerald_block"),
]

# Pre-compute palette in both RGB and LAB.
_PALETTE_RGB   = np.array([(r, g, b) for r, g, b, _ in BLOCK_PALETTE], dtype=np.float32)
_PALETTE_NAMES = [name for _, _, _, name in BLOCK_PALETTE]
_PALETTE_LAB   = _rgb_to_lab(_PALETTE_RGB)


# Pick the best subset of palette blocks for this specific image.
# Assigns every pixel to its nearest full-palette block, counts usage,
#   then keeps the top **max-colors** most-used blocks.
def select_palette(pixels: np.ndarray, max_colors: int = 24) -> tuple[np.ndarray, list[str]]:

    # Full-palette match in LAB space
    pixels_lab = _rgb_to_lab(pixels.astype(np.float32))
    diff = pixels_lab[:, np.newaxis, :] - _PALETTE_LAB[np.newaxis, :, :]
    distances = np.sum(diff ** 2, axis=2)
    nearest = np.argmin(distances, axis=1)

    # Count how often each palette entry is used
    counts = np.bincount(nearest, minlength=len(_PALETTE_NAMES))

    # Take the top max_colors
    top_indices = np.argsort(counts)[::-1][:max_colors]
    top_indices = np.sort(top_indices)  # Keep original palette order

    sub_rgb = _PALETTE_RGB[top_indices]
    sub_names = [_PALETTE_NAMES[i] for i in top_indices]
    return sub_rgb, sub_names


# Map (N, 3) RGB pixels to block names. If palette is provided, uses that palette.
def map_image_to_blocks(pixels: np.ndarray, palette_rgb: np.ndarray | None = None, palette_names: list[str] | None = None) -> list[str]:

    if palette_rgb is None:
        palette_lab = _PALETTE_LAB
        palette_names = _PALETTE_NAMES
    else:
        palette_lab = _rgb_to_lab(palette_rgb.astype(np.float32))

    pixels_lab = _rgb_to_lab(pixels.astype(np.float32))
    diff = pixels_lab[:, np.newaxis, :] - palette_lab[np.newaxis, :, :]
    distances = np.sum(diff ** 2, axis=2)
    indices = np.argmin(distances, axis=1)
    return [palette_names[i] for i in indices]


# Find nearest block to an RGB color using Euclidean distance.
def nearest_block_from_palette(
    color: np.ndarray,
    palette_rgb: np.ndarray,
    palette_names: list[str],
) -> tuple[str, np.ndarray]:

    color_lab = _rgb_to_lab(np.asarray(color, dtype=np.float32).reshape(1, 3))
    palette_lab = _rgb_to_lab(palette_rgb.astype(np.float32))
    distances = np.sum((palette_lab - color_lab) ** 2, axis=1)
    idx = int(np.argmin(distances))
    return palette_names[idx], palette_rgb[idx]