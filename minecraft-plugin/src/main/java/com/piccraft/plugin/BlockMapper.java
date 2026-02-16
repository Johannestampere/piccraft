package com.piccraft.plugin;

import org.bukkit.Material;

import java.util.HashMap;
import java.util.Map;

public class BlockMapper {

    private static final Map<String, Material> BLOCK_MAP = new HashMap<>();

    static {
        // Concrete
        BLOCK_MAP.put("minecraft:white_concrete", Material.WHITE_CONCRETE);
        BLOCK_MAP.put("minecraft:orange_concrete", Material.ORANGE_CONCRETE);
        BLOCK_MAP.put("minecraft:magenta_concrete", Material.MAGENTA_CONCRETE);
        BLOCK_MAP.put("minecraft:light_blue_concrete", Material.LIGHT_BLUE_CONCRETE);
        BLOCK_MAP.put("minecraft:yellow_concrete", Material.YELLOW_CONCRETE);
        BLOCK_MAP.put("minecraft:lime_concrete", Material.LIME_CONCRETE);
        BLOCK_MAP.put("minecraft:pink_concrete", Material.PINK_CONCRETE);
        BLOCK_MAP.put("minecraft:gray_concrete", Material.GRAY_CONCRETE);
        BLOCK_MAP.put("minecraft:light_gray_concrete", Material.LIGHT_GRAY_CONCRETE);
        BLOCK_MAP.put("minecraft:cyan_concrete", Material.CYAN_CONCRETE);
        BLOCK_MAP.put("minecraft:purple_concrete", Material.PURPLE_CONCRETE);
        BLOCK_MAP.put("minecraft:blue_concrete", Material.BLUE_CONCRETE);
        BLOCK_MAP.put("minecraft:brown_concrete", Material.BROWN_CONCRETE);
        BLOCK_MAP.put("minecraft:green_concrete", Material.GREEN_CONCRETE);
        BLOCK_MAP.put("minecraft:red_concrete", Material.RED_CONCRETE);
        BLOCK_MAP.put("minecraft:black_concrete", Material.BLACK_CONCRETE);

        // Wool
        BLOCK_MAP.put("minecraft:white_wool", Material.WHITE_WOOL);
        BLOCK_MAP.put("minecraft:orange_wool", Material.ORANGE_WOOL);
        BLOCK_MAP.put("minecraft:magenta_wool", Material.MAGENTA_WOOL);
        BLOCK_MAP.put("minecraft:light_blue_wool", Material.LIGHT_BLUE_WOOL);
        BLOCK_MAP.put("minecraft:yellow_wool", Material.YELLOW_WOOL);
        BLOCK_MAP.put("minecraft:lime_wool", Material.LIME_WOOL);
        BLOCK_MAP.put("minecraft:pink_wool", Material.PINK_WOOL);
        BLOCK_MAP.put("minecraft:gray_wool", Material.GRAY_WOOL);
        BLOCK_MAP.put("minecraft:light_gray_wool", Material.LIGHT_GRAY_WOOL);
        BLOCK_MAP.put("minecraft:cyan_wool", Material.CYAN_WOOL);
        BLOCK_MAP.put("minecraft:purple_wool", Material.PURPLE_WOOL);
        BLOCK_MAP.put("minecraft:blue_wool", Material.BLUE_WOOL);
        BLOCK_MAP.put("minecraft:brown_wool", Material.BROWN_WOOL);
        BLOCK_MAP.put("minecraft:green_wool", Material.GREEN_WOOL);
        BLOCK_MAP.put("minecraft:red_wool", Material.RED_WOOL);
        BLOCK_MAP.put("minecraft:black_wool", Material.BLACK_WOOL);

        // Terracotta
        BLOCK_MAP.put("minecraft:white_terracotta", Material.WHITE_TERRACOTTA);
        BLOCK_MAP.put("minecraft:orange_terracotta", Material.ORANGE_TERRACOTTA);
        BLOCK_MAP.put("minecraft:magenta_terracotta", Material.MAGENTA_TERRACOTTA);
        BLOCK_MAP.put("minecraft:light_blue_terracotta", Material.LIGHT_BLUE_TERRACOTTA);
        BLOCK_MAP.put("minecraft:yellow_terracotta", Material.YELLOW_TERRACOTTA);
        BLOCK_MAP.put("minecraft:lime_terracotta", Material.LIME_TERRACOTTA);
        BLOCK_MAP.put("minecraft:pink_terracotta", Material.PINK_TERRACOTTA);
        BLOCK_MAP.put("minecraft:gray_terracotta", Material.GRAY_TERRACOTTA);
        BLOCK_MAP.put("minecraft:light_gray_terracotta", Material.LIGHT_GRAY_TERRACOTTA);
        BLOCK_MAP.put("minecraft:cyan_terracotta", Material.CYAN_TERRACOTTA);
        BLOCK_MAP.put("minecraft:purple_terracotta", Material.PURPLE_TERRACOTTA);
        BLOCK_MAP.put("minecraft:blue_terracotta", Material.BLUE_TERRACOTTA);
        BLOCK_MAP.put("minecraft:brown_terracotta", Material.BROWN_TERRACOTTA);
        BLOCK_MAP.put("minecraft:green_terracotta", Material.GREEN_TERRACOTTA);
        BLOCK_MAP.put("minecraft:red_terracotta", Material.RED_TERRACOTTA);
        BLOCK_MAP.put("minecraft:black_terracotta", Material.BLACK_TERRACOTTA);
    }

    public static Material resolve(String blockId) {
        Material mat = BLOCK_MAP.get(blockId);
        if (mat != null) return mat;

        // Dynamic fallback: strip namespace and try Material.valueOf
        String upper = blockId.replace("minecraft:", "").toUpperCase();
        
        try {
            return Material.valueOf(upper);
        } catch (IllegalArgumentException e) {
            return Material.STONE;
        }
    }
}
