package com.gahoccode.ingestor.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ZendeskArticlesPage {

    private List<ZendeskArticle> articles;

    @JsonProperty("next_page")
    private String nextPage;

    private int count;

    public List<ZendeskArticle> getArticles() {
        return articles;
    }

    public void setArticles(List<ZendeskArticle> articles) {
        this.articles = articles;
    }

    public String getNextPage() {
        return nextPage;
    }

    public void setNextPage(String nextPage) {
        this.nextPage = nextPage;
    }

    public int getCount() {
        return count;
    }

    public void setCount(int count) {
        this.count = count;
    }
}
