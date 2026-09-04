package cn.yujian95.hospital.service;

import cn.yujian95.hospital.config.AiChatProperties;
import cn.yujian95.hospital.dto.ai.AiChatRequest;
import cn.yujian95.hospital.dto.ai.AiChatResponse;
import cn.yujian95.hospital.exception.AiChatUnavailableException;
import cn.yujian95.hospital.exception.AiChatClientException;
import cn.yujian95.hospital.service.impl.AiChatServiceImpl;
import org.junit.Before;
import org.junit.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.client.RequestMatcher;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.net.URI;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

public class AiChatServiceImplTest {

    private RestTemplate restTemplate;
    private MockRestServiceServer server;
    private AiChatServiceImpl service;

    @Before
    public void setUp() {
        restTemplate = new RestTemplate();
        server = MockRestServiceServer.bindTo(restTemplate).build();
        AiChatProperties properties = new AiChatProperties();
        properties.setBaseUrl("http://localhost:8000/");
        properties.setProxySecret("test-proxy-secret");
        service = new AiChatServiceImpl(restTemplate, properties);
    }

    @Test
    public void postsExactPayloadAndTrustedHeadersWithoutBrowserBearerToken() {
        server.expect(requestTo("http://localhost:8000/chat"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(noHeader(HttpHeaders.AUTHORIZATION))
                .andExpect(header("X-User-Id", "trusted-user"))
                .andExpect(header("X-AI-Proxy-Secret", "test-proxy-secret"))
                .andExpect(content().json("{\"session_id\":\"session-1\",\"user_id\":\"trusted-user\",\"message\":\"我头疼\"}"))
                .andRespond(withSuccess("{\"session_id\":\"session-1\",\"reply\":\"建议就医\",\"intent\":\"medical\",\"confidence\":0.9}", MediaType.APPLICATION_JSON));

        AiChatResponse response = service.chat(new AiChatRequest("session-1", "spoofed", "我头疼"),
                "Bearer test-token", "trusted-user");

        assertEquals("session-1", response.getSessionId());
        assertEquals("建议就医", response.getReply());
        assertEquals("medical", response.getIntent());
        assertEquals(Double.valueOf(0.9), response.getConfidence());
        server.verify();
    }

    @Test
    public void anonymousChatDoesNotForwardAuthorizationOrUserHeader() {
        server.expect(requestTo("http://localhost:8000/chat"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(noHeader(HttpHeaders.AUTHORIZATION))
                .andExpect(noHeader("X-User-Id"))
                .andExpect(header("X-AI-Proxy-Secret", "test-proxy-secret"))
                .andExpect(content().json("{\"session_id\":\"session-1\",\"message\":\"我头疼\"}"))
                .andRespond(withSuccess("{\"session_id\":\"session-1\",\"reply\":\"建议就医\",\"intent\":\"medical\",\"confidence\":0.9}", MediaType.APPLICATION_JSON));

        service.chat(new AiChatRequest("session-1", "spoofed", "我头疼"), null, null);
        server.verify();
    }

    @Test
    public void encodesSessionIdAsOnePathSegment() {
        server.expect(requestTo("http://localhost:8000/session/a%2Fb%20c/history"))
                .andExpect(method(HttpMethod.GET))
                .andExpect(header("X-AI-Proxy-Secret", "test-proxy-secret"))
                .andRespond(withSuccess("[]", MediaType.APPLICATION_JSON));

        service.history("a/b c", null, null);
        server.verify();
    }

    @Test(expected = AiChatUnavailableException.class)
    public void mapsUpstreamServerErrorToUnavailable() {
        server.expect(requestTo("http://localhost:8000/chat"))
                .andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE));

        service.chat(new AiChatRequest(null, null, "我头疼"), null, null);
    }

    @Test(expected = AiChatClientException.class)
    public void mapsUpstreamClientErrorToSanitizedClientException() {
        server.expect(requestTo("http://localhost:8000/chat"))
                .andRespond(withStatus(HttpStatus.BAD_REQUEST));

        service.chat(new AiChatRequest(null, null, "我头疼"), null, null);
    }

    @Test
    public void healthNeverForwardsAuthorization() {
        server.expect(requestTo("http://localhost:8000/health"))
                .andExpect(noHeader(HttpHeaders.AUTHORIZATION))
                .andExpect(noHeader("X-User-Id"))
                .andExpect(header("X-AI-Proxy-Secret", "test-proxy-secret"))
                .andRespond(withSuccess("{\"status\":\"ok\"}", MediaType.APPLICATION_JSON));

        service.health("Bearer should-not-leak", "alice");
        server.verify();
    }

    @Test(expected = AiChatUnavailableException.class)
    public void mapsNullResponseBodyToUnavailable() {
        server.expect(requestTo("http://localhost:8000/chat"))
                .andRespond(withSuccess("", MediaType.APPLICATION_JSON));

        service.chat(new AiChatRequest(null, null, "我头疼"), null, null);
    }

    @Test(expected = AiChatUnavailableException.class)
    public void mapsMalformedResponseBodyToUnavailable() {
        server.expect(requestTo("http://localhost:8000/chat"))
                .andRespond(withSuccess("not-json", MediaType.APPLICATION_JSON));

        service.chat(new AiChatRequest(null, null, "我头疼"), null, null);
    }

    @Test(expected = AiChatUnavailableException.class)
    public void mapsResourceAccessFailureToUnavailable() {
        RestTemplate failingTemplate = mock(RestTemplate.class);
        when(failingTemplate.postForEntity(any(URI.class), any(), any()))
                .thenThrow(new ResourceAccessException("connection refused"));
        AiChatProperties properties = new AiChatProperties();
        AiChatServiceImpl failingService = new AiChatServiceImpl(failingTemplate, properties);

        try {
            failingService.chat(new AiChatRequest(null, null, "我头疼"), null, null);
        } finally {
            verify(failingTemplate).postForEntity(any(URI.class), any(), any());
        }
    }

    private RequestMatcher noHeader(final String name) {
        return request -> assertNull("unexpected " + name + " header", request.getHeaders().getFirst(name));
    }
}
