package com.gahoccode.ingestor;

import com.gahoccode.ingestor.config.IngestorProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(IngestorProperties.class)
public class IngestorServiceApplication {

	public static void main(String[] args) {
		SpringApplication.run(IngestorServiceApplication.class, args);
	}

}
