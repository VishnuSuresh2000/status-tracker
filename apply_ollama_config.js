const fs = require('fs');
const path = '/home/node/.openclaw/openclaw.json';

try {
  const config = JSON.parse(fs.readFileSync(path, 'utf8'));

  // Define the Ollama provider config with discovered models
  const ollamaConfig = {
    baseUrl: "http://192.168.0.136:11434",
    apiKey: "ollama-local",
    api: "ollama",
    models: [
      {
        "id": "deepseek-v3.1:671b-cloud",
        "name": "deepseek-v3.1:671b-cloud",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "qwen3-coder-next:cloud",
        "name": "qwen3-coder-next:cloud",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "phi4-mini:latest",
        "name": "phi4-mini:latest",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "granite4:latest",
        "name": "granite4:latest",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "ministral-3:3b",
        "name": "ministral-3:3b",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "aikid123/qwen3-coder:latest",
        "name": "aikid123/qwen3-coder:latest",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "ministral-3:8b",
        "name": "ministral-3:8b",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "ishumilin/deepseek-r1-coder-tools:1.5b",
        "name": "ishumilin/deepseek-r1-coder-tools:1.5b",
        "reasoning": true,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "MFDoom/deepseek-r1-tool-calling:1.5b",
        "name": "MFDoom/deepseek-r1-tool-calling:1.5b",
        "reasoning": true,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "deepseek-r1:1.5b",
        "name": "deepseek-r1:1.5b",
        "reasoning": true,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "qwen3:0.6b",
        "name": "qwen3:0.6b",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "tinyllama:latest",
        "name": "tinyllama:latest",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "smollm:1.7b",
        "name": "smollm:1.7b",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "smollm:135m",
        "name": "smollm:135m",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "hf.co/acon96/Home-Llama-3.2-3B:Q4_K_M",
        "name": "hf.co/acon96/Home-Llama-3.2-3B:Q4_K_M",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "gemma2:2b",
        "name": "gemma2:2b",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "qwen3:1.7b",
        "name": "qwen3:1.7b",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "llama3.2:1b",
        "name": "llama3.2:1b",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "llama3:8b-instruct-q4_k_m",
        "name": "llama3:8b-instruct-q4_k_m",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      },
      {
        "id": "qwen2.5:3b",
        "name": "qwen2.5:3b",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 8192,
        "maxTokens": 81920
      }
    ]
  };

  // Ensure structure exists
  if (!config.models) config.models = {};
  if (!config.models.providers) config.models.providers = {};

  // Apply the patch
  config.models.providers.ollama = ollamaConfig;

  // Write back
  fs.writeFileSync(path, JSON.stringify(config, null, 2));
  console.log('Successfully updated OpenClaw config with Ollama provider.');

} catch (err) {
  console.error('Error updating config:', err);
  process.exit(1);
}
