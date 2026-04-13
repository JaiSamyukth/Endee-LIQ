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
 * POST /api/query
 * Send a query to the LangChain agent.
 * Backend retrieves memories from Endee, runs the agent, and optionally
 * stores a new memory before returning the full response.
 */
app.post('/api/query', async (req, res) => {
  try {
    const { query, context } = req.body;

    if (!query || query.trim().length === 0) {
      return res.status(400).json({ error: 'Query cannot be empty' });
    }

    const response = await axios.post(
      `${BACKEND_URL}/query`,
      { query, context },
      { timeout: 120000 }   // 2-min timeout — LLM can be slow on CPU
    );

    res.json(response.data);
  } catch (error) {
    console.error('Backend query error:', error.message);
    res.status(error.response?.status || 500).json({
      error:   'Failed to process query',
      details: error.response?.data?.detail || error.message,
    });
  }
});

/**
 * GET /api/memories
 * List stored memories from Endee.
 * Query params: domain (optional), limit (default 10)
 */
app.get('/api/memories', async (req, res) => {
  try {
    const { domain, limit = 10 } = req.query;
    const response = await axios.get(`${BACKEND_URL}/memories`, {
      params: { domain, limit },
    });
    res.json(response.data);
  } catch (error) {
    console.error('Backend memories error:', error.message);
    res.status(error.response?.status || 500).json({
      error:   'Failed to fetch memories',
      details: error.response?.data?.detail || error.message,
    });
  }
});

/**
 * GET /api/notifications/poll
 * Poll the backend for elapsed active reminders
 */
app.get('/api/notifications/poll', async (req, res) => {
  try {
    const response = await axios.get(`${BACKEND_URL}/notifications/poll`, { timeout: 5000 });
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ notifications: [] });
  }
});

/**
 * GET /api/health
 * Health-check proxy — passes through backend status.
 */
app.get('/api/health', async (req, res) => {
  try {
    const response = await axios.get(`${BACKEND_URL}/health`, { timeout: 5000 });
    res.json(response.data);
  } catch (error) {
    res.status(503).json({
      status:      'error',
      message:     'Backend unreachable',
      backend_url: BACKEND_URL,
    });
  }
});

// ============================================================================
// Serve Frontend
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
  console.log(`  ↳ Backend: ${BACKEND_URL}`);
  console.log(`  ↳ Serving: ./public/index.html`);
});

function shutdown(signal) {
  console.log(`\n${signal} received — shutting down gracefully...`);
  server.close(() => {
    console.log('✓ Server closed');
    process.exit(0);
  });
  setTimeout(() => {
    console.error('Forcing shutdown after timeout');
    process.exit(1);
  }, 5000);
}

process.on('SIGINT',  () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
