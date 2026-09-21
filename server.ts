import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer as createViteServer } from 'vite';
import dotenv from 'dotenv';

import { ARGO_FLOATS, ALL_PROFILES } from './server/argoData.ts';
import { runFloatForecast } from './server/forecaster.ts';
import { generateScientificResponse } from './server/geminiService.ts';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // API Routes
  // 1. Health check
  app.get('/api/health', (req, res) => {
    res.json({
      status: 'ok',
      service: 'FloatChat-XRAG-Forecasting-Engine',
      region: 'Arabian Sea / Northern Indian Ocean',
      version: '1.2.0-IEEE-Access-Spec'
    });
  });

  // 2. Available floats list
  app.get('/api/floats', (req, res) => {
    const list = ARGO_FLOATS.map(f => ({
      wmo_id: f.wmo_id,
      name: f.name,
      baseLat: f.baseLat,
      baseLon: f.baseLon,
      cycles: f.cycles,
      defaultCycle: f.cycles[f.cycles.length - 2]
    }));
    res.json(list);
  });

  // 3. Float profiles
  app.get('/api/profiles/:wmoId', (req, res) => {
    const { wmoId } = req.params;
    const profiles = [];
    for (const [key, profile] of ALL_PROFILES) {
      if (key.startsWith(`${wmoId}_`)) {
        profiles.push(profile);
      }
    }
    profiles.sort((a, b) => a.cycle_number - b.cycle_number);
    res.json(profiles);
  });

  // 4. Run Forecast with UQ, XAI attribution, and Evidence Links
  app.post('/api/forecast', (req, res) => {
    try {
      const { wmoId, cycle } = req.body;
      const targetWmo = wmoId || '3902114';
      const targetCycle = Number(cycle) || 92;

      const result = runFloatForecast(targetWmo, targetCycle);
      res.json(result);
    } catch (err: any) {
      console.error('Forecast calculation error:', err);
      res.status(500).json({ error: err.message || 'Forecast generation failed' });
    }
  });

  // 5. Conversational RAG & Anti-Hallucination Guardrail endpoint
  app.post('/api/chat', async (req, res) => {
    try {
      const { query, wmoId, cycle } = req.body;
      if (!query) {
        return res.status(400).json({ error: 'Query is required' });
      }

      const targetWmo = wmoId || '3902114';
      const targetCycle = Number(cycle) || 92;
      const forecast = runFloatForecast(targetWmo, targetCycle);

      const response = await generateScientificResponse(query, forecast);
      res.json({
        ...response,
        forecast_context: forecast
      });
    } catch (err: any) {
      console.error('Chat processing error:', err);
      res.status(500).json({ error: err.message || 'Error processing scientific dialogue' });
    }
  });

  // Vite middleware for development vs static serve for production
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`FloatChat X-RAG server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
