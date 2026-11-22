# Radar da Manu

Painel editorial de ofertas e oscilação de preços (6 meses), com persistência local no navegador (`localStorage`) e script auxiliar para atualização de fotos e preços.

## Estrutura
- `index.html` — Página principal pronta para GitHub Pages / Netlify / Vercel
- `radar-da-manu-logo.png` — Logo com fundo transparente
- `img/produtos/` — Fotos locais dos produtos
- `servidor_radar.py` — Servidor local opcional para o botão **Atualizar Preços & Fotos**

## Uso local (opcional)
```powershell
python servidor_radar.py
```
Depois abra `http://localhost:8765/index.html`.
