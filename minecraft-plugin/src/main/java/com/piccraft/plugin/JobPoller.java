package com.piccraft.plugin;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.plugin.Plugin;
import org.bukkit.scheduler.BukkitTask;

import java.util.Collection;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Logger;

public class JobPoller {

    private final Plugin plugin;
    private final BackendClient client;
    private final BuildExecutor executor;
    private final Logger logger;
    private final int pollIntervalTicks;
    private final int forwardOffset;

    private BukkitTask pollTask;

    // Track processed job+stage combos to avoid duplicates
    private final Set<String> processed = ConcurrentHashMap.newKeySet();

    public JobPoller(Plugin plugin, BackendClient client, BuildExecutor executor,
                     Logger logger, int pollIntervalSeconds, int forwardOffset) {
        this.plugin = plugin;
        this.client = client;
        this.executor = executor;
        this.logger = logger;
        this.pollIntervalTicks = pollIntervalSeconds * 20;
        this.forwardOffset = forwardOffset;
    }

    public void start() {
        logger.info("Starting job poller (interval: " + (pollIntervalTicks / 20) + "s)");
        pollTask = Bukkit.getScheduler().runTaskTimerAsynchronously(plugin, this::pollCycle, 20L, pollIntervalTicks);
    }

    public void stop() {
        if (pollTask != null) {
            pollTask.cancel();
            pollTask = null;
        }
    }

    /**
     * One poll cycle. Runs on an async thread.
     */
    private void pollCycle() {
        client.pollReady().thenAccept(response -> {
            if (response.ready == null || response.ready.isEmpty()) return;

            logger.info("Poll found " + response.ready.size() + " ready stage(s)");

            for (BuildPlan.ReadyStage ready : response.ready) {
                String key = ready.job_id + ":" + ready.stage;
                if (!processed.add(key)) continue;

                client.downloadBuildPlan(ready.job_id, ready.stage)
                        .thenAccept(plan -> {
                            logger.info("[" + ready.job_id + "] Downloaded "
                                    + ready.stage + ": " + plan.blocks.size() + " blocks");

                            // Hand off to main thread for placement
                            Bukkit.getScheduler().runTask(plugin, () -> {
                                Player target = selectPlayer();
                                if (target == null) {
                                    logger.warning("[" + ready.job_id + "] No player online, skipping");
                                    processed.remove(key);
                                    return;
                                }
                                executor.executeBuild(plan, target, forwardOffset);
                            });
                        })
                        .exceptionally(ex -> {
                            logger.severe("[" + ready.job_id + "] Download failed: "
                                    + ex.getMessage());
                            processed.remove(key);
                            return null;
                        });
            }
        });
    }

    private Player selectPlayer() {
        Collection<? extends Player> online = Bukkit.getOnlinePlayers();
        if (online.isEmpty()) return null;
        return online.iterator().next();
    }
}