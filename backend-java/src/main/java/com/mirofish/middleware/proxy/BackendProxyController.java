package com.mirofish.middleware.proxy;

import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.util.UUID;

import static org.springframework.web.bind.annotation.RequestMethod.DELETE;
import static org.springframework.web.bind.annotation.RequestMethod.GET;
import static org.springframework.web.bind.annotation.RequestMethod.OPTIONS;
import static org.springframework.web.bind.annotation.RequestMethod.PATCH;
import static org.springframework.web.bind.annotation.RequestMethod.POST;
import static org.springframework.web.bind.annotation.RequestMethod.PUT;

@RestController
public class BackendProxyController {
    private static final Logger log = LoggerFactory.getLogger(BackendProxyController.class);

    private final BackendProxyService proxyService;
    private final String graphBaseUrl;
    private final String simulationBaseUrl;
    private final String reportBaseUrl;

    public BackendProxyController(
            BackendProxyService proxyService,
            @Value("${app.proxy.graph-base-url}") String graphBaseUrl,
            @Value("${app.proxy.simulation-base-url}") String simulationBaseUrl,
            @Value("${app.proxy.report-base-url}") String reportBaseUrl
    ) {
        this.proxyService = proxyService;
        this.graphBaseUrl = graphBaseUrl;
        this.simulationBaseUrl = simulationBaseUrl;
        this.reportBaseUrl = reportBaseUrl;
    }

    @RequestMapping(
            value = {
                    "/api/graph", "/api/graph/**",
                    "/api/simulation", "/api/simulation/**",
                    "/api/report", "/api/report/**"
            },
            method = {GET, POST, PUT, PATCH, DELETE, OPTIONS}
    )
    public ResponseEntity<byte[]> proxy(
            HttpServletRequest request
    ) throws IOException, InterruptedException {
        String requestId = UUID.randomUUID().toString().substring(0, 8);
        String path = request.getRequestURI();
        String base = resolveBase(path);
        String query = request.getQueryString();
        log.info(
                "[proxy:{}] inbound method={} path={} query={} contentType={} contentLength={}",
                requestId,
                request.getMethod(),
                path,
                query == null ? "" : query,
                request.getContentType(),
                request.getContentLengthLong()
        );

        // Use raw request bytes to preserve multipart/form-data boundaries.
        byte[] body = request.getInputStream().readAllBytes();
        log.info("[proxy:{}] forwarding to base={} bodyBytes={}", requestId, base, body == null ? 0 : body.length);

        try {
            ResponseEntity<byte[]> response = proxyService.forward(request, body, base, requestId);
            log.info(
                    "[proxy:{}] outbound status={} responseBytes={}",
                    requestId,
                    response.getStatusCode().value(),
                    response.getBody() == null ? 0 : response.getBody().length
            );
            return response;
        } catch (IOException | InterruptedException e) {
            log.error("[proxy:{}] forwarding failed: {}", requestId, e.getMessage(), e);
            throw e;
        }
    }

    private String resolveBase(String path) {
        if (path.startsWith("/api/graph")) {
            return graphBaseUrl;
        }
        if (path.startsWith("/api/simulation")) {
            return simulationBaseUrl;
        }
        if (path.startsWith("/api/report")) {
            return reportBaseUrl;
        }
        throw new IllegalArgumentException("Unsupported proxy path: " + path);
    }
}
