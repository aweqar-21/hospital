package cn.yujian95.hospital;

import org.junit.Test;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Paths;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class AiChatPageBehaviorTest {

    @Test
    public void executesOfflineBrowserBehaviorHarness() throws Exception {
        assertTrue("Node.js is required for AI chat page behavior tests", nodeIsAvailable());

        File harness = Paths.get("src", "test", "resources", "ai-chat-page-behavior.test.js").toFile();
        File page = Paths.get("src", "main", "resources", "static", "ai-chat.html").toFile();
        Process process = new ProcessBuilder("node", harness.getAbsolutePath(), page.getAbsolutePath())
                .redirectErrorStream(true)
                .start();
        String output = readAll(process.getInputStream());
        assertEquals(output, 0, process.waitFor());
    }

    private boolean nodeIsAvailable() {
        try {
            Process process = new ProcessBuilder("node", "--version").start();
            process.getInputStream().close();
            process.getErrorStream().close();
            return process.waitFor() == 0;
        } catch (IOException exception) {
            return false;
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    private String readAll(InputStream input) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int read;
        while ((read = input.read(buffer)) >= 0) {
            output.write(buffer, 0, read);
        }
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }
}
