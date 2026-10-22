#!/usr/bin/env python3
"""Prova no ESTADO FINAL DO CRM (lido pela API, não pelo log desta ferramenta).
Uso: CRM_TOKEN=... python verificar_crm.py [--saida evidencia-estado-final-crm.md]
Confere: (1) todo pedido de venda aceito tem negócio no CRM, (2) nada que não é venda foi criado por nós,
(3) sem e-mail repetido entre os negócios novos, (4) o total do CRM fecha. Sai com código 1 se algo falhar."""
import argparse
import json
import sys
import time
import urllib.request

import comum
import sincronizar_crm as crm


def todos_os_negocios():
    itens, pagina = [], 1
    while pagina:
        for _ in range(crm.TENTATIVAS):
            st, js = crm.chamar("GET", f"/deals?per_page=50&page={pagina}")
            if st == 200 and js and js.get("status") == "ok":
                break
            time.sleep(0.5)
        else:
            sys.exit("CRM não respondeu; tente de novo.")
        itens += js["data"]
        pagina = js["next_page"]
    return itens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default="evidencia-estado-final-crm.md")
    ap.add_argument("--base-id", type=int, default=None, help="maior deal_id antes da nossa execução (padrão: máximo da cópia do banco)")
    a = ap.parse_args()
    with urllib.request.urlopen(crm.URL + "/estado", timeout=10) as r:
        estado = json.loads(r.read())
    deals = todos_os_negocios()
    norm = lambda e: (e or "").strip().lower()
    with comum.conectar() as c:
        base = c.execute("SELECT MAX(deal_id), COUNT(*) FROM negocios_crm").fetchone()
        vendas = {norm(r[0]) for r in c.execute("SELECT p.email FROM pedidos_formulario p JOIN triagem t USING(event_id) WHERE t.categoria='venda'")}
        nao_vendas = {norm(r[0]) for r in c.execute("SELECT p.email FROM pedidos_formulario p JOIN triagem t USING(event_id) WHERE t.categoria<>'venda'")} - vendas
        criados = [r["deal_id"] for r in c.execute("SELECT deal_id FROM triagem WHERE status_crm='criado'")]
    base_id, base_total = base[0], base[1]
    if a.base_id:
        base_id = a.base_id
    por_email = {}
    for d in deals:
        por_email.setdefault(norm(d["email"]), []).append(d)
    novos = [d for d in deals if d["deal_id"] > base_id]
    falta = sorted(e for e in vendas if e not in por_email)
    indevidos = [d for d in novos if norm(d["email"]) in nao_vendas]
    fora_da_lista = [d for d in novos if norm(d["email"]) not in vendas]
    emails_novos = [norm(d["email"]) for d in novos]
    duplicados = sorted({e for e in emails_novos if emails_novos.count(e) > 1})
    sem_registro = sorted(set(d["deal_id"] for d in novos) - set(criados))
    checks = [
        ("Todo pedido de venda aceito tem negócio no CRM", not falta, f"{len(vendas) - len(falta)} de {len(vendas)}; faltam {len(falta)}"),
        ("Nenhum teste, spam, fornecedor ou suporte virou negócio", not indevidos, f"{len(indevidos)} indevidos"),
        ("Todo negócio novo veio de um pedido de venda", not fora_da_lista, f"{len(fora_da_lista)} sem pedido de origem"),
        ("Nenhum e-mail repetido entre os negócios novos", not duplicados, f"{len(duplicados)} repetidos"),
        ("Os negócios novos batem com o que a ferramenta diz ter criado", not sem_registro, f"{len(novos)} no CRM, {len(criados)} no registro"),
        ("O total do CRM fecha", estado["total"] == len(deals) == base_total + len(novos),
         f"/estado={estado['total']}, lidos={len(deals)}, antes={base_total}, novos={len(novos)}"),
    ]
    L = ["# Estado final do CRM (lido da API)", "", f"Total de negócios: **{estado['total']}** (antes: {base_total}, novos: {len(novos)})", "",
         "Por etapa: " + ", ".join(f"{k}: {v}" for k, v in sorted(estado["por_etapa"].items())), "",
         "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
    L += [f"| {n} | {'ok' if ok else 'FALHOU'} | {d} |" for n, ok, d in checks]
    L += ["", "## Negócios criados nesta rodada", "", "| deal_id | nome | criado_em (Brasília) |", "|---|---|---|"]
    L += [f"| {d['deal_id']} | {d['nome']} | {d['criado_em']} |" for d in novos]
    open(a.saida, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:14]))
    sys.exit(0 if all(ok for _, ok, _ in checks) else 1)


if __name__ == "__main__":
    main()
