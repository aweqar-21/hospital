package cn.yujian95.hospital.controller;

import cn.yujian95.hospital.dto.ai.AiChatRequest;
import cn.yujian95.hospital.dto.ai.AiChatResponse;
import cn.yujian95.hospital.exception.AiChatExceptionHandler;
import cn.yujian95.hospital.exception.AiChatClientException;
import cn.yujian95.hospital.exception.AiChatUnavailableException;
import cn.yujian95.hospital.service.AiChatService;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;
import org.springframework.http.MediaType;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.security.Principal;

import static org.junit.Assert.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@RunWith(MockitoJUnitRunner.class)
public class AiChatControllerTest {

    @Mock
    private AiChatService aiChatService;

    private MockMvc mvc;

    @Before
    public void setUp() {
        mvc = MockMvcBuilders.standaloneSetup(new AiChatController(aiChatService))
                .setControllerAdvice(new AiChatExceptionHandler())
                .build();
    }

    @Test
    public void rejectsBlankMessage() throws Exception {
        mvc.perform(post("/ai/chat")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"message\":\"   \"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    public void acceptsAnonymousChatAndWrapsResponse() throws Exception {
        when(aiChatService.chat(any(AiChatRequest.class), any(), any()))
                .thenReturn(new AiChatResponse("session-1", "建议前往内科就诊", "medical", 0.9));

        mvc.perform(post("/ai/chat")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"session_id\":\"session-1\",\"user_id\":\"spoofed\",\"message\":\"我头疼\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.session_id").value("session-1"))
                .andExpect(jsonPath("$.data.reply").value("建议前往内科就诊"))
                .andExpect(jsonPath("$.data.intent").value("medical"))
                .andExpect(jsonPath("$.data.confidence").value(0.9));

        verify(aiChatService).chat(any(AiChatRequest.class), eq(null), eq(null));
    }

    @Test
    public void authenticatedPrincipalOverridesClientUserId() throws Exception {
        when(aiChatService.chat(any(AiChatRequest.class), any(), any()))
                .thenReturn(new AiChatResponse("session-1", "回复", "medical", 0.8));
        Principal principal = new Principal() {
            @Override
            public String getName() {
                return "trusted-user";
            }
        };

        mvc.perform(post("/ai/chat")
                .principal(principal)
                .header("Authorization", "Bearer test-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"user_id\":\"spoofed\",\"message\":\"我头疼\"}"))
                .andExpect(status().isOk());

        ArgumentCaptor<AiChatRequest> requestCaptor = ArgumentCaptor.forClass(AiChatRequest.class);
        verify(aiChatService).chat(requestCaptor.capture(), eq("Bearer test-token"), eq("trusted-user"));
        assertEquals("trusted-user", requestCaptor.getValue().getUserId());
    }

    @Test
    public void returnsSafeServiceUnavailableResponse() throws Exception {
        when(aiChatService.chat(any(AiChatRequest.class), any(), any()))
                .thenThrow(new AiChatUnavailableException());

        mvc.perform(post("/ai/chat")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"message\":\"我头疼\"}"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value(503))
                .andExpect(jsonPath("$.message").value("AI 问诊服务暂时不可用，请稍后重试"));
    }

    @Test
    public void preservesUpstreamClientStatusWithoutReturningItsDetail() throws Exception {
        when(aiChatService.chat(any(AiChatRequest.class), any(), any()))
                .thenThrow(new AiChatClientException(HttpStatus.BAD_REQUEST.value()));

        mvc.perform(post("/ai/chat")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"message\":\"我头疼\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value("AI 问诊请求无效"));
    }

    @Test
    public void doesNotForwardAuthorizationWithoutTrustedPrincipal() throws Exception {
        when(aiChatService.chat(any(AiChatRequest.class), any(), any()))
                .thenReturn(new AiChatResponse("session-1", "回复", "medical", 0.8));

        mvc.perform(post("/ai/chat")
                .header("Authorization", "Bearer untrusted")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"user_id\":\"spoofed\",\"message\":\"我头疼\"}"))
                .andExpect(status().isOk());

        verify(aiChatService).chat(any(AiChatRequest.class), eq(null), eq(null));
    }

    @Test
    public void wrapsHistoryDeleteAndHealthDelegation() throws Exception {
        when(aiChatService.history(eq("session-1"), eq(null), eq(null))).thenReturn("history");
        when(aiChatService.deleteSession(eq("session-1"), eq(null), eq(null))).thenReturn("deleted");
        when(aiChatService.health(eq(null), eq(null))).thenReturn("ok");

        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/ai/session/session-1/history"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").value("history"));
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete("/ai/session/session-1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").value("deleted"));
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/ai/health")
                .header("Authorization", "Bearer ignored"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").value("ok"));
    }
}
