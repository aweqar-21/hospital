package cn.yujian95.hospital.controller;

import cn.yujian95.hospital.common.api.CommonResult;
import cn.yujian95.hospital.component.SensitiveWebLog;
import cn.yujian95.hospital.dto.ai.AiChatRequest;
import cn.yujian95.hospital.dto.ai.AiChatResponse;
import cn.yujian95.hospital.service.AiChatService;
import org.springframework.http.HttpHeaders;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.validation.Valid;
import java.security.Principal;

@RestController
@RequestMapping("/ai")
@SensitiveWebLog
public class AiChatController {

    private final AiChatService aiChatService;

    public AiChatController(AiChatService aiChatService) {
        this.aiChatService = aiChatService;
    }

    @PostMapping("/chat")
    public CommonResult<AiChatResponse> chat(@Valid @RequestBody AiChatRequest request,
                                             @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization,
                                             Principal principal) {
        String trustedUserId = trustedUserId(principal);
        request.setUserId(trustedUserId);
        return CommonResult.success(aiChatService.chat(request, forwardedAuthorization(authorization, trustedUserId), trustedUserId));
    }

    @GetMapping("/session/{sessionId}/history")
    public CommonResult<Object> history(@PathVariable String sessionId,
                                        @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization,
                                        Principal principal) {
        String trustedUserId = trustedUserId(principal);
        return CommonResult.success(aiChatService.history(sessionId, forwardedAuthorization(authorization, trustedUserId), trustedUserId));
    }

    @DeleteMapping("/session/{sessionId}")
    public CommonResult<Object> deleteSession(@PathVariable String sessionId,
                                              @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization,
                                              Principal principal) {
        String trustedUserId = trustedUserId(principal);
        return CommonResult.success(aiChatService.deleteSession(sessionId, forwardedAuthorization(authorization, trustedUserId), trustedUserId));
    }

    @GetMapping("/health")
    public CommonResult<Object> health(@RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization,
                                       Principal principal) {
        return CommonResult.success(aiChatService.health(null, null));
    }

    private String trustedUserId(Principal principal) {
        if (principal == null || principal.getName() == null || principal.getName().trim().isEmpty()) {
            return null;
        }
        return principal.getName();
    }

    private String forwardedAuthorization(String authorization, String trustedUserId) {
        return trustedUserId != null && StringUtils.hasText(authorization) ? authorization : null;
    }
}
