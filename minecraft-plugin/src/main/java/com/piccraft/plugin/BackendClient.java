package com.piccraft.plugin;

import com.google.gson.Gson;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.logging.Logger;

public class BackendClient {

    private final HttpClient httpClient;
    private final Gson gson;
    private final String baseUrl;
    private final Logger logger;

    public BackendClient(String baseUrl, Logger logger) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.logger = logger;
        this.gson = new Gson();
        this.httpClient = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(Duration.ofSeconds(5))
            .build();
    }

    /**
     * Poll GET /api/v0/jobs/ready.
     * Returns on the HTTP thread pool
     */
    public CompletableFuture<BuildPlan.ReadyResponse> pollReady() {
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/api/v0/jobs/ready"))
            .timeout(Duration.ofSeconds(10))
            .GET()
            .build();

        return httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
            .thenApply(response -> {
                if (response.statusCode() != 200) {
                    logger.warning("Poll /ready returned " + response.statusCode());
                    return emptyResponse();
                }
                return gson.fromJson(response.body(), BuildPlan.ReadyResponse.class);
            })
            .exceptionally(ex -> {
                logger.warning("Poll /ready failed: " + ex.getMessage());
                return emptyResponse();
            });
    }

    /**
     * Download a build plan: GET /api/v0/jobs/{jobId}/stages/{stage}.
     */
    public CompletableFuture<BuildPlan.Plan> downloadBuildPlan(String jobId, String stage) {
        String url = baseUrl + "/api/v0/jobs/" + jobId + "/stages/" + stage;

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(30))
                .GET()
                .build();

        return httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(response -> {
                    if (response.statusCode() != 200) {
                        throw new RuntimeException("Download build plan failed: HTTP " + response.statusCode());
                    }
                    return gson.fromJson(response.body(), BuildPlan.Plan.class);
                });
    }

    private static BuildPlan.ReadyResponse emptyResponse() {
        BuildPlan.ReadyResponse r = new BuildPlan.ReadyResponse();
        r.ready = List.of();
        return r;
    }
}