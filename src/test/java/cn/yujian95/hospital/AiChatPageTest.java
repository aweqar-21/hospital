package cn.yujian95.hospital;

import org.junit.Test;
import org.yaml.snakeyaml.Yaml;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class AiChatPageTest {

    private static final Path PAGE = Paths.get("src", "main", "resources", "static", "ai-chat.html");
    private static final Path APPLICATION_YML = Paths.get("src", "main", "resources", "application.yml");

    @Test
    public void patientAiChatPageProvidesSafeAccessibleConsultationUi() throws IOException {
        assertTrue("AI consultation page should exist", Files.isRegularFile(PAGE));
        String html = readUtf8(PAGE);

        assertTrue(html.contains("AI 健康咨询"));
        assertTrue(html.contains("不能替代医生"));
        assertTrue(html.contains("急诊"));
        assertTrue(html.contains("新建会话"));
        assertTrue(html.contains("/ai/chat"));
        assertTrue(html.contains("maxLength=\"4096\""));
        assertTrue(html.contains("hospitalAiSessionId"));
        assertTrue(html.contains("aria-live"));
        assertTrue(html.contains("textContent"));
        assertTrue(html.contains("<meta name=\"viewport\""));
        assertTrue(html.contains("@media"));
        assertTrue(html.contains("localStorage.getItem"));
        assertTrue(html.contains("getStorageItem('token')"));
        assertTrue(html.contains("getStorageItem('Authorization')"));
        assertTrue(html.contains("getStorageItem('hospitalToken')"));
        assertTrue(html.contains("function getStorageItem"));
        assertTrue(html.contains("function setStorageItem"));
        assertTrue(html.contains("function removeStorageItem"));
        assertTrue(html.contains("setStorageItem(SESSION_STORAGE_KEY"));
        assertTrue(html.contains("removeStorageItem(SESSION_STORAGE_KEY"));
        assertTrue(countOccurrences(html, "localStorage.setItem(") == 1);
        assertTrue(countOccurrences(html, "localStorage.removeItem(") == 1);
        assertTrue(countOccurrences(html, "localStorage.getItem(") == 1);
        assertFalse(html.contains("deepseek"));
        assertFalse(html.contains("innerHTML"));
        assertFalse(html.contains("localStorage.setItem('token'"));
        assertFalse(html.contains("localStorage.setItem(\"token\""));
        assertFalse(html.contains("localStorage.setItem('Authorization'"));
        assertFalse(html.contains("localStorage.setItem(\"Authorization\""));
        assertFalse(html.contains("localStorage.setItem('hospitalToken'"));
        assertFalse(html.contains("localStorage.setItem(\"hospitalToken\""));
        assertFalse(html.contains("localStorage.removeItem('token'"));
        assertFalse(html.contains("localStorage.removeItem(\"token\""));
        assertFalse(html.contains("localStorage.removeItem('Authorization'"));
        assertFalse(html.contains("localStorage.removeItem(\"Authorization\""));
        assertFalse(html.contains("localStorage.removeItem('hospitalToken'"));
        assertFalse(html.contains("localStorage.removeItem(\"hospitalToken\""));
    }

    @Test
    public void securityWhitelistExposesOnlyAiProxyAndChatPage() throws IOException {
        Map<String, Object> root = new Yaml().load(readUtf8(APPLICATION_YML));
        Map<String, Object> secure = map(root.get("secure"));
        Map<String, Object> ignored = map(secure.get("ignored"));
        List<Object> urls = list(ignored.get("urls"));

        assertTrue(urls.contains("/ai/**"));
        assertTrue(urls.contains("/ai-chat.html"));
        assertFalse(urls.contains("/**"));
    }

    private String readUtf8(Path path) throws IOException {
        return new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
    }

    private int countOccurrences(String value, String needle) {
        int count = 0;
        int index = 0;
        while ((index = value.indexOf(needle, index)) >= 0) {
            count++;
            index += needle.length();
        }
        return count;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> map(Object value) {
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    private List<Object> list(Object value) {
        return (List<Object>) value;
    }
}
