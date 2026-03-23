package com.mirofish.middleware.proxy;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;

import static org.springframework.web.bind.annotation.RequestMethod.DELETE;
import static org.springframework.web.bind.annotation.RequestMethod.GET;
import static org.springframework.web.bind.annotation.RequestMethod.OPTIONS;
import static org.springframework.web.bind.annotation.RequestMethod.PATCH;
import static org.springframework.web.bind.annotation.RequestMethod.POST;
import static org.springframework.web.bind.annotation.RequestMethod.PUT;

@RestController
public class BackendProxyController {

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
            HttpServletRequest request,
            @RequestBody(required = false) byte[] body
    ) throws IOException, InterruptedException {
        String path = request.getRequestURI();
        String base = resolveBase(path);
        return proxyService.forward(request, body, base);
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
