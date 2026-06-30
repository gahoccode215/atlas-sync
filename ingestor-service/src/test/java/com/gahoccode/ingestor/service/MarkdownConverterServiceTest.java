package com.gahoccode.ingestor.service;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

public class MarkdownConverterServiceTest {
    private final MarkdownConverterService converter = new MarkdownConverterService();

    @Test
    void shouldConvertHeadingsAndParagraphs() {
        String html = "<h2>Getting Started</h2><p>This is a test.</p>";
        String md = converter.convert(html);

        assertThat(md).contains("## Getting Started");
        assertThat(md).contains("This is a test.");
    }

    @Test
    void shouldPreserveCodeBlocks() {
        String html = "<pre><code>const x = 1;</code></pre>";
        String md = converter.convert(html);

        assertThat(md).contains("```");
        assertThat(md).contains("const x = 1;");
    }

    @Test
    void shouldPreserveLinks() {
        String html = "<p>See <a href=\"/hc/en-us/articles/123\">this article</a>.</p>";
        String md = converter.convert(html);

        assertThat(md).contains("[this article](/hc/en-us/articles/123)");
    }

    @Test
    void shouldHandleEmptyInput() {
        assertThat(converter.convert(null)).isEmpty();
        assertThat(converter.convert("")).isEmpty();
    }
}
