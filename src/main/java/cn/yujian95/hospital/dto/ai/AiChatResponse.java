package cn.yujian95.hospital.dto.ai;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

public class AiChatResponse {

    private String sessionId;
    private String reply;
    private String intent;
    private Double confidence;

    public AiChatResponse() {
    }

    @JsonCreator
    public AiChatResponse(@JsonProperty("session_id") String sessionId,
                          @JsonProperty("reply") String reply,
                          @JsonProperty("intent") String intent,
                          @JsonProperty("confidence") Double confidence) {
        this.sessionId = sessionId;
        this.reply = reply;
        this.intent = intent;
        this.confidence = confidence;
    }

    @JsonProperty("session_id")
    public String getSessionId() {
        return sessionId;
    }

    @JsonProperty("session_id")
    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    @JsonProperty("reply")
    public String getReply() {
        return reply;
    }

    @JsonProperty("reply")
    public void setReply(String reply) {
        this.reply = reply;
    }

    @JsonProperty("intent")
    public String getIntent() {
        return intent;
    }

    @JsonProperty("intent")
    public void setIntent(String intent) {
        this.intent = intent;
    }

    @JsonProperty("confidence")
    public Double getConfidence() {
        return confidence;
    }

    @JsonProperty("confidence")
    public void setConfidence(Double confidence) {
        this.confidence = confidence;
    }
}
