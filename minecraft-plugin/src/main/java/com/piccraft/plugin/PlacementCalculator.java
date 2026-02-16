package com.piccraft.plugin;

import org.bukkit.Location;
import org.bukkit.entity.Player;

public class PlacementCalculator {

    /**
     * Compute the world origin for plan coordinate (0, 0, 0).
     *
     * anchor = "bottom_center": centered horizontally, bottom at player Y.
     * The build is placed forwardOffset blocks in front of the player.
     */
    public static Location computeOrigin(
            Player player, 
            BuildPlan.Dimensions dims,
            String anchor, 
            int forwardOffset) {

        Location loc = player.getLocation();
        CardinalDirection facing = CardinalDirection.fromYaw(loc.getYaw());

        int px = loc.getBlockX();
        int py = loc.getBlockY();
        int pz = loc.getBlockZ();

        int halfWidth = dims.width / 2;

        // Forward from player, then shift left by half width to center the build
        int originX = px + facing.forwardX * forwardOffset - facing.rightX * halfWidth;
        int originZ = pz + facing.forwardZ * forwardOffset - facing.rightZ * halfWidth;

        return new Location(player.getWorld(), originX, py, originZ);
    }

    /**
     * Transform plan coordinate (bx, by, bz) to world location.
     *
     * Plan coords: x = left-to-right, y = up, z = depth (away from viewer).
     */
    public static Location planToWorld(Location origin, int bx, int by, int bz, CardinalDirection facing) {
        int worldX = origin.getBlockX() + facing.rightX * bx + facing.forwardX * bz;
        int worldY = origin.getBlockY() + by;
        int worldZ = origin.getBlockZ() + facing.rightZ * bx + facing.forwardZ * bz;

        return new Location(origin.getWorld(), worldX, worldY, worldZ);
    }

    /**
     * Minecraft yaw: 0 = South, 90 = West, 180 = North, 270 = East.
     * Each direction has a forward vector and a right vector in world XZ.
     */
    public enum CardinalDirection {
        SOUTH(0, 1, -1, 0),
        WEST(-1, 0, 0, -1),
        NORTH(0, -1, 1, 0),
        EAST(1, 0, 0, 1);

        public final int forwardX, forwardZ, rightX, rightZ;

        CardinalDirection(int forwardX, int forwardZ, int rightX, int rightZ) {
            this.forwardX = forwardX;
            this.forwardZ = forwardZ;
            this.rightX = rightX;
            this.rightZ = rightZ;
        }

        public static CardinalDirection fromYaw(float yaw) {
            float normalized = ((yaw % 360) + 360) % 360;
            if (normalized >= 315 || normalized < 45) return SOUTH;
            if (normalized < 135) return WEST;
            if (normalized < 225) return NORTH;
            return EAST;
        }
    }
}