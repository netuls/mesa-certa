#!/usr/bin/env python3
"""Simula o formulário da Mesa Certa entregando eventos ao seu receptor de webhook.

Uso:  python enviar-lote.py --url http://127.0.0.1:8000/webhook
Opções: --ritmo 0.02 (segundos entre entregas)   --limite 50 (só as primeiras N entregas)
Leia README.md antes.
"""
import argparse
import json
import socket
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ESPERAS = [0.5, 1.0, 2.0]          # em produção seria bem mais devagar; aqui é curto para o teste andar


def entregar(url, corpo, assinatura, tentativa, timeout):
    req = urllib.request.Request(
        url, data=corpo.encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "X-Signature": assinatura,
                 "X-Delivery-Attempt": str(tentativa)})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000/webhook")   # 127.0.0.1: "localhost" demora no Windows (tenta IPv6 antes)
    ap.add_argument("--ritmo", type=float, default=0.02)
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=5.0)
    a = ap.parse_args()

    linhas = [json.loads(l) for l in (AQUI / "lote-webhook.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.limite:
        linhas = linhas[: a.limite]
    resumo = Counter()
    with open(AQUI / "envios.log", "a", encoding="utf-8") as log:
        for i, l in enumerate(linhas, start=1):
            final = None
            for tentativa in range(1, 5):
                st = entregar(a.url, l["corpo"], l["assinatura"], tentativa, a.timeout)
                log.write(f"{time.strftime('%H:%M:%S')} entrega={i} tentativa={tentativa} status={st}\n")
                if st is not None and 200 <= st < 300:
                    final = "aceita"
                    break
                if st is not None and 400 <= st < 500:
                    final = "recusada_4xx"      # erro do lado do receptor/da mensagem: não reenvia
                    break
                if tentativa < 4:
                    time.sleep(ESPERAS[tentativa - 1])
            resumo[final or "desistiu_apos_retentativas"] += 1
            time.sleep(a.ritmo)
    print(f"{len(linhas)} entregas processadas:", dict(resumo))


if __name__ == "__main__":
    main()
