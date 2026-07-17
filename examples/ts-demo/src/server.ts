/** Serveur HTTP express factice — points d'entrée pour CodeAtlas. */

import express from 'express';

import { CatalogService } from './services/catalog';

const app = express();

app.get('/products', (_req, res) => {
  res.json([]);
});

app.post('/products', (_req, res) => {
  res.json({ created: true });
});

app.listen(3000);
