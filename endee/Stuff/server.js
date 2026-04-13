const express = require('express');
const cors = require('cors');
const axios = require('axios');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Middleware
app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.use(express.static('public'));

// ============================================================================
// Proxy Endpoints — Forward requests to the FastAPI backend
// ============================================================================

/**
 * POST /api/query — Send a query to the LangChain agent.
 * The backend retrieves memories from Endee, runs the agent,
 * and optionally stores a new memory.
 */
app.post('/api/query', async (req, res) => {
  try {
    const { query, domain = 'general', context } = req.body;

    if (!query || query.trim().length === 0) {
      return res.status(400).json({ error: 'Query cannot be empty' });
    }

    const response = await axios.post(`${BACKEND_URL}/query`, {
      query,
      domain,
      context
    }, { timeout: 120000 }); // 2 min timeout for LLM processing

    res.json(response.data);
  } catch (error) {
    console.error('Backend error:', error.message);
    res.status(error.response?.status || 500).json({
      error: 'Failed to process query',
      details: error.response?.data?.detail || error.message
    });
  }
});

/**
 * GET /api/memories — List stored memories from Endee.
 * Optional query params: domain, limit
 */
app.get('/api/memories', async (req, res) => {
  try {
    const { domain, limit = 10 } = req.query;

    const response = await axios.get(`${BACKEND_URL}/memories`, {
      params: { domain, limit }
    });

    res.json(response.data);
  } catch (error) {
    console.error('Backend error:', error.message);
    res.status(error.response?.status || 500).json({
      error: 'Failed to fetch memories',
      details: error.response?.data?.detail || error.message
    });
  }
});

/**
 * DELETE /api/memories/:memoryId — Delete a specific memory.
 */
app.delete('/api/memories/:memoryId', async (req, res) => {
  try {
    const { memoryId } = req.params;
    const response = await axios.delete(`${BACKEND_URL}/memories/${memoryId}`);
    res.json(response.data);
  } catch (error) {
    console.error('Backend error:', error.message);
    res.status(error.response?.status || 500).json({
      error: 'Failed to delete memory',
      details: error.response?.data?.detail || error.message
    });
  }
});

/**
 * GET /api/health — Health check proxy to the backend.
 */
app.get('/api/health', async (req, res) => {
  try {
    const response = await axios.get(`${BACKEND_URL}/health`, { timeout: 5000 });
    res.json(response.data);
  } catch (error) {
    res.status(503).json({
      status: 'error',
      message: 'Backend unreachable',
      backend_url: BACKEND_URL
    });
  }
});

// ============================================================================
// Static Files — Serve the frontend UI
// ============================================================================

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// ============================================================================
// Global Error Handler
// ============================================================================

app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// ============================================================================
// Start Server with Graceful Shutdown
// ============================================================================

const server = app.listen(PORT, () => {
  console.log(`✓ Frontend running on http://localhost:${PORT}`);
  console.log(`  Backend: ${BACKEND_URL}`);
  console.log(`  Serving: ./public/index.html`);
});

// Graceful shutdown on SIGINT / SIGTERM
function shutdown(signal) {
  console.log(`\n${signal} received — shutting down gracefully...`);
  server.close(() => {
    console.log('✓ Server closed');
    process.exit(0);
  });
  // Force close after 5s
  setTimeout(() => {
    console.error('Forcing shutdown after timeout');
    process.exit(1);
  }, 5000);
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));