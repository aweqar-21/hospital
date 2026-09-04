package cn.yujian95.hospital.component;

import cn.yujian95.hospital.controller.AiChatController;
import cn.yujian95.hospital.dto.ai.AiChatRequest;
import org.junit.Test;

import java.lang.reflect.Method;
import java.security.Principal;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

public class WebLogComponentTest {

    @Test
    public void redactsArgumentsAndResultsForSensitiveControllerOperations() throws Exception {
        Method chat = AiChatController.class.getMethod("chat", AiChatRequest.class, String.class, Principal.class);

        assertTrue(WebLogComponent.isSensitiveWebLog(chat));
        assertEquals(WebLogComponent.REDACTED, WebLogComponent.redactIfSensitive(chat, "symptom text"));
        assertNull(WebLogComponent.resolveAccountName(chat, null, "Bearer ", null));
    }
}
