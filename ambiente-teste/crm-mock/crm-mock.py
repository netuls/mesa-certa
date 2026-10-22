#!/usr/bin/env python3
"""CRM de mentira da Mesa Certa (porta 8001). Documentação em README.md.

Uso:  python crm-mock.py            (continua de onde parou)
      python crm-mock.py --reset    (volta ao estado inicial de crm-seed.json)
"""
import argparse
import datetime as dt
import json
import random
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

AQUI = Path(__file__).resolve().parent
SEED = AQUI / "crm-seed.json"
ESTADO = AQUI / "crm-mock-estado.json"
TOKEN = os.environ.get("CRM_TOKEN", "local-mock-only")

lock = threading.Lock()
rng = random.Random(7)
deals = {}
janela = []          # instantes das últimas requisições (limite de taxa)


def carregar(reset):
    if not reset and ESTADO.exists():
        dados = json.loads(ESTADO.read_text(encoding="utf-8"))
    else:
        dados = json.loads(SEED.read_text(encoding="utf-8"))
    for d in dados:
        deals[d["deal_id"]] = d


def salvar():
    ESTADO.write_text(json.dumps(list(deals.values()), ensure_ascii=False), encoding="utf-8")


def norm(email):
    return (email or "").strip().lower()


def agora_brt():
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *a):
        print(f"[crm] {self.command} {self.path} -> {getattr(self, '_st', '?')}", flush=True)

    def _json(self, status, corpo, extra=None):
        self._st = status
        b = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(b)
        except (ConnectionError, TimeoutError):
            pass                                  # o cliente desistiu antes da resposta

    def _corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return None

    def _porteiro(self):
        """Autenticação, limite de taxa e instabilidade. Devolve 'ok', 'gravou_e_500' ou None (já respondeu)."""
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self._json(401, {"status": "erro", "erro": "nao_autorizado"})
            return None
        with lock:
            agora = time.time()
            janela[:] = [t for t in janela if agora - t < 1.0]
            janela.append(agora)
            excedeu = len(janela) > 5
            r = rng.random()
        if excedeu:
            self._json(429, {"status": "erro", "erro": "muitas_requisicoes"}, {"Retry-After": "1"})
            return None
        if r < 0.10:
            return "500"
        if r < 0.16:
            time.sleep(8)
            return "ok"
        if r < 0.24:
            self._json(200, {"status": "erro", "mensagem": "fila ocupada, tente novamente"})
            return None
        return "ok"

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/estado":
            por = {}
            for d in deals.values():
                por[d["etapa"]] = por.get(d["etapa"], 0) + 1
            return self._json(200, {"total": len(deals), "por_etapa": por})
        modo = self._porteiro()
        if modo is None:
            return
        if modo == "500":
            return self._json(500, {"status": "erro", "erro": "erro_interno"})
        q = parse_qs(u.query)
        m = re.fullmatch(r"/deals/(\d+)", u.path)
        if m:
            d = deals.get(int(m.group(1)))
            return self._json(200, {"status": "ok", "data": d}) if d else self._json(404, {"status": "erro", "erro": "nao_encontrado"})
        if u.path == "/deals":
            itens = list(deals.values())
            if "email" in q:
                alvo = norm(q["email"][0])
                itens = [d for d in itens if norm(d["email"]) == alvo]
            page = max(1, int(q.get("page", ["1"])[0]))
            per = min(50, max(1, int(q.get("per_page", ["20"])[0])))
            ini = (page - 1) * per
            fim = ini + per
            return self._json(200, {"status": "ok", "data": itens[ini:fim], "page": page, "per_page": per,
                                    "total": len(itens), "next_page": page + 1 if fim < len(itens) else None})
        self._json(404, {"status": "erro", "erro": "rota_inexistente"})

    def do_POST(self):
        if urlparse(self.path).path != "/deals":
            return self._json(404, {"status": "erro", "erro": "rota_inexistente"})
        modo = self._porteiro()
        if modo is None:
            return
        corpo = self._corpo()
        if corpo is None:
            return self._json(400, {"status": "erro", "erro": "json_invalido"})
        faltando = [k for k in ("nome", "email", "telefone") if not str(corpo.get(k, "")).strip()]
        if faltando:
            return self._json(422, {"status": "erro", "erro": "campos_obrigatorios", "faltando": faltando})
        with lock:
            existente = next((d for d in deals.values() if norm(d["email"]) == norm(corpo["email"])), None)
            if existente:
                return self._json(409, {"status": "erro", "erro": "email_ja_cadastrado", "deal_id": existente["deal_id"]})
            grava = modo == "ok" or rng.random() < 0.5      # 500 às vezes grava mesmo assim
            if grava:
                novo_id = max(deals) + 1
                agora = agora_brt()
                deals[novo_id] = {"deal_id": novo_id, "nome": corpo["nome"], "email": corpo["email"],
                                  "telefone": corpo["telefone"], "restaurante": corpo.get("restaurante", ""),
                                  "etapa": "Novo", "origem": corpo.get("origem", "Site"),
                                  "criado_em": agora, "atualizado_em": agora}
                salvar()
        if modo == "500":
            return self._json(500, {"status": "erro", "erro": "erro_interno"})
        self._json(201, {"status": "ok", "deal_id": novo_id})

    def do_PATCH(self):
        m = re.fullmatch(r"/deals/(\d+)", urlparse(self.path).path)
        if not m:
            return self._json(404, {"status": "erro", "erro": "rota_inexistente"})
        modo = self._porteiro()
        if modo is None:
            return
        if modo == "500":
            return self._json(500, {"status": "erro", "erro": "erro_interno"})
        corpo = self._corpo() or {}
        with lock:
            d = deals.get(int(m.group(1)))
            if not d:
                return self._json(404, {"status": "erro", "erro": "nao_encontrado"})
            if "etapa" in corpo:
                if corpo["etapa"] not in ("Novo", "Contato", "Reunião marcada", "Reunião realizada", "Perdido"):
                    return self._json(422, {"status": "erro", "erro": "etapa_invalida"})
                d["etapa"] = corpo["etapa"]
                d["atualizado_em"] = agora_brt()
                salvar()
        self._json(200, {"status": "ok", "data": d})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--porta", type=int, default=8001)
    a = ap.parse_args()
    carregar(a.reset)
    print(f"CRM mock no ar em http://localhost:{a.porta} com {len(deals)} negócios", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.porta), H).serve_forever()
