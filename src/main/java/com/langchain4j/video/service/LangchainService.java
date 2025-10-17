package com.langchain4j.video.service;

import org.springframework.stereotype.Service;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
@Service
public class LangchainService {

     private final OpenAiChatModel model;

    public LangchainService(
            @Value("${groq.api.key}") String apiKey,
            @Value("${groq.model:llama-3.1-8b-instant}") String modelName
    ) {
        this.model = OpenAiChatModel.builder()
                .apiKey(apiKey)
                .baseUrl("https://api.groq.com/openai/v1")
                .modelName(modelName)
                .build();
    }

    public String explainMath(String question, String teacherName) {
        String prompt = String.format(
                "Explique cet exercice de math comme le ferait le professeur %s : %s",
                teacherName, question
        );
        try {
            return model.generate(prompt);
        } catch (RuntimeException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "LLM error: " + ex.getMessage(), ex);
        }
    }
    
}
