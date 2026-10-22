#!/usr/bin/env python3
"""Leva ao CRM os pedidos de venda que ainda não estão lá.  Uso: CRM_TOKEN=... python sincronizar_crm.py
Pode rodar a qualquer hora e quantas vezes quiser. O CRM falha de propósito (500 que às vezes grava, 200 com erro,
429, demora de 8 s): nunca confiamos no código da resposta; depois de qualquer dúvida, olhamos o CRM de novo.
Status gravado em triagem.status_crm:
  criado           criamos o negócio agora
  ja_no_crm        já existia um negócio criado na mesma hora do pedido (a integração normal)
  repetido_no_crm  a pessoa já tinha negócio ANTIGO (o CRM recusa e-mail repetido): o pedido novo não abre negócio -> vai ao resumo
  erro_dados       o CRM recusou os dados (ex.: sem telefone) -> um humano precisa olhar
  pendente         o CRM não respondeu direito; tenta de novo na próxima rodada"""
import datetime as dt
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

import comum
import triagem
import triagem_ia

URL = os.environ.get("CRM_URL", "http://127.0.0.1:8001")
INTERVALO = 0.27            # ~4 chamadas por segundo (limite do CRM: 5)
TENTATIVAS = 10
JANELA_MIN = 15             # a integração cria o negócio em segundos; 15 min cobre duplo clique e relógio torto
_ultima = [0.0]


def token():
    return comum.exigir("CRM_TOKEN")


def chamar(metodo, caminho, corpo=None):
    espera = INTERVALO - (time.time() - _ultima[0])
    if espera > 0:
        time.sleep(espera)
    _ultima[0] = time.time()
    req = urllib.request.Request(
        URL + caminho, method=metodo, data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:        # maior que a demora de 8 s do CRM
            status, txt = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, txt = e.code, e.read()
        if status == 429:
            time.sleep(float(e.headers.get("Retry-After") or 1))
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError):
        return None, None
    try:
        return status, json.loads(txt)
    except ValueError:
        return status, None


def buscar(email):
    """Negócios com esse e-mail, ou None se o CRM não respondeu direito."""
    for _ in range(TENTATIVAS):
        st, js = chamar("GET", "/deals?per_page=50&email=" + urllib.parse.quote(email))
        if st == 200 and js and js.get("status") == "ok":
            return js["data"]
        time.sleep(0.5)
    return None


def do_pedido(deals, criado_utc):
    """Negócio criado na mesma hora do pedido (±JANELA_MIN), se houver."""
    alvo = dt.datetime.strptime(criado_utc, "%Y-%m-%dT%H:%M:%SZ") - dt.timedelta(hours=3)
    for d in deals:
        t = dt.datetime.strptime(d["criado_em"], "%Y-%m-%d %H:%M:%S")
        if abs((t - alvo).total_seconds()) <= JANELA_MIN * 60:
            return d
    return None


def processar(p):
    """Devolve (status, deal_id)."""
    postou = False
    for _ in range(TENTATIVAS):
        deals = buscar(p["email"].strip())
        if deals is None:
            return "pendente", None
        achou = do_pedido(deals, p["criado_em"])
        if achou:
            return ("criado" if postou else "ja_no_crm"), achou["deal_id"]
        if deals and not postou:                       # só há negócio ANTIGO: o CRM não aceita um segundo com o mesmo e-mail
            return "repetido_no_crm", deals[-1]["deal_id"]
        if deals and postou:                           # nosso POST gravou, mas aparece fora da janela: confere o mais novo
            return "criado", deals[-1]["deal_id"]
        postou = True
        st, js = chamar("POST", "/deals", {"nome": p["nome"], "email": p["email"].strip(), "telefone": p["telefone"],
                                           "restaurante": p["restaurante"] or "", "origem": "Site"})
        if st == 201 and js and js.get("status") == "ok":
            return "criado", js["deal_id"]
        if st == 409 and js:
            return "repetido_no_crm", js.get("deal_id")
        if st in (400, 422):
            return "erro_dados", None
        time.sleep(0.5)                                # 5xx, 429, timeout ou 200 com erro: incerto, confere de novo no giro
    return "pendente", None


def triar_pendentes(c):
    n = 0
    for r in c.execute("SELECT * FROM pedidos_formulario WHERE event_id NOT IN (SELECT event_id FROM triagem)").fetchall():
        cat, motivo = triagem.classificar(dict(r))
        c.execute("INSERT OR IGNORE INTO triagem(event_id,categoria,motivo,status_crm,atualizado_em) VALUES(?,?,?,?,?)",
                  (r["event_id"], cat, motivo, "pendente" if cat == "venda" else "nao_enviar", comum.agora_utc()))
        n += 1
    c.commit()
    return n


def main():
    token()
    with comum.conectar() as c:
        comum.preparar(c)
        print(f"{triar_pendentes(c)} pedidos antigos classificados.")
        triagem_ia.reclassificar_pendentes(c)
        fila = c.execute("SELECT p.* FROM pedidos_formulario p JOIN triagem t USING(event_id) "
                         "WHERE t.categoria='venda' AND t.status_crm='pendente' ORDER BY p.criado_em").fetchall()
        print(f"{len(fila)} pedidos de venda a conferir no CRM.", flush=True)
        for i, p in enumerate(fila, 1):
            status, deal = processar(p)
            c.execute("UPDATE triagem SET status_crm=?, deal_id=?, tentativas=tentativas+1, atualizado_em=? WHERE event_id=?",
                      (status, deal, comum.agora_utc(), p["event_id"]))
            c.commit()
            if i % 25 == 0:
                print(f"  {i}/{len(fila)}", flush=True)
        print("Resultado:", dict(Counter(r[0] for r in c.execute("SELECT status_crm FROM triagem WHERE categoria='venda'"))))


if __name__ == "__main__":
    main()
