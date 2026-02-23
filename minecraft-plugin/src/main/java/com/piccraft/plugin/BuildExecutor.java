package com.piccraft.plugin;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.plugin.Plugin;
import org.bukkit.scheduler.BukkitTask;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Logger;

public class BuildExecutor {

    private final Plugin plugin;
    private final Logger logger;
    private final int blocksPerTick;

    // Latest placed region per job (for clearing on replacement)
    private final Map<String, BuildRegion> activeRegions = new ConcurrentHashMap<>();

    // Placement origin per job (locked on first stage, reused for replacements)
    private final Map<String, OriginInfo> origins = new ConcurrentHashMap<>();

    // Most recently placed job id
    private volatile String lastJobId = null;

    public BuildExecutor(Plugin plugin, Logger logger, int blocksPerTick) {
        this.plugin = plugin;
        this.logger = logger;
        this.blocksPerTick = blocksPerTick;
    }

    public static class OriginInfo {
        public final Location origin;
        public final PlacementCalculator.CardinalDirection facing;

        public OriginInfo(Location origin, PlacementCalculator.CardinalDirection facing) {
            this.origin = origin;
            this.facing = facing;
        }
    }

    /**
     * Execute a build plan: clear previous stage, then place new blocks.
     * Must be called from the main thread.
     */
    public void executeBuild(BuildPlan.Plan plan, Player player, int forwardOffset) {
        String jobId = plan.job_id;
        long startTime = System.currentTimeMillis();

        logger.info("[" + jobId + "] Executing stage: " + plan.stage
                + " (" + plan.blocks.size() + " blocks)");

        // Get or compute placement origin
        OriginInfo info = origins.get(jobId);

        if (info == null) {
            Location origin = PlacementCalculator.computeOrigin(player, plan.dimensions, plan.anchor, forwardOffset);

            PlacementCalculator.CardinalDirection facing = PlacementCalculator.CardinalDirection.fromYaw(player.getLocation().getYaw());

            info = new OriginInfo(origin, facing);
            origins.put(jobId, info);

            logger.info("[" + jobId + "] Origin: " + origin.getBlockX()
                    + ", " + origin.getBlockY() + ", " + origin.getBlockZ()
                    + " facing " + facing.name());
        }

        // Blocks to clear from previous stage
        BuildRegion previous = activeRegions.get(jobId);
        List<Location> toClear = (previous != null)
                ? new ArrayList<>(previous.getPlacedBlocks())
                : Collections.emptyList();

        // Compute world locations for new blocks
        OriginInfo finalInfo = info;
        List<Map.Entry<Location, Material>> toPlace = new ArrayList<>();

        for (BuildPlan.BlockEntry entry : plan.blocks) {
            Location worldLoc = PlacementCalculator.planToWorld(finalInfo.origin, entry.x, entry.y, entry.z, finalInfo.facing);
            Material mat = BlockMapper.resolve(entry.block);
            toPlace.add(Map.entry(worldLoc, mat));
        }

        // New region to track what we place
        BuildRegion newRegion = new BuildRegion(jobId, plan.stage, finalInfo.origin.getWorld());

        // Run batched clear + place
        new BatchedTask(toClear, toPlace, newRegion, () -> {
            activeRegions.put(jobId, newRegion);
            lastJobId = jobId;
            long elapsed = System.currentTimeMillis() - startTime;

            logger.info("[" + jobId + "] Stage " + plan.stage + " placed: " + newRegion.size() + " blocks in " + elapsed + "ms");

            if (player.isOnline()) {
                player.sendMessage("[PicCraft] " + plan.stage + " placed! (" + newRegion.size() + " blocks, " + elapsed + "ms)");
            }
        }).start();
    }

    /**
     * Clear the blocks placed for a specific job. Returns false if job not found.
     */
    public boolean clearJob(String jobId) {
        BuildRegion region = activeRegions.remove(jobId);
        origins.remove(jobId);
        if (region == null) return false;

        List<Location> toClear = new ArrayList<>(region.getPlacedBlocks());
        
        new BatchedTask(toClear, Collections.emptyList(), new BuildRegion(jobId, "cleared", region.getWorld()), () -> {
            if (jobId.equals(lastJobId)) lastJobId = null;
        }).start();

        return true;
    }

    /**
     * Clear the most recently placed build. Returns the job id cleared, or null if none.
     */
    public String clearLast() {
        if (lastJobId == null) return null;
        String id = lastJobId;
        clearJob(id);
        return id;
    }

    public java.util.Set<String> getActiveJobIds() {
        return activeRegions.keySet();
    }

    /**
     * Batched tick-by-tick block placement.
     * Phase 1: clear old blocks (set AIR). Phase 2: place new blocks.
     * Shares the per-tick budget across both phases.
     */
    private class BatchedTask {
        private final List<Location> clearList;
        private final List<Map.Entry<Location, Material>> placeList;
        private final BuildRegion newRegion;
        private final Runnable onComplete;

        private int clearIdx = 0;
        private int placeIdx = 0;
        private BukkitTask task;

        BatchedTask(List<Location> clearList, List<Map.Entry<Location, Material>> placeList,
                    BuildRegion newRegion, Runnable onComplete) {
            this.clearList = clearList;
            this.placeList = placeList;
            this.newRegion = newRegion;
            this.onComplete = onComplete;
        }

        void start() {
            task = Bukkit.getScheduler().runTaskTimer(plugin, this::tick, 0L, 1L);
        }

        private void tick() {
            int remaining = blocksPerTick;

            // Phase 1: clear
            while (remaining > 0 && clearIdx < clearList.size()) {
                clearList.get(clearIdx).getBlock().setType(Material.AIR, false);
                clearIdx++;
                remaining--;
            }

            // Phase 2: place
            while (remaining > 0 && placeIdx < placeList.size()) {
                Map.Entry<Location, Material> entry = placeList.get(placeIdx);
                Location loc = entry.getKey();

                if (!loc.getChunk().isLoaded()) {
                    loc.getChunk().load();
                }

                loc.getBlock().setType(entry.getValue(), false);
                newRegion.addBlock(loc);
                placeIdx++;
                remaining--;
            }

            // Done
            if (clearIdx >= clearList.size() && placeIdx >= placeList.size()) {
                task.cancel();
                onComplete.run();
            }
        }
    }
}