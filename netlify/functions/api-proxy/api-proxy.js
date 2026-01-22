const https = require('https');

const API_BASE_URL = 'chat-rank-api.amionai.com';
const API_KEY = process.env.API_KEY;

exports.handler = async (event) => {
  // Handle CORS preflight
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      },
      body: ''
    };
  }

  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers: { 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  // Extract endpoint from rawUrl or path
  // rawUrl contains the original request URL before redirect
  let originalPath = event.path;
  if (event.rawUrl) {
    const url = new URL(event.rawUrl);
    originalPath = url.pathname;
  }
  
  // Convert /api/get-by-id/ -> /tables/get-by-id/
  const pathParts = originalPath.replace('/api/', '').replace(/\/$/, '');
  const endpoint = `/tables/${pathParts}/`;
  
  console.log('Original path:', originalPath);
  console.log('Endpoint:', endpoint);

  return new Promise((resolve) => {
    const options = {
      hostname: API_BASE_URL,
      port: 443,
      path: endpoint,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
          },
          body: data
        });
      });
    });

    req.on('error', (error) => {
      resolve({
        statusCode: 500,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ error: error.message })
      });
    });

    req.write(event.body || '{}');
    req.end();
  });
};
