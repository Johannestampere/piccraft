package com.piccraft.plugin;

import java.util.List;

public class BuildPlan {

    // GET /api/v0/jobs/ready
    public static class ReadyResponse {
        public List<ReadyStage> ready;
    }

    public static class ReadyStage {
        public String job_id;
        public String stage;
        public String completed_at;
    }

    // GET /api/v0/jobs/{job_id}/stages/{stage}
    public static class Plan {
        public String job_id;
        public String stage;
        public Dimensions dimensions;
        public String orientation;
        public String anchor;
        public List<BlockEntry> blocks;
        public Metadata metadata;
    }

    public static class Dimensions {
        public int width;
        public int height;
        public int depth;
    }

    public static class BlockEntry {
        public int x;
        public int y;
        public int z;
        public String block;
    }

    public static class Metadata {
        public int total_blocks;
        public List<String> palette_used;
        public int processing_time_ms;
    }
}