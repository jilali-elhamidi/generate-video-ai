package com.langchain4j.video.controller;
import com.langchain4j.video.service.LangchainService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/math")
public class MathController {

    private final LangchainService langchainService;

    public MathController(LangchainService langchainService) {
        this.langchainService = langchainService;
    }

    @GetMapping(value = "/explain", produces = "text/markdown; charset=UTF-8")
    public String explain(
            @RequestParam String question,
            @RequestParam(defaultValue = "Ahmed") String prof
    ) {
        return langchainService.explainMath(question, prof);
    }
}