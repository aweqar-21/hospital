package cn.yujian95.hospital;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class ReadmeDocumentationTest {

    @Test
    public void readmeHasRequiredSectionsAndNoLegacyAdvertisement() throws Exception {
        String readme = readme();
        String[] headings = {
                "项目简介", "系统架构", "项目结构", "环境要求", "DeepSeek 配置", "本地启动",
                "Docker Compose 启动", "AI 问诊接口", "患者聊天页面", "测试", "医疗免责声明", "安全说明"
        };
        for (String heading : headings) {
            assertTrue("README missing heading: " + heading, readme.contains("## " + heading));
        }

        assertFalse(readme.contains("**收费** ！！！ 技术咨询服务或微信小程序、Web项目开发、官网定制等需求"));
        assertFalse(readme.contains("可加微信：**mo0052**"));
    }

    @Test
    public void deepSeekSectionUsesTheCurrentModelWithoutLegacyAliases() throws Exception {
        String deepSeek = section(readme(), "DeepSeek 配置");

        assertTrue(deepSeek.contains("DEEPSEEK_MODEL=deepseek-v4-flash"));
        assertTrue(deepSeek.contains("LLM_MODEL = 'deepseek-v4-flash'"));
        assertTrue(deepSeek.contains("LLM_MODEL='deepseek-v4-flash'"));
        assertFalse(deepSeek.contains("deepseek-" + "chat"));
        assertFalse(deepSeek.contains("deepseek-" + "reasoner"));
    }

    @Test
    public void localStartupWarnsBeforeDestructiveSqlAndUsesDedicatedDatabaseUser() throws Exception {
        String localStartup = section(readme(), "本地启动");
        int warning = localStartup.indexOf("会执行 `DROP TABLE`");
        int windowsImport = localStartup.indexOf("cmd /c \"mysql -u root -p hospital < src\\main\\resources\\hospital.sql\"");
        int unixImport = localStartup.indexOf("mysql -u root -p hospital < src/main/resources/hospital.sql");

        assertTrue("destructive warning must be explicit", warning >= 0);
        assertTrue(localStartup.contains("仅用于全新或确认可清空的一次性开发数据库"));
        assertTrue(localStartup.contains("已有数据库先备份"));
        assertTrue("warning must precede Windows import", warning < windowsImport);
        assertTrue("warning must precede Unix import", warning < unixImport);

        assertTrue(localStartup.contains("CREATE USER 'hospital_app'@'localhost'"));
        assertTrue(localStartup.contains("GRANT SELECT, INSERT, UPDATE, DELETE ON hospital.* TO 'hospital_app'@'localhost'"));
        assertTrue(localStartup.contains("MYSQL_USERNAME = 'hospital_app'"));
        assertTrue(localStartup.contains("MYSQL_USERNAME='hospital_app'"));
        assertFalse(localStartup.contains("CREATE USER IF NOT EXISTS"));
        assertFalse(localStartup.contains("ALTER USER"));
    }

    @Test
    public void localStartupExplainsWindowsRedisLifecycleAndWslFallback() throws Exception {
        String localStartup = section(readme(), "本地启动");

        assertTrue(localStartup.contains("Docker Desktop"));
        assertTrue(localStartup.contains("Linux containers"));
        assertTrue(localStartup.contains("6379 端口"));
        assertTrue(localStartup.contains("docker run --name hospital-redis"));
        assertTrue(localStartup.contains("docker exec hospital-redis redis-cli ping"));
        assertTrue(localStartup.contains("docker start hospital-redis"));
        assertTrue(localStartup.contains("docker ps -a --filter"));
        assertTrue(localStartup.contains("WSL"));
        assertTrue(localStartup.contains("wsl -l -q"));
        assertTrue(localStartup.contains("<DistroName>"));
        assertFalse(localStartup.contains("wsl -d Ubuntu"));
        assertTrue(localStartup.contains("systemd"));
        assertTrue(localStartup.contains("redis-server --daemonize yes"));
        assertTrue(localStartup.contains("redis-cli ping"));
        assertTrue(localStartup.contains("PONG"));
    }

    @Test
    public void interfaceTestAndSafetySectionsKeepOperationalContract() throws Exception {
        String readme = readme();
        String api = section(readme, "AI 问诊接口");
        String tests = section(readme, "测试");
        String safety = section(readme, "安全说明");

        assertTrue(api.contains("POST /hospital/ai/chat"));
        assertTrue(api.contains("GET /hospital/ai/session/{sessionId}/history"));
        assertTrue(api.contains("DELETE /hospital/ai/session/{sessionId}"));
        assertTrue(api.contains("GET /hospital/ai/health"));
        assertTrue(api.contains("503"));
        assertTrue(tests.contains("python -m pytest"));
        assertTrue(tests.contains("mvn test"));
        assertTrue(safety.contains("匿名"));
        assertTrue(safety.contains("敏感日志"));
    }

    private String readme() throws Exception {
        return new String(Files.readAllBytes(Paths.get("README.md")), StandardCharsets.UTF_8);
    }

    private String section(String readme, String heading) {
        String marker = "## " + heading;
        int start = readme.indexOf(marker);
        assertTrue("README missing section: " + heading, start >= 0);
        int end = readme.indexOf("\n## ", start + marker.length());
        return end < 0 ? readme.substring(start) : readme.substring(start, end);
    }
}
