package com.mirofish.middleware.graphiti;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.stream.Collectors;

@Component
public class GraphitiClient {

    private final String baseUrl;
    private final String apiKey;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final Duration timeout;

    public GraphitiClient(
            @Value("${app.graphiti.base-url}") String baseUrl,
            @Value("${app.graphiti.api-key:}") String apiKey,
            @Value("${app.graphiti.timeout-seconds:30}") long timeoutSeconds,
            ObjectMapper objectMapper
    ) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.apiKey = apiKey == null ? "" : apiKey.trim();
        this.timeout = Duration.ofSeconds(Math.max(5, timeoutSeconds));
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        this.objectMapper = objectMapper;
    }

    public JsonNode get(String path, Map<String, String> query) {
        return send("GET", path, null, query);
    }

    public JsonNode post(String path, JsonNode payload) {
        return send("POST", path, payload, null);
    }

    public JsonNode delete(String path) {
        return send("DELETE", path, null, null);
    }

    private JsonNode send(String method, String path, JsonNode payload, Map<String, String> query) {
        String url = buildUrl(path, query);
        try {
            HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(url))
                    .timeout(timeout)
                    .header("Accept", "application/json")
                    .header("Content-Type", "application/json");
            if (!apiKey.isBlank()) {
                builder.header("Authorization", "Bearer " + apiKey);
            }
            String body = payload == null ? "" : objectMapper.writeValueAsString(payload);
            HttpRequest.BodyPublisher publisher =
                    payload == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofString(body);
            builder.method(method, publisher);

            HttpResponse<String> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofString());
            int code = response.statusCode();
            if (code < 200 || code >= 300) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_GATEWAY,
                        "Graphiti request failed: HTTP " + code + ", body: " + response.body()
                );
            }
            String respBody = response.body();
            if (respBody == null || respBody.isBlank()) {
                return objectMapper.createObjectNode();
            }
            return objectMapper.readTree(respBody);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Graphiti request error: " + e.getMessage(), e);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Graphiti request error: " + e.getMessage(), e);
        }
    }

    private String buildUrl(String path, Map<String, String> query) {
        String normalizedPath = path.startsWith("/") ? path : "/" + path;
        if (query == null || query.isEmpty()) {
            return baseUrl + normalizedPath;
        }
        String qs = query.entrySet().stream()
                .filter(e -> e.getValue() != null)
                .map(e -> URLEncoder.encode(e.getKey(), StandardCharsets.UTF_8)
                        + "=" + URLEncoder.encode(e.getValue(), StandardCharsets.UTF_8))
                .collect(Collectors.joining("&"));
        return baseUrl + normalizedPath + (qs.isBlank() ? "" : "?" + qs);
    }
}
