package cn.yujian95.hospital.common.security;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import org.junit.Test;
import org.slf4j.LoggerFactory;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

public class JwtTokenUtilTest {

    @Test
    public void doesNotLogRawJwtWhenParsingFails() {
        JwtTokenUtil tokenUtil = new JwtTokenUtil();
        ReflectionTestUtils.setField(tokenUtil, "secret", "test-secret");
        String rawToken = "distinctive.invalid.jwt.token";
        Logger logger = (Logger) LoggerFactory.getLogger(JwtTokenUtil.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<ILoggingEvent>();
        appender.start();
        logger.addAppender(appender);

        try {
            assertNull(tokenUtil.getUserNameFromToken(rawToken));
            assertFalse(appender.list.isEmpty());
            boolean genericFailureLogged = false;
            for (ILoggingEvent event : appender.list) {
                String message = event.getFormattedMessage();
                assertFalse(message.contains(rawToken));
                genericFailureLogged = genericFailureLogged || message.contains("JWT格式验证失败");
            }
            assertTrue(genericFailureLogged);
        } finally {
            logger.detachAppender(appender);
            appender.stop();
        }
    }
}
