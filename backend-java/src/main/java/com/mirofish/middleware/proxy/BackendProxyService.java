package com.mirofish.middleware.proxy;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

@Service
public class BackendProxyService {

    private static final Set<String> HOP_BY_HOP_HEADERS = Set.of(
            "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
            "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length"
    );

    private final HttpClient httpClient;

    public BackendProxyService(@Value("${app.proxy.timeout-seconds:300}") long timeoutSeconds) {
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .followRedirects(HttpClient.Redirect.NORMAL)
                .build();
        this.timeout = Duration.ofSeconds(Math.max(10, timeoutSeconds));
    }

    private final Duration timeout;

    public ResponseEntity<byte[]> forward(HttpServletRequest incoming, byte[] body, String upstreamBaseUrl)
            throws IOException, InterruptedException {
        String targetUrl = buildTargetUrl(incoming, upstreamBaseUrl);
        HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(targetUrl)).timeout(timeout);

        copyRequestHeaders(incoming, builder);
        String method = incoming.getMethod().toUpperCase(Locale.ROOT);

        boolean hasBody = switch (method) {
            case "POST", "PUT", "PATCH", "DELETE" -> true;
            default -> false;
        };
        HttpRequest.BodyPublisher publisher =
                (hasBody && body != null && body.length > 0)
                        ? HttpRequest.BodyPublishers.ofByteArray(body)
                        : HttpRequest.BodyPublishers.noBody();
        builder.method(method, publisher);

        HttpResponse<byte[]> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofByteArray());
        return toSpringResponse(response);
    }

    private String buildTargetUrl(HttpServletRequest incoming, String upstreamBaseUrl) {
        String base = upstreamBaseUrl.endsWith("/") ? upstreamBaseUrl.substring(0, upstreamBaseUrl.length() - 1) : upstreamBaseUrl;
        String path = incoming.getRequestURI();
        String query = incoming.getQueryString();
        return query == null || query.isBlank() ? base + path : base + path + "?" + query;
    }

    private void copyRequestHeaders(HttpServletRequest incoming, HttpRequest.Builder builder) {
        Enumeration<String> names = incoming.getHeaderNames();
        while (names != null && names.hasMoreElements()) {
            String name = names.nextElement();
            if (HOP_BY_HOP_HEADERS.contains(name.toLowerCase(Locale.ROOT))) {
                continue;
            }
            Enumeration<String> values = incoming.getHeaders(name);
            while (values.hasMoreElements()) {
                builder.header(name, values.nextElement());
            }
        }
    }

    private ResponseEntity<byte[]> toSpringResponse(HttpResponse<byte[]> response) {
        HttpHeaders headers = new HttpHeaders();
        for (Map.Entry<String, java.util.List<String>> entry : response.headers().map().entrySet()) {
            String headerName = entry.getKey();
            if (HOP_BY_HOP_HEADERS.contains(headerName.toLowerCase(Locale.ROOT))) {
                continue;
            }
            headers.put(headerName, new ArrayList<>(entry.getValue()));
        }
        HttpStatus status = HttpStatus.resolve(response.statusCode());
        if (status == null) {
            status = HttpStatus.BAD_GATEWAY;
        }
        return new ResponseEntity<>(response.body(), headers, status);
    }
}
