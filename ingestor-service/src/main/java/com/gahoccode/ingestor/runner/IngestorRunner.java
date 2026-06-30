package com.gahoccode.ingestor.runner;

import com.gahoccode.ingestor.client.ZendeskClient;
import com.gahoccode.ingestor.model.ZendeskArticle;
import com.gahoccode.ingestor.service.FileWriterService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class IngestorRunner implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(IngestorRunner.class);

    private final ZendeskClient zendeskClient;
    private final FileWriterService fileWriterService;

    public IngestorRunner(ZendeskClient zendeskClient, FileWriterService fileWriterService) {
        this.zendeskClient = zendeskClient;
        this.fileWriterService = fileWriterService;
    }

    @Override
    public void run(String... args) {
        log.info("=== Starting OptiSigns article ingestion ===");

        List<ZendeskArticle> articles = zendeskClient.fetchAllArticles();
        log.info("Fetched {} articles from Zendesk", articles.size());

        int success = 0;
        int failed = 0;

        for (ZendeskArticle article : articles) {
            try {
                fileWriterService.writeArticle(article);
                success++;
            } catch (Exception e) {
                log.error("Failed to write article id={} title={}", article.getId(), article.getTitle(), e);
                failed++;
            }
        }

        log.info("=== Ingestion complete: {} written, {} failed, {} total ===",
                success, failed, articles.size());
    }
}