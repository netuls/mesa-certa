#!/usr/bin/env python3
"""Carrega o lote do webhook (lote-webhook.jsonl) no banco, sem precisar subir o receptor nem rodar o enviar-lote.

Aplica as mesmas regras do receptor.py: confere a assinatura, joga o que está errado na quarentena,
não duplica o mesmo event_id e classifica cada pedido (venda, teste, suporte...). Pode rodar quantas vezes quiser:
rodar de novo não repete nada.

Uso:  WEBHOOK_SECRET=... python importar_lote.py [caminho/do/lote-webhook.jsonl]
"""
import hashlib
import hmac
import json
import os
import re
import shutil
import sys
from pathlib import Path

import comum
import triagem

AQUI = Path(__file__).resolve().parent
ONDE = [AQUI / "lote-webhook.jsonl", AQUI / "webhook" / "lote-webhook.jsonl", AQUI.parent / "webhook" / "lote-webhook.jsonl",
         AQUI.parent / "ambiente-teste" / "webhook" / "lote-webhook.jsonl"]
MINIMOS = ("event_id", "criado_em", "email")
ISO_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def achar_lote():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    return next((p for p in ONDE if p.exists()), None)


def main():
    lote = achar_lote()
    if not lote or not lote.exists():
        print("Lote não encontrado. Coloque o lote-webhook.jsonl na pasta do painel. O painel abre mesmo assim.")
        return 0
    # Com segredo: confere cada assinatura (como o receptor). Sem segredo (painel local): nao da para conferir;
    # ficam de fora so as assinaturas ja conhecidas como invalidas (lote-assinaturas-invalidas.txt).
    segredo = os.environ.get("WEBHOOK_SECRET", "").encode()
    conhecidas = set()
    if not segredo:
        arq = AQUI / "lote-assinaturas-invalidas.txt"
        conhecidas = {l.strip() for l in arq.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")} if arq.exists() else set()
        print("Modo painel: sem WEBHOOK_SECRET, as assinaturas nao sao conferidas; as %d ja conhecidas como invalidas ficam de fora." % len(conhecidas))
    banco = Path(comum.DB)
    copia = banco.with_name(banco.stem + ".original.db")
    if banco.exists() and not copia.exists():
        shutil.copy2(banco, copia)                      # guarda o banco como veio, só na primeira vez
        print(f"Cópia do banco original criada: {copia.name}")

    novos = repetidos = quarentena = 0
    with comum.conectar() as c:
        comum.preparar(c)
        for linha in lote.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            try:
                env = json.loads(linha)
                raw = env["corpo"].encode("utf-8")
                assinatura = env.get("assinatura", "")
            except (ValueError, KeyError):
                quarentena += 1
                continue
            esperado = "sha256=" + hmac.new(segredo, raw, hashlib.sha256).hexdigest()
            try:
                ev = json.loads(raw.decode("utf-8"))
            except ValueError:
                ev = None
            motivo = None
            invalida = (assinatura in conhecidas) if not segredo else not hmac.compare_digest(assinatura, esperado)
            if invalida:
                motivo = "assinatura_invalida"
            elif not isinstance(ev, dict):
                motivo = "corpo_ilegivel"
            elif any(not str(ev.get(k, "")).strip() for k in MINIMOS) or not ISO_UTC.fullmatch(str(ev["criado_em"])):
                motivo = "campos_minimos_faltando"
            if motivo:
                ja = c.execute("SELECT 1 FROM quarentena WHERE corpo=? AND motivo=?", (raw.decode("utf-8", "replace"), motivo)).fetchone()
                if not ja:                              # rodar de novo não duplica a quarentena
                    d = ev if isinstance(ev, dict) else {}
                    c.execute("INSERT INTO quarentena(recebido_em,motivo,event_id,nome,email,corpo) VALUES(?,?,?,?,?,?)",
                              (comum.agora_utc(), motivo, d.get("event_id"), d.get("nome"), d.get("email"), raw.decode("utf-8", "replace")))
                quarentena += 1
                continue
            ev = {k: (triagem.corrigir_acentos(v).strip() if isinstance(v, str) else v) for k, v in ev.items()}
            cur = c.execute(
                "INSERT OR IGNORE INTO pedidos_formulario(event_id,criado_em,nome,email,telefone,restaurante,mensagem,origem,recebido_em)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (ev["event_id"], ev["criado_em"], ev.get("nome", ""), ev["email"], ev.get("telefone", ""), ev.get("restaurante", ""),
                 ev.get("mensagem", ""), ev.get("origem", "site"), comum.agora_utc()))
            if cur.rowcount == 0:
                repetidos += 1
                continue
            novos += 1
            cat, mot = triagem.classificar(ev)
            c.execute("INSERT OR IGNORE INTO triagem(event_id,categoria,motivo,status_crm,atualizado_em) VALUES(?,?,?,?,?)",
                      (ev["event_id"], cat, mot, "pendente" if cat == "venda" else "nao_enviar", comum.agora_utc()))
    print(f"Lote carregado: {novos} pedidos novos, {repetidos} repetidos ignorados, {quarentena} na quarentena.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
