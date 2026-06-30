package com.gahoccode.ingestor.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.NestedConfigurationProperty;

@ConfigurationProperties(prefix = "ingestor")
public class IngestorProperties {

    @NestedConfigurationProperty
    private Zendesk zendesk = new Zendesk();

    @NestedConfigurationProperty
    private Output output = new Output();

    private int minArticles = 30;

    public Zendesk getZendesk() {
        return zendesk;
    }

    public void setZendesk(Zendesk zendesk) {
        this.zendesk = zendesk;
    }

    public Output getOutput() {
        return output;
    }

    public void setOutput(Output output) {
        this.output = output;
    }

    public int getMinArticles() {
        return minArticles;
    }

    public void setMinArticles(int minArticles) {
        this.minArticles = minArticles;
    }

    public static class Zendesk {
        private String baseUrl;
        private String locale = "en-us";
        private int perPage = 100;

        public String getBaseUrl() {
            return baseUrl;
        }

        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }

        public String getLocale() {
            return locale;
        }

        public void setLocale(String locale) {
            this.locale = locale;
        }

        public int getPerPage() {
            return perPage;
        }

        public void setPerPage(int perPage) {
            this.perPage = perPage;
        }
    }

    public static class Output {
        private String dir = "./articles";

        public String getDir() {
            return dir;
        }

        public void setDir(String dir) {
            this.dir = dir;
        }
    }
}