package cn.yujian95.hospital.service.impl;

import cn.yujian95.hospital.config.AiChatProperties;
import cn.yujian95.hospital.dto.ai.AiChatRequest;
import cn.yujian95.hospital.dto.ai.AiChatResponse;
import cn.yujian95.hospital.exception.AiChatUnavailableException;
import cn.yujian95.hospital.exception.AiChatClientException;
import cn.yujian95.hospital.service.AiChatService;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;

@Service
public class AiChatServiceImpl implements AiChatService {

    private final RestTemplate restTemplate;
    private final AiChatProperties properties;

    public AiChatServiceImpl(RestTemplate aiChatRestTemplate, AiChatProperties properties) {
        this.restTemplate = aiChatRestTemplate;
        this.properties = properties;
    }

    @Override
    public AiChatResponse chat(AiChatRequest request, String authorization, String trustedUserId) {
        AiChatRequest upstreamRequest = new AiChatRequest(request.getSessionId(), trustedUserId, request.getMessage());
        ResponseEntity<AiChatResponse> response = invoke(new UpstreamCall<ResponseEntity<AiChatResponse>>() {
            @Override
            public ResponseEntity<AiChatResponse> call() {
                return restTemplate.postForEntity(chatUri(), new HttpEntity<AiChatRequest>(upstreamRequest,
                        headers(trustedUserId)), AiChatResponse.class);
            }
        });
        if (response == null || response.getBody() == null) {
            throw new AiChatUnavailableException();
        }
        return response.getBody();
    }

    @Override
    public Object history(String sessionId, String authorization, String trustedUserId) {
        return body(invoke(new UpstreamCall<ResponseEntity<Object>>() {
            @Override
            public ResponseEntity<Object> call() {
                return restTemplate.exchange(sessionHistoryUri(sessionId), HttpMethod.GET,
                        new HttpEntity<Object>(headers(trustedUserId)), Object.class);
            }
        }));
    }

    @Override
    public Object deleteSession(String sessionId, String authorization, String trustedUserId) {
        return body(invoke(new UpstreamCall<ResponseEntity<Object>>() {
            @Override
            public ResponseEntity<Object> call() {
                return restTemplate.exchange(sessionUri(sessionId), HttpMethod.DELETE,
                        new HttpEntity<Object>(headers(trustedUserId)), Object.class);
            }
        }));
    }

    @Override
    public Object health(String authorization, String trustedUserId) {
        return body(invoke(new UpstreamCall<ResponseEntity<Object>>() {
            @Override
            public ResponseEntity<Object> call() {
                return restTemplate.exchange(pathUri("health"), HttpMethod.GET,
                        new HttpEntity<Object>(headers(null)), Object.class);
            }
        }));
    }

    private Object body(ResponseEntity<Object> response) {
        if (response == null || response.getBody() == null) {
            throw new AiChatUnavailableException();
        }
        return response.getBody();
    }

    private HttpHeaders headers(String trustedUserId) {
        HttpHeaders headers = new HttpHeaders();
        if (StringUtils.hasText(trustedUserId)) {
            headers.set("X-User-Id", trustedUserId);
        }
        if (StringUtils.hasText(properties.getProxySecret())) {
            headers.set("X-AI-Proxy-Secret", properties.getProxySecret());
        }
        return headers;
    }

    private URI chatUri() {
        return pathUri("chat");
    }

    private URI sessionHistoryUri(String sessionId) {
        return UriComponentsBuilder.fromHttpUrl(properties.getBaseUrl())
                .pathSegment("session", sessionId, "history")
                .build()
                .encode()
                .toUri();
    }

    private URI sessionUri(String sessionId) {
        return UriComponentsBuilder.fromHttpUrl(properties.getBaseUrl())
                .pathSegment("session", sessionId)
                .build()
                .encode()
                .toUri();
    }

    private URI pathUri(String path) {
        return UriComponentsBuilder.fromHttpUrl(properties.getBaseUrl())
                .pathSegment(path)
                .build()
                .encode()
                .toUri();
    }

    private <T> T invoke(UpstreamCall<T> call) {
        try {
            return call.call();
        } catch (HttpClientErrorException exception) {
            throw new AiChatClientException(exception.getRawStatusCode());
        } catch (HttpServerErrorException exception) {
            throw new AiChatUnavailableException(exception);
        } catch (ResourceAccessException exception) {
            throw new AiChatUnavailableException(exception);
        } catch (RestClientException exception) {
            throw new AiChatUnavailableException(exception);
        }
    }

    private interface UpstreamCall<T> {
        T call();
    }
}
