package cn.yujian95.hospital.exception;

/** A sanitized representation of a client error returned by the AI service. */
public class AiChatClientException extends RuntimeException {

    private final int statusCode;

    public AiChatClientException(int statusCode) {
        this.statusCode = statusCode;
    }

    public int getStatusCode() {
        return statusCode;
    }
}
