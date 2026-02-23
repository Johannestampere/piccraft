package com.piccraft.plugin;

import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;

import java.util.ArrayList;
import java.util.List;

public class MoveCommand implements CommandExecutor, TabCompleter {

    private final BuildExecutor executor;
    private final int forwardOffset;

    public MoveCommand(BuildExecutor executor, int forwardOffset) {
        this.executor = executor;
        this.forwardOffset = forwardOffset;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("[PicCraft] This command requires a player.");
            return true;
        }

        if (args.length == 0 || args[0].equalsIgnoreCase("last")) {
            String moved = executor.moveLast(player, forwardOffset);
            if (moved == null) {
                sender.sendMessage("[PicCraft] No active builds to move.");
            } else {
                sender.sendMessage("[PicCraft] Moving build: " + moved);
            }
            return true;
        }

        String jobId = args[0];
        boolean found = executor.moveJob(jobId, player, forwardOffset);
        if (found) {
            sender.sendMessage("[PicCraft] Moving build: " + jobId);
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