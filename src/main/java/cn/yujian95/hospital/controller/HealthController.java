package cn.yujian95.hospital.controller;

import cn.yujian95.hospital.common.api.CommonResult;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * 健康检查接口
 *
 * @author AWEQAR_21 aweqar1225918785@gmail.com
 */
@Api(value = "健康检查模块", tags = "健康检查接口")
@RestController
@CrossOrigin
@RequestMapping("/health")
public class HealthController {

    @ApiOperation(value = "心跳检测", notes = "检查服务是否正常运行")
    @RequestMapping(value = "/heartbeat", method = RequestMethod.GET)
    public CommonResult<Map<String, Object>> heartbeat() {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "UP");
        result.put("timestamp", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        return CommonResult.success(result, "服务运行正常");
    }
}
