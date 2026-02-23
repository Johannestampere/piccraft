package com.piccraft.plugin;

import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;

import java.util.ArrayList;
import java.util.List;

public class ClearCommand implements CommandExecutor, TabCompleter {

    private final BuildExecutor executor;

    public ClearCommand(BuildExecutor executor) {
        this.executor = executor;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (args.length == 0 || args[0].equalsIgnoreCase("last")) {
            String cleared = executor.clearLast();
            if (cleared == null) {
                sender.sendMessage("[PicCraft] No active builds to clear.");
            } else {
                sender.sendMessage("[PicCraft] Clearing build: " + cleared);
            }
            return true;
        }

        String jobId = args[0];
        boolean found = executor.clearJob(jobId);
        if (found) {
            sender.sendMessage("[PicCraft] Clearing build: " + jobId);
        } else {
            sender.sendMessage("[PicCraft] No build found with id: " + jobId);
        }
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String label, String[] args) {
        List<String> completions = new ArrayList<>();
        if (args.length == 1) {
            completions.add("last");
            for (String id : executor.getActiveJobIds()) {
                if (id.startsWith(args[0])) completions.add(id);
            }
        }
        return completions;
    }
}
