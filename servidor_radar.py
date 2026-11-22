#!/usr/bin/env python3
"""
Servidor local e baixador de fotos/preÃ§os para o Radar da Manu.

Uso:
  1) Baixar todas as fotos dos 19 produtos agora (para upload do site):
       python servidor_radar.py --baixar-fotos

  2) Rodar o servidor local (para o botÃ£o "Atualizar PreÃ§os & Fotos" no HTML):
       python servidor_radar.py
     Depois abra: http://localhost:8765/index.html
"""

import http.server
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR
IMG_DIR = PUBLIC_DIR / "img" / "produtos"
PORT = 8765

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

DEFAULT_QUERIES = [
    (1, "Combo Apice Fitagem Gelatina Cachos Creme Nutri Waves"),
    (2, "Ativador Modelador Anti-Frizz Cachos Essence Apice 1L"),
    (3, "Gelatina Ativadora Nutritiva Apice Cachos Essence Coco e Chia 500ml"),
    (4, "Mascara Acidificante Amend Essencial 250g"),
    (5, "Po Compacto Translucido Boca Rosa Cuscuz"),
    (6, "Contorno Stick Niina Secrets Eudora Cor 3"),
    (7, "Bruma Facial Niina Secrets Nutri Fresh 110ml"),
    (8, "Bruma Facial Dailus Fix Tudo 150ml"),
    (9, "Blindagem Angel Magic Pri Lessa Catharine Hill 30ml"),
    (10, "Corretivo Liquido Ruby Kisses Under Eye Corrector 25"),
    (11, "Lip Balm Ruby Rose Blow Girls Night"),
    (12, "Gloss Labial Ruby Rose Blow The Glossier One"),
    (13, "Gloss Labial Boca Rosa Hidra Labios Bege"),
    (14, "Lapis Contorno Labial Boca Rosa Castanho Intenso"),
    (15, "Batom Liquido Quem Disse Berenice Marrom Marronli"),
    (16, "Sallve Super Acido Glicolico 10%"),
    (17, "Creamy Acido Glicolico 30g"),
    (18, "Tenis Olympikus Treino Feminino Azul Claro"),
    (19, "Tenis Under Armour Tribase Reps Feminino Azul"),
]


def fetch_ml_search(query: str):
    """Consulta a API pÃºblica do Mercado Livre Brasil."""
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(query)}&limit=5"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            results = data.get("results") or []
            if results:
                # Ordena pelo menor preÃ§o vÃ¡lido para referÃªncia
                valid = [r for r in results if r.get("price")]
                best = min(valid, key=lambda x: x["price"]) if valid else results[0]
                thumb = best.get("thumbnail", "")
                # Converte thumbnail de baixa resoluÃ§Ã£o (-I.jpg) para alta resoluÃ§Ã£o (-O.jpg)
                if thumb:
                    thumb = re.sub(r"-I\.jpg$", "-O.jpg", thumb.replace("http://", "https://"))
                return {
                    "price": float(best["price"]) if best.get("price") else None,
                    "store": "Mercado Livre",
                    "image_url": thumb,
                    "permalink": best.get("permalink"),
                }
    except Exception as e:
        print(f"  [ML API] aviso para '{query[:35]}': {e}")
    return None


def fetch_bing_image_candidates(query: str):
    """Retorna lista de URLs candidatas de imagem (murl + thumbnails confiÃ¡veis do Bing)."""
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query + ' produto')}&first=1"
    req = urllib.request.Request(url, headers=HEADERS)
    candidates = []
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            murls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png|webp))', html, re.IGNORECASE)
            thumbs = re.findall(r'(https://tse\d\.mm\.bing\.net/th\?id=OIP\.[^"&]+)', html)
            candidates.extend(murls[:3])
            candidates.extend(thumbs[:3])
    except Exception as e:
        print(f"  [Fallback Img] aviso para '{query[:35]}': {e}")
    return candidates


def download_image(image_url: str, dest_path: Path) -> bool:
    if not image_url:
        return False
    req = urllib.request.Request(image_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) < 1500:
                return False
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(data)
            return True
    except Exception as e:
        print(f"  [Download] erro {image_url[:50]}: {e}")
        return False


def update_single_product(item_id: int, query: str, skip_existing: bool = False):
    """Busca preÃ§o e baixa a foto localmente em public/img/produtos/produto-<id>.jpg."""
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMG_DIR / f"produto-{item_id}.jpg"
    rel_path = f"img/produtos/produto-{item_id}.jpg"

    if skip_existing and dest.exists() and dest.stat().st_size > 1500:
        return {"id": item_id, "image": rel_path, "price": None, "store": None, "downloaded": True}

    ml = fetch_ml_search(query)
    image_url = ml["image_url"] if ml and ml.get("image_url") else None
    price = ml["price"] if ml and ml.get("price") else None
    store = ml["store"] if ml and ml.get("store") else None

    ok_img = download_image(image_url, dest) if image_url else False
    if not ok_img:
        for cand in fetch_bing_image_candidates(query):
            if download_image(cand, dest):
                ok_img = True
                break

    return {
        "id": item_id,
        "image": rel_path if (ok_img or dest.exists()) else None,
        "price": price,
        "store": store,
        "downloaded": ok_img,
    }


def download_all_default_photos():
    print(f"Baixando fotos para {IMG_DIR} ...")
    skip = "--faltantes" in sys.argv
    ok_count = 0
    for item_id, query in DEFAULT_QUERIES:
        res = update_single_product(item_id, query, skip_existing=skip)
        status = "OK" if res["downloaded"] else "FALHOU"
        price_str = f"R$ {res['price']:.2f}" if res["price"] else "sem preÃ§o ML"
        print(f"  [{item_id:02d}] {status:6s} | {price_str:12s} | {query[:45]}")
        if res["downloaded"]:
            ok_count += 1
    print(f"\nConcluÃ­do: {ok_count}/{len(DEFAULT_QUERIES)} fotos salvas em {IMG_DIR}")


class RadarHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/atualizar":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                payload = {}

            items = payload.get("items") or []
            results = []
            for it in items:
                item_id = int(it.get("id", 0))
                query = str(it.get("query") or it.get("name") or "").strip()
                if item_id and query:
                    results.append(update_single_product(item_id, query))

            body = json.dumps({"ok": True, "results": results}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    if "--baixar-fotos" in sys.argv:
        download_all_default_photos()
    else:
        print(f"Servidor Radar da Manu rodando em: http://localhost:{PORT}/index.html")
        print("Pressione Ctrl+C para encerrar.")
        with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), RadarHandler) as httpd:
            httpd.serve_forever()

