package com.gahoccode.ingestor.service;

import com.gahoccode.ingestor.config.IngestorProperties;
import com.gahoccode.ingestor.model.ZendeskArticle;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.text.Normalizer;
import java.util.regex.Pattern;

@Service
public class FileWriterService {

    private static final Logger log = LoggerFactory.getLogger(FileWriterService.class);
    private static final Pattern NON_ALPHANUMERIC = Pattern.compile("[^a-z0-9]+");

    private final IngestorProperties properties;
    private final MarkdownConverterService markdownConverterService;

    public FileWriterService(IngestorProperties properties,
                             MarkdownConverterService markdownConverterService) {
        this.properties = properties;
        this.markdownConverterService = markdownConverterService;
    }

    public Path writeArticle(ZendeskArticle article) {
        String markdownBody = markdownConverterService.convert(article.getBody());
        String frontMatter = buildFrontMatter(article);
        String fullContent = frontMatter + "\n" + markdownBody + "\n";

        String slug = slugify(article.getTitle()) + "-" + article.getId() + ".md";
        Path outputDir = Path.of(properties.getOutput().getDir());
        Path filePath = outputDir.resolve(slug);

        try {
            Files.createDirectories(outputDir);
            Files.writeString(filePath, fullContent);
            log.info("Wrote: {}", filePath);
        } catch (IOException e) {
            throw new RuntimeException("Failed to write file: " + filePath, e);
        }

        return filePath;
    }

    private String buildFrontMatter(ZendeskArticle article) {
        return """
                ---
                title: %s
                article_id: %d
                source_url: %s
                updated_at: %s
                ---
                """.formatted(
                escapeYaml(article.getTitle()),
                article.getId(),
                article.getHtmlUrl(),
                article.getUpdatedAt()
        );
    }

    private String escapeYaml(String text) {
        if (text == null) return "";
        if (text.contains(":") || text.contains("\"")) {
            return "\"" + text.replace("\"", "\\\"") + "\"";
        }
        return text;
    }

    private String slugify(String title) {
        if (title == null || title.isBlank()) {
            return "untitled";
        }
        String normalized = Normalizer.normalize(title, Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "");
        String lower = normalized.toLowerCase().trim();
        String slug = NON_ALPHANUMERIC.matcher(lower).replaceAll("-");
        return slug.replaceAll("^-+|-+$", "");
    }
}