const fs = require('fs');

async function applyConfig() {
  const configPath = '/home/node/.openclaw/openclaw.json';
  const rawConfig = fs.readFileSync(configPath, 'utf8');
  const config = JSON.parse(rawConfig);
  
  const token = config.gateway.auth.token;
  const port = config.gateway.port;
  
  console.log(`Applying config to Gateway on port ${port}...`);
  
  try {
    const response = await fetch(`http://127.0.0.1:${port}/gateway/config/apply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        raw: rawConfig,
        note: "Force apply Ollama config via API"
      })
    });
    
    const result = await response.json();
    console.log('Response:', JSON.stringify(result, null, 2));
  } catch (err) {
    console.error('Error applying config:', err);
  }
}

applyConfig();
