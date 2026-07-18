# Quickstart: valider le pont IA

## Validation P1 — Carte du dépôt

```bash
codeatlas export examples/python-demo | head -30      # carte : vue d'ensemble, entrées, parcours, API
codeatlas export examples/python-demo --budget 2600 | tail -3   # section « Omis (budget) »
codeatlas export examples/python-demo --format graph | head -5  # IR JSON canonique
codeatlas export examples/python-demo > a.md && codeatlas export examples/python-demo > b.md && diff a.md b.md
```

## Validation P2 — Analyse d'impact

```bash
codeatlas impact examples/python-demo --focus InMemoryRepo.find --depth 2
# attendu : niveau 1 = place/price_of ; niveau 2 = main (+ refresh incertain) ;
# points d'entrée atteints listés
```

## Validation P2 — Serveur MCP

```bash
pip install "codeatlas-doc[mcp]"
codeatlas mcp examples/python-demo     # serveur stdio — à brancher dans un assistant
# Claude Code (.mcp.json) :
# { "mcpServers": { "codeatlas": { "command": "codeatlas", "args": ["mcp", "."] } } }
pytest tests/integration/test_mcp_server.py tests/unit/test_mcp_tools.py
```

## Validation P3 — Parcours de lecture

```bash
codeatlas build examples/layered-demo --out /tmp/atlas-tour --no-site
sed -n '1,12p' /tmp/atlas-tour/docs/tour.md
# attendu : webshop.api.routes (point d'entrée) puis domain puis infra
```
