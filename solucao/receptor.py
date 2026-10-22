#!/usr/bin/env python3
"""Receptor do webhook do formulário.  Uso: WEBHOOK_SECRET=... python receptor.py [--porta 8000]
Responde rápido (o remetente desiste em 5 s): grava e deixa o envio ao CRM para o sincronizar_crm.py.
  200  recebido (reenvio do mesmo event_id não duplica)
  401  assinatura inválida  -> NÃO vira pedido; vai para a quarentena (alguém confere com o marketing)
  400  corpo ilegível/sem campos mínimos -> idem, quarentena
  500  falha nossa -> o remetente reenvia"""
import argparse
import hashlib
import hmac
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import comum
import triagem

SEGREDO = comum.exigir("WEBHOOK_SECRET").encode()
MINIMOS = ("event_id", "criado_em", "email")          # telefone/restaurante/mensagem faltando NÃO derruba o pedido
ISO_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
trava = threading.Lock()


def quarentena(motivo, raw, ev=None):
    ev = ev if isinstance(ev, dict) else {}
    with trava, comum.conectar() as c:
        c.execute("INSERT INTO quarentena(recebido_em,motivo,event_id,nome,email,corpo) VALUES(?,?,?,?,?,?)",
                  (comum.agora_utc(), motivo, ev.get("event_id"), ev.get("nome"), ev.get("email"), raw.decode("utf-8", "replace")))


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _resp(self, status, corpo):
        b = json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        if self.path != "/webhook":
            return self._resp(404, {"status": "erro"})
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        esperado = "sha256=" + hmac.new(SEGREDO, raw, hashlib.sha256).hexdigest()
        try:
            ev = json.loads(raw.decode("utf-8"))
        except ValueError:
            ev = None
        if not hmac.compare_digest(self.headers.get("X-Signature", ""), esperado):
            quarentena("assinatura_invalida", raw, ev)
            return self._resp(401, {"status": "erro", "erro": "assinatura_invalida"})
        if not isinstance(ev, dict):
            quarentena("corpo_ilegivel", raw)
            return self._resp(400, {"status": "erro", "erro": "corpo_ilegivel"})
        if any(not str(ev.get(k, "")).strip() for k in MINIMOS) or not ISO_UTC.fullmatch(str(ev["criado_em"])):
            quarentena("campos_minimos_faltando", raw, ev)
            return self._resp(400, {"status": "erro", "erro": "campos_minimos_faltando"})
        ev = {k: (triagem.corrigir_acentos(v).strip() if isinstance(v, str) else v) for k, v in ev.items()}
        try:
            with trava, comum.conectar() as c:
                cur = c.execute(
                    "INSERT OR IGNORE INTO pedidos_formulario(event_id,criado_em,nome,email,telefone,restaurante,mensagem,origem,recebido_em)"
                    " VALUES(?,?,?,?,?,?,?,?,?)",
                    (ev["event_id"], ev["criado_em"], ev.get("nome", ""), ev["email"], ev.get("telefone", ""), ev.get("restaurante", ""),
                     ev.get("mensagem", ""), ev.get("origem", "site"), comum.agora_utc()))
                cat, motivo = triagem.classificar(ev)
                c.execute("INSERT OR IGNORE INTO triagem(event_id,categoria,motivo,status_crm,atualizado_em) VALUES(?,?,?,?,?)",
                          (ev["event_id"], cat, motivo, "pendente" if cat == "venda" else "nao_enviar", comum.agora_utc()))
            self._resp(200, {"status": "ok", "duplicado": cur.rowcount == 0})
        except Exception as e:                       # falha nossa: 5xx para o remetente tentar de novo
            self._resp(500, {"status": "erro", "erro": type(e).__name__})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, default=8000)
    a = ap.parse_args()
    with comum.conectar() as c:
        comum.preparar(c)
    print(f"Receptor em http://127.0.0.1:{a.porta}/webhook (banco: {comum.DB})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.porta), H).serve_forever()
