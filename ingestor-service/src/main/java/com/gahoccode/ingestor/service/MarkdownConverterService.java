package com.gahoccode.ingestor.service;

import com.vladsch.flexmark.html2md.converter.FlexmarkHtmlConverter;
import com.vladsch.flexmark.util.data.MutableDataSet;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.nodes.TextNode;
import org.springframework.stereotype.Service;

@Service
public class MarkdownConverterService {

    private final FlexmarkHtmlConverter converter;

    public MarkdownConverterService() {
        MutableDataSet options = new MutableDataSet();
        options.set(FlexmarkHtmlConverter.SETEXT_HEADINGS, false);
        this.converter = FlexmarkHtmlConverter.builder(options).build();
    }

    public String convert(String html) {
        if (html == null || html.isBlank()) {
            return "";
        }
        String cleanedHtml = cleanHtml(html);
        return converter.convert(cleanedHtml).trim();
    }

    private String cleanHtml(String rawHtml) {
        Document doc = Jsoup.parse(rawHtml);
        doc.outputSettings().prettyPrint(false);
        doc.select("script, style, iframe, nav, footer").remove();
        doc.select("img").remove();
        for (Element pre : doc.select("pre")) {
            String codeText = pre.text();
            String fenced = "\n```\n" + codeText + "\n```\n";
            pre.replaceWith(new TextNode(fenced));
        }

        return doc.body().html();
    }
}