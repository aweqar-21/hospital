package cn.yujian95.hospital.exception;

import cn.yujian95.hospital.common.api.CommonResult;
import cn.yujian95.hospital.controller.AiChatController;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.bind.MethodArgumentNotValidException;

@RestControllerAdvice(assignableTypes = AiChatController.class)
public class AiChatExceptionHandler {

    private static final String UNAVAILABLE_MESSAGE = "AI 问诊服务暂时不可用，请稍后重试";

    @ExceptionHandler(AiChatUnavailableException.class)
    public ResponseEntity<CommonResult<Void>> handleUnavailable(AiChatUnavailableException exception) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(CommonResult.failed(HttpStatus.SERVICE_UNAVAILABLE.value(), UNAVAILABLE_MESSAGE));
    }

    @ExceptionHandler(AiChatClientException.class)
    public ResponseEntity<CommonResult<Void>> handleClientError(AiChatClientException exception) {
        return ResponseEntity.status(exception.getStatusCode())
                .body(CommonResult.failed(exception.getStatusCode(), "AI 问诊请求无效"));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<CommonResult<Void>> handleValidationError(MethodArgumentNotValidException exception) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                .body(CommonResult.failed(HttpStatus.BAD_REQUEST.value(), "请求参数错误"));
    }
}
