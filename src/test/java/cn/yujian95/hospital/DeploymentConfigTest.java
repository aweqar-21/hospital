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
import java.util.regex.Pattern;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class DeploymentConfigTest {

    private static final Path ROOT = Paths.get("");
    private static final Path COMPOSE = ROOT.resolve("docker-compose.yml");
    private static final Path APP_CONFIG = ROOT.resolve(Paths.get("src", "main", "resources", "application.yml"));
    private static final Path ROOT_DOCKERFILE = ROOT.resolve("Dockerfile");
    private static final Path CHATBOT_DOCKERFILE = ROOT.resolve(Paths.get("chatbot-service", "Dockerfile"));
    private static final Path CHATBOT_COMPOSE = ROOT.resolve(Paths.get("chatbot-service", "docker-compose.yml"));
    private static final Path CHATBOT_MAIN = ROOT.resolve(Paths.get("chatbot-service", "main.py"));
    private static final Path CHATBOT_ROUTES = ROOT.resolve(Paths.get("chatbot-service", "api", "routes.py"));
    private static final Path CHATBOT_BOOTSTRAP = ROOT.resolve(Paths.get("chatbot-service", "scripts", "bootstrap.py"));
    private static final Path README = ROOT.resolve("README.md");
    private static final Path CHATBOT_README = ROOT.resolve(Paths.get("chatbot-service", "README.md"));
    private static final Path DOCKERIGNORE = ROOT.resolve(".dockerignore");
    private static final Path ENV_EXAMPLE = ROOT.resolve(".env.example");
    private static final Path CHATBOT_ENV_EXAMPLE = ROOT.resolve(Paths.get("chatbot-service", ".env.example"));
    private static final Path CHATBOT_SETTINGS = ROOT.resolve(Paths.get("chatbot-service", "config", "settings.py"));
    private static final Path SQL_INIT = ROOT.resolve(Paths.get("src", "main", "resources", "hospital.sql"));
    private static final Path REQUIREMENTS_LOCK = ROOT.resolve(Paths.get("chatbot-service", "requirements.lock"));
    private static final Path POM = ROOT.resolve("pom.xml");
    private static final String MAVEN_IMAGE = "maven:3.9.9-eclipse-temurin-8@sha256:e20e4fc05fb5480c884a1f750c362ed0e91aca15cec5736e12796713710ec9b3";
    private static final String JAVA_IMAGE = "eclipse-temurin:8-jre-jammy@sha256:d53aa7811eba390450721b1037978605992f5d9467c4af629384f23a49f78436";
    private static final String PYTHON_IMAGE = "python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6";
    private static final String MYSQL_IMAGE = "mysql:8.4.3@sha256:106d5197fd8e4892980469ad42eb20f7a336bd81509aae4ee175d852f5cc4565";
    private static final String REDIS_IMAGE = "redis:7.4.2-alpine@sha256:02419de7eddf55aa5bcf49efb74e88fa8d931b4d77c07eff8a6b2144472b6952";

    @Test
    public void composeDefinesAHealthyPrivateChatbotStack() throws IOException {
        Map<String, Object> root = yaml(COMPOSE);
        Map<String, Object> services = map(root.get("services"));
        assertTrue(services.keySet().containsAll(java.util.Arrays.asList("mysql", "redis", "chatbot", "hospital")));

        Map<String, Object> mysql = map(services.get("mysql"));
        Map<String, Object> redis = map(services.get("redis"));
        Map<String, Object> chatbot = map(services.get("chatbot"));
        Map<String, Object> hospital = map(services.get("hospital"));

        assertTrue(string(mysql.get("image")).matches("mysql:8(\\.[0-9]+)+@sha256:[a-f0-9]{64}"));
        assertTrue(string(redis.get("image")).matches("redis:7(\\.[0-9]+)*-alpine@sha256:[a-f0-9]{64}"));
        assertTrue(string(mysql.get("restart")).length() > 0);
        assertTrue(string(redis.get("restart")).length() > 0);
        assertTrue(string(chatbot.get("restart")).length() > 0);
        assertTrue(string(hospital.get("restart")).length() > 0);

        assertTrue(map(mysql.get("healthcheck")).containsKey("test"));
        assertTrue(map(redis.get("healthcheck")).containsKey("test"));
        assertTrue(map(chatbot.get("healthcheck")).containsKey("test"));
        assertTrue(map(hospital.get("healthcheck")).containsKey("test"));
        assertTrue(string(map(chatbot.get("healthcheck")).get("test")).contains("/health"));
        assertTrue(string(map(hospital.get("healthcheck")).get("test")).contains("/hospital/actuator/health"));

        assertFalse("chatbot is internal-only", chatbot.containsKey("ports"));
        assertEquals(java.util.Collections.singletonList("127.0.0.1:8080:8080"), list(hospital.get("ports")));
        assertFalse(mysql.containsKey("container_name"));
        assertFalse(redis.containsKey("container_name"));
        assertFalse(chatbot.containsKey("container_name"));
        assertFalse(hospital.containsKey("container_name"));

        assertTrue(contains(string(mysql.get("volumes")), "hospital.sql"));
        assertTrue(contains(string(mysql.get("volumes")), ":ro"));
        assertTrue(contains(string(mysql.get("volumes")), "mysql_data"));
        assertTrue(contains(string(redis.get("volumes")), "redis_data"));
        assertTrue(contains(string(chatbot.get("volumes")), "chatbot_data"));
        assertTrue(map(root.get("volumes")).keySet().containsAll(java.util.Arrays.asList("mysql_data", "redis_data", "chatbot_data")));

        Map<String, Object> chatbotEnvironment = map(chatbot.get("environment"));
        Map<String, Object> hospitalEnvironment = map(hospital.get("environment"));
        Map<String, Object> redisEnvironment = map(redis.get("environment"));
        assertTrue(string(chatbotEnvironment.get("LLM_API_KEY")).contains("${LLM_API_KEY"));
        assertTrue(string(chatbotEnvironment.get("LLM_MODEL")).contains("${DEEPSEEK_MODEL"));
        assertTrue(string(chatbotEnvironment.get("LLM_BASE_URL")).contains("${DEEPSEEK_BASE_URL"));
        assertEquals("${ENABLE_RAG:-false}", string(chatbotEnvironment.get("ENABLE_RAG")));
        assertTrue(string(redisEnvironment.get("REDIS_PASSWORD")).contains("${REDIS_PASSWORD"));
        assertEquals("http://chatbot:8000", string(hospitalEnvironment.get("CHATBOT_BASE_URL")));
        assertTrue(string(hospitalEnvironment.get("MYSQL_URL")).contains("mysql:3306"));
        assertTrue(string(hospitalEnvironment.get("MYSQL_URL")).contains("allowPublicKeyRetrieval=true"));
        assertTrue(string(hospitalEnvironment.get("MYSQL_USERNAME")).contains("${MYSQL_USER"));
        assertTrue(string(hospitalEnvironment.get("MYSQL_PASSWORD")).contains("${MYSQL_PASSWORD"));
        assertEquals("redis", string(hospitalEnvironment.get("REDIS_HOST")));
        assertTrue(string(hospitalEnvironment.get("REDIS_PORT")).contains("${REDIS_PORT"));
        assertTrue(string(hospitalEnvironment.get("REDIS_PASSWORD")).contains("${REDIS_PASSWORD"));
        assertTrue(string(hospitalEnvironment.get("JWT_SECRET")).contains("${JWT_SECRET"));

        Map<String, Object> dependsOn = map(hospital.get("depends_on"));
        for (String dependency : java.util.Arrays.asList("mysql", "redis", "chatbot")) {
            assertEquals("service_healthy", string(map(dependsOn.get(dependency)).get("condition")));
        }
    }

    @Test
    public void runtimeFilesKeepSecretsOutAndSupportContainerHealthChecks() throws IOException {
        String rootDockerfile = text(ROOT_DOCKERFILE);
        String chatbotDockerfile = text(CHATBOT_DOCKERFILE);
        String dockerignore = text(DOCKERIGNORE);
        String envExample = text(ENV_EXAMPLE);

        assertTrue(rootDockerfile.contains("maven:"));
        assertTrue(rootDockerfile.contains("-DskipTests package"));
        assertTrue(rootDockerfile.contains("target/hospital.jar"));
        assertTrue(rootDockerfile.contains("EXPOSE 8080"));
        assertTrue(rootDockerfile.toLowerCase().contains("curl"));
        assertTrue(chatbotDockerfile.contains("python:3.11-slim"));
        assertEquals("/app", dockerfileInstruction(chatbotDockerfile, "WORKDIR"));
        assertTrue(chatbotDockerfile.contains("COPY . ."));
        assertFalse("Source copied into WORKDIR must not require an editable package build", chatbotDockerfile.matches("(?s).*pip\\s+install[^\\n]*\\s-e(?:\\s|$).*"));
        assertTrue("The copied source must be importable directly from WORKDIR", chatbotDockerfile.contains("api.routes:app"));
        assertTrue(chatbotDockerfile.contains("curl"));
        assertTrue(chatbotDockerfile.contains("EXPOSE 8000"));

        assertTrue(dockerignore.contains(".git"));
        assertTrue(dockerignore.contains(".worktrees"));
        assertTrue(dockerignore.contains("target"));
        assertTrue(dockerignore.contains(".env"));
        assertTrue(dockerignore.contains("!.env.example"));
        assertTrue(dockerignore.contains("__pycache__"));
        assertTrue(dockerignore.contains(".venv"));
        assertTrue(dockerignore.contains("data"));
        assertTrue(dockerignore.contains("logs"));

        assertTrue(envExample.contains("LLM_API_KEY="));
        assertTrue(envExample.contains("DEEPSEEK_MODEL="));
        assertTrue(envExample.contains("DEEPSEEK_BASE_URL="));
        assertTrue(envExample.contains("ENABLE_RAG=false"));
        assertTrue(envExample.contains("CHATBOT_BASE_URL="));
        assertTrue(envExample.contains("MYSQL_DATABASE="));
        assertTrue(envExample.contains("MYSQL_USER="));
        assertTrue(envExample.contains("MYSQL_PASSWORD="));
        assertTrue(envExample.contains("MYSQL_ROOT_PASSWORD="));
        assertTrue(envExample.contains("REDIS_HOST="));
        assertTrue(envExample.contains("REDIS_PORT="));
        assertTrue(envExample.contains("REDIS_PASSWORD="));
        assertTrue(envExample.contains("JWT_SECRET="));
        assertEmptyEnvironmentVariable(envExample, "LLM_API_KEY");
        assertEmptyEnvironmentVariable(envExample, "JWT_SECRET");
        assertNoLiteralCredentials(rootDockerfile, chatbotDockerfile, envExample);
    }

    @Test
    public void applicationConfigReadsDeploymentEnvironmentWithoutChangingTheAiWhitelist() throws IOException {
        String rawConfig = text(APP_CONFIG);
        Map<String, Object> root = new Yaml().load(rawConfig);
        Map<String, Object> spring = map(root.get("spring"));
        Map<String, Object> datasource = map(spring.get("datasource"));
        Map<String, Object> redis = map(spring.get("redis"));
        Map<String, Object> jwt = map(root.get("jwt"));
        Map<String, Object> hospital = map(root.get("hospital"));
        Map<String, Object> ai = map(hospital.get("ai"));
        List<Object> whitelist = list(map(map(root.get("secure")).get("ignored")).get("urls"));

        assertTrue(string(datasource.get("url")).contains("${MYSQL_URL:"));
        assertTrue(string(datasource.get("url")).contains("allowPublicKeyRetrieval=true"));
        assertTrue(string(datasource.get("username")).contains("${MYSQL_USERNAME:"));
        assertTrue(string(datasource.get("password")).contains("${MYSQL_PASSWORD:"));
        assertTrue(string(redis.get("host")).contains("${REDIS_HOST:"));
        assertTrue(string(redis.get("port")).contains("${REDIS_PORT:"));
        assertTrue(string(redis.get("password")).contains("${REDIS_PASSWORD:"));
        assertTrue(string(jwt.get("secret")).contains("${JWT_SECRET:"));
        assertTrue(string(ai.get("base-url")).contains("${CHATBOT_BASE_URL:"));
        assertTrue(whitelist.contains("/ai/**"));
        assertTrue(whitelist.contains("/ai-chat.html"));
        assertFalse(whitelist.contains("/**"));
    }

    @Test
    public void sqlInitDoesNotHardCodeTheComposeDatabaseName() throws IOException {
        String sql = text(SQL_INIT);

        assertTrue(sql.contains("SET FOREIGN_KEY_CHECKS"));
        assertFalse("The Compose MYSQL_DATABASE substitution must select the target schema", sql.contains("`hospital`."));
    }

    @Test
    public void deploymentUsesAuthenticatedHealthChecksRequiredSecretsAndReproducibleNonRootImages() throws IOException {
        Map<String, Object> compose = yaml(COMPOSE);
        Map<String, Object> services = map(compose.get("services"));
        Map<String, Object> mysql = map(services.get("mysql"));
        Map<String, Object> redis = map(services.get("redis"));
        Map<String, Object> chatbot = map(services.get("chatbot"));
        Map<String, Object> hospital = map(services.get("hospital"));
        String mysqlHealthcheck = string(map(mysql.get("healthcheck")).get("test"));
        String rootDockerfile = text(ROOT_DOCKERFILE);
        String chatbotDockerfile = text(CHATBOT_DOCKERFILE);
        String dockerignore = text(DOCKERIGNORE);
        String envExample = text(ENV_EXAMPLE);
        String requirementsLock = text(REQUIREMENTS_LOCK);

        assertTrue(mysqlHealthcheck.contains("MYSQL_PWD=\"$$MYSQL_PASSWORD\""));
        assertTrue(mysqlHealthcheck.contains("mysql --protocol=TCP -h 127.0.0.1 -u \"$$MYSQL_USER\" -D \"$$MYSQL_DATABASE\" -e \"SELECT 1\""));
        assertFalse(mysqlHealthcheck.contains("mysqladmin"));
        assertFalse("Do not put the password in an unquoted -p argument", mysqlHealthcheck.matches("(?s).*\\s-p\\S+.*"));

        Map<String, Object> hospitalEnvironment = map(hospital.get("environment"));
        assertEquals("${JWT_SECRET:?JWT_SECRET is required}", string(hospitalEnvironment.get("JWT_SECRET")));
        assertEquals(java.util.Collections.singletonList("127.0.0.1:8080:8080"), list(hospital.get("ports")));
        assertEquals("${ENABLE_RAG:-false}", string(map(chatbot.get("environment")).get("ENABLE_RAG")));

        assertDockerfileBaseImages(rootDockerfile, MAVEN_IMAGE, JAVA_IMAGE);
        assertDockerfileBaseImages(chatbotDockerfile, PYTHON_IMAGE);
        assertEquals(MYSQL_IMAGE, string(mysql.get("image")));
        assertEquals(REDIS_IMAGE, string(redis.get("image")));
        assertFalse(string(mysql.get("image")).contains(":latest"));
        assertFalse(string(redis.get("image")).contains(":latest"));

        assertTrue(rootDockerfile.contains("USER hospital"));
        assertTrue(chatbotDockerfile.contains("USER chatbot"));
        assertTrue(rootDockerfile.contains("chown -R hospital:hospital /app"));
        assertTrue(chatbotDockerfile.contains("chown -R chatbot:chatbot /app"));
        assertTrue(chatbotDockerfile.contains("COPY requirements.lock ."));
        assertTrue(chatbotDockerfile.contains("pip install --no-cache-dir -r requirements.lock"));
        assertFalse(chatbotDockerfile.matches("(?s).*pip\\s+install[^\\n]*\\s-e(?:\\s|$).*"));
        assertFalse(chatbotDockerfile.contains("pip install --no-cache-dir uvicorn[standard]"));
        assertTrue(dockerignore.contains("/chatbot-service/"));
        assertTrue(requirementsLock.contains("fastapi=="));
        assertTrue(requirementsLock.contains("uvicorn=="));
        assertTrue(requirementsLock.contains("chromadb=="));
        assertFalse(Pattern.compile("(?m)^\\s*[A-Za-z0-9_.-]+>=.*$").matcher(requirementsLock).find());

        assertNoLiteralCredentials(rootDockerfile, chatbotDockerfile, text(COMPOSE), text(APP_CONFIG), envExample, requirementsLock);
    }

    @Test
    public void qiniuDependencyUsesTheKnownCompatibleResolvedVersion() throws IOException {
        String pom = text(POM);

        assertTrue(pom.matches("(?s).*<artifactId>qiniu-java-sdk</artifactId>\\s*<version>7\\.2\\.29</version>.*"));
        assertFalse(pom.matches("(?s).*<artifactId>qiniu-java-sdk</artifactId>\\s*<version>\\s*[\\[(].*"));
    }

    @Test
    public void deepSeekDefaultsUseTheCurrentSupportedModel() throws IOException {
        String compose = text(COMPOSE);
        String rootEnv = text(ENV_EXAMPLE);
        String chatbotEnv = text(CHATBOT_ENV_EXAMPLE);
        String settings = text(CHATBOT_SETTINGS);

        assertTrue(compose.contains("${DEEPSEEK_MODEL:-deepseek-v4-flash}"));
        assertTrue(rootEnv.contains("DEEPSEEK_MODEL=deepseek-v4-flash"));
        assertTrue(chatbotEnv.contains("LLM_MODEL=deepseek-v4-flash"));
        assertTrue(settings.contains("LLM_MODEL: str = \"deepseek-v4-flash\""));
        for (String content : java.util.Arrays.asList(compose, rootEnv, chatbotEnv, settings)) {
            assertFalse(content.contains("deepseek-" + "chat"));
            assertFalse(content.contains("deepseek-" + "reasoner"));
        }
    }

    @Test
    public void aiProxyTrustBoundaryAndBearerSafeStartupAreDeploymentContracts() throws IOException {
        Map<String, Object> root = yaml(COMPOSE);
        Map<String, Object> services = map(root.get("services"));
        Map<String, Object> chatbotEnvironment = map(map(services.get("chatbot")).get("environment"));
        Map<String, Object> hospitalEnvironment = map(map(services.get("hospital")).get("environment"));
        Map<String, Object> child = yaml(CHATBOT_COMPOSE);
        Map<String, Object> childServices = map(child.get("services"));
        Map<String, Object> childChatbot = map(childServices.get("chatbot"));
        String requiredSecret = "${AI_PROXY_SECRET:?AI_PROXY_SECRET is required}";
        String chatbotDockerfile = text(CHATBOT_DOCKERFILE);
        String main = text(CHATBOT_MAIN);
        String routes = text(CHATBOT_ROUTES);
        String bootstrap = text(CHATBOT_BOOTSTRAP);
        String readmes = text(README) + "\n" + text(CHATBOT_README);

        assertEquals(requiredSecret, string(chatbotEnvironment.get("AI_PROXY_SECRET")));
        assertEquals(requiredSecret, string(hospitalEnvironment.get("AI_PROXY_SECRET")));
        assertEmptyEnvironmentVariable(text(ENV_EXAMPLE), "AI_PROXY_SECRET");
        assertEmptyEnvironmentVariable(text(CHATBOT_ENV_EXAMPLE), "AI_PROXY_SECRET");
        assertEquals(java.util.Collections.singletonList("127.0.0.1:8000:8000"), list(childChatbot.get("ports")));
        assertEquals(java.util.Collections.singletonList("127.0.0.1:6379:6379"), list(map(childServices.get("redis")).get("ports")));
        assertEquals(java.util.Collections.singletonList("127.0.0.1:8001:8000"), list(map(childServices.get("chroma")).get("ports")));

        assertTrue(chatbotDockerfile.contains("--no-access-log"));
        assertTrue(main.contains("port=8000"));
        assertTrue(main.contains("reload=False"));
        assertTrue(main.contains("access_log=False"));
        assertTrue(bootstrap.contains("--no-access-log"));
        assertFalse(Pattern.compile("(?m)^.*uvicorn(?!.*--no-access-log).*$").matcher(readmes).find());

        assertFalse(routes.contains("allow_origins=[\"*\"]"));
        assertFalse(routes.contains("allow_credentials=True"));
        assertFalse(routes.contains("allow_methods=[\"*\"]"));
        assertFalse(routes.contains("allow_headers=[\"*\"]"));
    }

    private Map<String, Object> yaml(Path path) throws IOException {
        assertTrue("Missing deployment file: " + path, Files.isRegularFile(path));
        return new Yaml().load(text(path));
    }

    private String text(Path path) throws IOException {
        assertTrue("Missing deployment file: " + path, Files.isRegularFile(path));
        return new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> map(Object value) {
        assertTrue("Expected YAML map", value instanceof Map);
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    private List<Object> list(Object value) {
        assertTrue("Expected YAML list", value instanceof List);
        return (List<Object>) value;
    }

    private String string(Object value) {
        return String.valueOf(value);
    }

    private boolean contains(String renderedList, String value) {
        return renderedList.contains(value);
    }

    private void assertNoLiteralCredentials(String... texts) {
        for (String value : texts) {
            assertFalse(value.contains("sk-"));
            assertFalse(value.contains("DeepSeek API Key"));
            assertFalse("Private keys must not be committed", value.contains("-----BEGIN PRIVATE KEY-----"));
            assertFalse("GitHub tokens must not be committed", Pattern.compile("gh[pousr]_[A-Za-z0-9]{20,}").matcher(value).find());
            assertFalse("AWS access keys must not be committed", Pattern.compile("AKIA[0-9A-Z]{16}").matcher(value).find());
        }
    }

    private void assertDockerfileBaseImages(String dockerfile, String... approvedReferences) {
        java.util.regex.Matcher matcher = Pattern.compile("(?m)^FROM[ \\t]+([^ \\t\\r\\n]+)").matcher(dockerfile);
        java.util.ArrayList<String> actualReferences = new java.util.ArrayList<>();
        while (matcher.find()) {
            actualReferences.add(matcher.group(1));
        }
        assertEquals("Dockerfile must use only the reviewed digest-pinned references", java.util.Arrays.asList(approvedReferences), actualReferences);
    }

    private void assertEmptyEnvironmentVariable(String envFile, String name) {
        assertTrue("Expected " + name + " to be present and empty", Pattern.compile("(?m)^" + Pattern.quote(name) + "=[ \\t]*$").matcher(envFile).find());
        assertFalse("Expected no committed value for " + name, Pattern.compile("(?m)^" + Pattern.quote(name) + "=[ \\t]*[^\\s#]").matcher(envFile).find());
    }

    private String dockerfileInstruction(String dockerfile, String instruction) {
        java.util.regex.Matcher matcher = Pattern.compile("(?m)^" + Pattern.quote(instruction) + "[ \\t]+(.+?)[ \\t]*$").matcher(dockerfile);
        assertTrue("Missing Dockerfile instruction " + instruction, matcher.find());
        return matcher.group(1);
    }
}
