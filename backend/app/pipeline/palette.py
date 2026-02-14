import numpy as np

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
]

# Pre-compute numpy array of all 48 palette colors.
_PALETTE_RGB = np.array(
    [(r, g, b) for r, g, b, _ in BLOCK_PALETTE], dtype=np.float32
)
_PALETTE_NAMES = [name for _, _, _, name in BLOCK_PALETTE]


# Pick the best subset of palette blocks for this specific image.
# Assigns every pixel to its nearest full-palette block, counts usage,
#   then keeps the top **max-colors** most-used blocks.
def select_palette(pixels: np.ndarray, max_colors: int = 24) -> tuple[np.ndarray, list[str]]:

    # Full-palette match for every pixel
    diff = pixels[:, np.newaxis, :].astype(np.float32) - _PALETTE_RGB[np.newaxis, :, :]
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
def map_image_to_blocks(
    pixels: np.ndarray,
    palette_rgb: np.ndarray | None = None,
    palette_names: list[str] | None = None,
) -> list[str]:

    if palette_rgb is None:
        palette_rgb = _PALETTE_RGB
        palette_names = _PALETTE_NAMES

    diff = pixels[:, np.newaxis, :].astype(np.float32) - palette_rgb[np.newaxis, :, :]
    distances = np.sum(diff ** 2, axis=2)
    indices = np.argmin(distances, axis=1)
    return [palette_names[i] for i in indices]


# Find nearest block to an RGB color using Euclidean distance.
def nearest_block_from_palette(
    color: np.ndarray,
    palette_rgb: np.ndarray,
    palette_names: list[str],
) -> tuple[str, np.ndarray]:

    color = np.asarray(color, dtype=np.float32)
    distances = np.sum((palette_rgb - color) ** 2, axis=1)
    idx = int(np.argmin(distances))
    return palette_names[idx], palette_rgb[idx]