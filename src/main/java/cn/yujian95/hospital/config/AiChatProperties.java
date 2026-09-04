package cn.yujian95.hospital.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "hospital.ai")
public class AiChatProperties {

    private String baseUrl = "http://localhost:8000";
    private int connectTimeoutMs = 3000;
    private int readTimeoutMs = 60000;
    private String proxySecret = "";

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        if (baseUrl == null || baseUrl.trim().isEmpty()) {
            this.baseUrl = "http://localhost:8000";
            return;
        }
        String normalized = baseUrl.trim();
        while (normalized.endsWith("/") && !normalized.endsWith("://")) {
            normalized = normalized.substring(0, normalized.length() - 1);
        }
        this.baseUrl = normalized;
    }

    public int getConnectTimeoutMs() {
        return connectTimeoutMs;
    }

    public void setConnectTimeoutMs(int connectTimeoutMs) {
        this.connectTimeoutMs = connectTimeoutMs;
    }

    public int getReadTimeoutMs() {
        return readTimeoutMs;
    }

    public void setReadTimeoutMs(int readTimeoutMs) {
        this.readTimeoutMs = readTimeoutMs;
    }

    public String getProxySecret() {
        return proxySecret;
    }

    public void setProxySecret(String proxySecret) {
        this.proxySecret = proxySecret == null ? "" : proxySecret;
    }
}
