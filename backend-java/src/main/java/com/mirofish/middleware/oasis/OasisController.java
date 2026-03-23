package com.mirofish.middleware.oasis;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/oasis")
@Tag(name = "OASIS", description = "OASIS bridge status")
public class OasisController {

    @Value("${app.oasis.mode:legacy-proxy}")
    private String oasisMode;

    @GetMapping("/health")
    @Operation(summary = "Check OASIS bridge mode")
    public Map<String, Object> health() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("success", true);
        data.put("service", "oasis-bridge");
        data.put("mode", oasisMode);
        data.put("message", "OASIS is preserved via middleware bridge.");
        return data;
    }
}
