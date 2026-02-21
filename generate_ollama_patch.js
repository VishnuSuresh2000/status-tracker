const fs = require('fs');

const ollamaResponse = {
  "models": [
    {"name":"deepseek-v3.1:671b-cloud","model":"deepseek-v3.1:671b-cloud"},
    {"name":"qwen3-coder-next:cloud","model":"qwen3-coder-next:cloud"},
    {"name":"phi4-mini:latest","model":"phi4-mini:latest"},
    {"name":"granite4:latest","model":"granite4:latest"},
    {"name":"ministral-3:3b","model":"ministral-3:3b"},
    {"name":"aikid123/qwen3-coder:latest","model":"aikid123/qwen3-coder:latest"},
    {"name":"ministral-3:8b","model":"ministral-3:8b"},
    {"name":"ishumilin/deepseek-r1-coder-tools:1.5b","model":"ishumilin/deepseek-r1-coder-tools:1.5b"},
    {"name":"MFDoom/deepseek-r1-tool-calling:1.5b","model":"MFDoom/deepseek-r1-tool-calling:1.5b"},
    {"name":"deepseek-r1:1.5b","model":"deepseek-r1:1.5b"},
    {"name":"qwen3:0.6b","model":"qwen3:0.6b"},
    {"name":"tinyllama:latest","model":"tinyllama:latest"},
    {"name":"smollm:1.7b","model":"smollm:1.7b"},
    {"name":"smollm:135m","model":"smollm:135m"},
    {"name":"hf.co/acon96/Home-Llama-3.2-3B:Q4_K_M","model":"hf.co/acon96/Home-Llama-3.2-3B:Q4_K_M"},
    {"name":"gemma2:2b","model":"gemma2:2b"},
    {"name":"qwen3:1.7b","model":"qwen3:1.7b"},
    {"name":"llama3.2:1b","model":"llama3.2:1b"},
    {"name":"llama3:8b-instruct-q4_k_m","model":"llama3:8b-instruct-q4_k_m"},
    {"name":"qwen2.5:3b","model":"qwen2.5:3b"}
  ]
};

const patch = {
  models: {
    providers: {
      ollama: {
        baseUrl: "http://192.168.0.136:11434",
        apiKey: "ollama-local",
        api: "ollama",
        models: []
      }
    }
  }
};

ollamaResponse.models.forEach(m => {
  const isReasoning = m.name.includes('deepseek-r1') || m.name.includes('reasoning');
  patch.models.providers.ollama.models.push({
    id: m.name,
    name: m.name,
    reasoning: isReasoning,
    input: ["text"],
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    contextWindow: 8192,
    maxTokens: 81920
  });
});

console.log(JSON.stringify(patch));
