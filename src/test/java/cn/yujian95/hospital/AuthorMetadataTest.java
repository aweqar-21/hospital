package cn.yujian95.hospital;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class AuthorMetadataTest {

    private static final String EXPECTED_AUTHOR =
            "@author AWEQAR_21 aweqar1225918785@gmail.com";
    private static final Pattern LEGACY_JAVA_AUTHOR = Pattern.compile(
            "(?i)@author\\s+(?:YuJian95|yujian|chenlijian)\\b");

    @Test
    public void projectUsesCurrentAuthorMetadataWithoutLegacyAttribution() throws Exception {
        String javaSources = readJavaSources(Paths.get("src/main/java"));
        String pom = read(Paths.get("pom.xml"));
        String pyproject = read(Paths.get("chatbot-service/pyproject.toml"));
        String inspectedMetadata = javaSources + "\n" + pom + "\n" + pyproject;

        assertFalse("legacy email clj9509@163.com remains",
                inspectedMetadata.contains("clj9509@163.com"));
        assertFalse("legacy email yujian95_cn@163.com remains",
                inspectedMetadata.contains("yujian95_cn@163.com"));
        assertFalse("legacy project URL remains",
                inspectedMetadata.contains("blog.yujian95.cn"));
        assertFalse("legacy Java @author remains",
                LEGACY_JAVA_AUTHOR.matcher(javaSources).find());
        assertFalse("legacy Swagger author credit remains",
                javaSources.contains("Created by yujian95"));
        assertFalse("legacy Swagger project URL remains",
                javaSources.contains("github.com/YuJian95"));
        assertFalse("legacy Swagger service URL remains",
                javaSources.contains("https://yujian95.cn"));

        assertTrue("new Java @author is missing", javaSources.contains(EXPECTED_AUTHOR));
        assertTrue("current Swagger maintainer credit is missing",
                javaSources.contains("Maintained by AWEQAR_21"));
        assertTrue("new Python author metadata is missing", pyproject.contains(
                "{name = \"AWEQAR_21\", email = \"aweqar1225918785@gmail.com\"}"));
        assertTrue("new Maven project URL is missing",
                pom.contains("<url>https://github.com/aweqar-21/hospital</url>"));
    }

    private String readJavaSources(Path sourceRoot) throws Exception {
        try (Stream<Path> paths = Files.walk(sourceRoot)) {
            return paths
                    .filter(Files::isRegularFile)
                    .filter(path -> path.toString().endsWith(".java"))
                    .sorted()
                    .map(this::readUnchecked)
                    .collect(Collectors.joining("\n"));
        }
    }

    private String readUnchecked(Path path) {
        try {
            return read(path);
        } catch (Exception exception) {
            throw new IllegalStateException("Unable to read " + path, exception);
        }
    }

    private String read(Path path) throws Exception {
        return new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
    }
}
