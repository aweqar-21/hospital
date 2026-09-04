package cn.yujian95.hospital.dto.ai;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class AiChatRequest {

    private String sessionId;
    private String userId;

    @NotBlank
    @Size(max = 4096)
    private String message;

    public AiChatRequest() {
    }

    @JsonCreator
    public AiChatRequest(@JsonProperty("session_id") String sessionId,
                         @JsonProperty("user_id") String userId,
                         @JsonProperty("message") String message) {
        this.sessionId = sessionId;
        this.userId = userId;
        this.message = message;
    }

    @JsonProperty("session_id")
    public String getSessionId() {
        return sessionId;
    }

    @JsonProperty("session_id")
    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    @JsonProperty("user_id")
    public String getUserId() {
        return userId;
    }

    @JsonProperty("user_id")
    public void setUserId(String userId) {
        this.userId = userId;
    }

    @JsonProperty("message")
    public String getMessage() {
        return message;
    }

    @JsonProperty("message")
    public void setMessage(String message) {
        this.message = message;
    }
}
