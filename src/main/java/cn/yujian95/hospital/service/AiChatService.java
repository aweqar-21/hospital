package cn.yujian95.hospital.service;

import cn.yujian95.hospital.dto.ai.AiChatRequest;
import cn.yujian95.hospital.dto.ai.AiChatResponse;

public interface AiChatService {

    AiChatResponse chat(AiChatRequest request, String authorization, String trustedUserId);

    Object history(String sessionId, String authorization, String trustedUserId);

    Object deleteSession(String sessionId, String authorization, String trustedUserId);

    Object health(String authorization, String trustedUserId);
}
