package com.gahoccode.ingestor.client;

import com.gahoccode.ingestor.config.IngestorProperties;
import com.gahoccode.ingestor.model.ZendeskArticle;
import com.gahoccode.ingestor.model.ZendeskArticlesPage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.ArrayList;
import java.util.List;

@Component
public class ZendeskClient {

    private static final Logger log = LoggerFactory.getLogger(ZendeskClient.class);

    private final RestClient restClient;
    private final IngestorProperties properties;

    public ZendeskClient(IngestorProperties properties) {
        this.properties = properties;
        this.restClient = RestClient.create();
    }

    /**
     * Lấy toàn bộ article (đã publish, không phải draft) bằng cách
     * lặp qua các trang Zendesk trả về cho tới khi hết next_page.
     */
    public List<ZendeskArticle> fetchAllArticles() {
        List<ZendeskArticle> result = new ArrayList<>();

        String url = properties.getZendesk().getBaseUrl()
                + "/" + properties.getZendesk().getLocale()
                + "/articles.json?per_page=" + properties.getZendesk().getPerPage();

        int pageNumber = 1;

        while (url != null) {
            log.info("Fetching page {} -> {}", pageNumber, url);

            ZendeskArticlesPage page = restClient.get()
                    .uri(url)
                    .retrieve()
                    .body(ZendeskArticlesPage.class);

            if (page == null || page.getArticles() == null) {
                log.warn("Empty response at page {}, stopping.", pageNumber);
                break;
            }

            List<ZendeskArticle> published = page.getArticles().stream()
                    .filter(a -> !a.isDraft())
                    .toList();

            result.addAll(published);
            log.info("Page {} returned {} articles ({} published)",
                    pageNumber, page.getArticles().size(), published.size());

            url = page.getNextPage();
            pageNumber++;
        }

        log.info("Total published articles fetched: {}", result.size());
        return result;
    }
}