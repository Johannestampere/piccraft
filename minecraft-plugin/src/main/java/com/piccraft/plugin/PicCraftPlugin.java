package com.piccraft.plugin;

import org.bukkit.plugin.java.JavaPlugin;

public class PicCraftPlugin extends JavaPlugin {

    private JobPoller poller;

    @Override
    public void onEnable() {
        saveDefaultConfig();

        String backendUrl = getConfig().getString("backend-url", "http://localhost:8000");
        int pollInterval = getConfig().getInt("poll-interval-seconds", 3);
        int blocksPerTick = getConfig().getInt("blocks-per-tick", 200);
        int forwardOffset = getConfig().getInt("forward-offset", 5);

        getLogger().info("Backend URL: " + backendUrl);
        getLogger().info("Poll interval: " + pollInterval + "s");
        getLogger().info("Blocks/tick: " + blocksPerTick);

        BackendClient client = new BackendClient(backendUrl, getLogger());
        BuildExecutor executor = new BuildExecutor(this, getLogger(), blocksPerTick);
        poller = new JobPoller(this, client, executor, getLogger(), pollInterval, forwardOffset);

        poller.start();

        ClearCommand clearCmd = new ClearCommand(executor);
        getCommand("picclear").setExecutor(clearCmd);
        getCommand("picclear").setTabCompleter(clearCmd);

        getLogger().info("PicCraft enabled. Polling for builds...");
    }

    @Override
    public void onDisable() {
        if (poller != null) {
            poller.stop();
        }
        getLogger().info("PicCraft disabled.");
    }
}