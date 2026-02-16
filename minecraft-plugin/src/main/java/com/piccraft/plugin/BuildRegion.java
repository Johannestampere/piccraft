package com.piccraft.plugin;

import org.bukkit.Location;
import org.bukkit.World;

import java.util.ArrayList;
import java.util.List;

/**
 * Tracks every block placed for a job so the region
 * can be cleared before a replacement stage is placed.
 */
public class BuildRegion {

    private final String jobId;
    private final String stage;
    private final World world;
    private final List<Location> placedBlocks;

    public BuildRegion(String jobId, String stage, World world) {
        this.jobId = jobId;
        this.stage = stage;
        this.world = world;
        this.placedBlocks = new ArrayList<>();
    }

    public String getJobId() { return jobId; }
    public String getStage() { return stage; }
    public World getWorld() { return world; }
    public List<Location> getPlacedBlocks() { return placedBlocks; }

    public void addBlock(Location loc) {
        placedBlocks.add(loc);
    }

    public int size() {
        return placedBlocks.size();
    }
}