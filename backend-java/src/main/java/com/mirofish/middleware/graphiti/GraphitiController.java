package com.mirofish.middleware.graphiti;

import com.fasterxml.jackson.databind.JsonNode;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Min;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@Validated
@RestController
@RequestMapping(value = "/api/graphiti", produces = MediaType.APPLICATION_JSON_VALUE)
@Tag(name = "Graphiti", description = "Graphiti API facade from Java middle layer")
public class GraphitiController {

    private final GraphitiClient graphitiClient;

    public GraphitiController(GraphitiClient graphitiClient) {
        this.graphitiClient = graphitiClient;
    }

    @GetMapping("/healthcheck")
    @Operation(summary = "Graphiti health check")
    public JsonNode healthcheck() {
        return graphitiClient.get("/healthcheck", Map.of());
    }

    @PostMapping("/messages")
    @Operation(summary = "Add messages to Graphiti")
    public JsonNode addMessages(@RequestBody JsonNode payload) {
        return graphitiClient.post("/messages", payload);
    }

    @PostMapping("/search")
    @Operation(summary = "Search Graphiti")
    public JsonNode search(@RequestBody JsonNode payload) {
        return graphitiClient.post("/search", payload);
    }

    @GetMapping("/get-memory/{groupId}")
    @Operation(summary = "Get memory by group id")
    public JsonNode getMemory(@PathVariable String groupId) {
        return graphitiClient.get("/get-memory/" + groupId, Map.of());
    }

    @GetMapping("/episodes/{groupId}")
    @Operation(summary = "Get episodes by group id")
    public JsonNode getEpisodes(
            @PathVariable String groupId,
            @RequestParam(name = "last_n", defaultValue = "10") @Min(1) int lastN
    ) {
        return graphitiClient.get("/episodes/" + groupId, Map.of("last_n", String.valueOf(lastN)));
    }

    @GetMapping("/episode/{episodeUuid}")
    @Operation(summary = "Get episode by uuid")
    public JsonNode getEpisode(@PathVariable String episodeUuid) {
        return graphitiClient.get("/episode/" + episodeUuid, Map.of());
    }

    @PostMapping("/entity-node")
    @Operation(summary = "Create entity node")
    public JsonNode createEntityNode(@RequestBody JsonNode payload) {
        return graphitiClient.post("/entity-node", payload);
    }

    @GetMapping("/entity-edge/{edgeUuid}")
    @Operation(summary = "Get entity edge by uuid")
    public JsonNode getEntityEdge(@PathVariable String edgeUuid) {
        return graphitiClient.get("/entity-edge/" + edgeUuid, Map.of());
    }

    @DeleteMapping("/entity-edge/{edgeUuid}")
    @Operation(summary = "Delete entity edge by uuid")
    public JsonNode deleteEntityEdge(@PathVariable String edgeUuid) {
        return graphitiClient.delete("/entity-edge/" + edgeUuid);
    }

    @PostMapping("/clear")
    @Operation(summary = "Clear Graphiti data by payload conditions")
    public JsonNode clear(@RequestBody(required = false) JsonNode payload) {
        return graphitiClient.post("/clear", payload == null ? com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode() : payload);
    }
}
