#!/usr/bin/env python3
"""Resumo semanal para a gestora. Uso: python relatorio_semanal.py [--agora "2026-10-12 08:00"] [--enviar]
Só lê o banco. Gera relatorios/AAAA-MM-DD.md e, com --enviar, manda por Slack (SLACK_WEBHOOK_URL) ou e-mail (SMTP_*).
Semana = segunda 00:00 a domingo 23:59 (Brasília) imediatamente anterior a 'agora'."""
import argparse
import datetime as dt
import json
import os
import pathlib
import urllib.request

import analise as a

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def semana_anterior(agora):
    seg = (agora - dt.timedelta(days=agora.weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
    return seg, seg + dt.timedelta(days=7)


def montar(c, agora):
    ini, fim = semana_anterior(agora)
    f, p, s = a.funil(c), a.pedidos_semana(c, ini, fim), a.sla(c, ini, fim, agora)
    recentes, antigos = a.fila_hoje(c, agora)
    lixo = a.lixo_na_fila(c)
    quarentena, repetidos = a.pedidos_para_olhar(c)
    L = [f"# Resumo da semana {ini:%d/%m} a {(fim - dt.timedelta(days=1)):%d/%m}", ""]
    L += ["## Como está o time agora"] + [f"- {e}: **{n}**" for e, n in f.items()] + [""]
    L += ["## Pedidos de demonstração na semana",
          f"**{p['pessoas_distintas']} pessoas** pediram demonstração (de segunda 00:00 a domingo 23:59, horário de Brasília), "
          "contando uma vez cada pessoa e deixando de fora teste, suporte, fornecedor e spam.", "",
          "Por que não é o número do CRM nem o da planilha:",
          f"- A planilha trouxe {p['mexidos']}: conta todo negócio **mexido** na semana. {p['antigos_mexidos']} eram negócios antigos "
          "(só nesta semana a limpeza automática fechou 22 de uma vez na terça).",
          f"- Negócios **criados** na semana: {p['criados']}. Desses, {p['manuais']} foram digitados pelo time (não vieram do formulário) "
          f"e {p['lixo']} eram lixo ({', '.join(f'{n} {k}' for k, n in p['lixo_por_tipo'].items())}).",
          f"- Pedidos reais que o CRM nunca recebeu: {len(p['sem_negocio'])}. A ferramenta abriu o negócio de {p['criados_pela_ferramenta']} deles.",
          "- Mais pedidos (ver 'Pedidos que precisam de gente'): pessoas que já tinham negócio antigo e os que chegaram sem confirmação de origem.", ""]
    L += ["## Retorno em até 4 horas úteis (negócios com prazo já vencido)",
          "| Quem | No prazo | Atrasados | Sem retorno e já vencidos | % no prazo |", "|---|---|---|---|---|"]
    tot = {"no_prazo": 0, "atrasado": 0, "sem_retorno_vencido": 0, "vencidos": 0}
    for who, k in s.items():
        L.append(f"| {who} | {k['no_prazo']} | {k['atrasado']} | {k['sem_retorno_vencido']} | {k['pct_no_prazo']}% |")
        for kk in tot: tot[kk] += k[kk]
    L += [f"| **Time** | {tot['no_prazo']} | {tot['atrasado']} | {tot['sem_retorno_vencido']} | "
          f"{round(100 * tot['no_prazo'] / tot['vencidos']) if tot['vencidos'] else 0}% |", "",
          "Atenção: o CRM guarda quem é o responsável pelo negócio, mas não quem fez a ligação. Estes indicadores são por responsável atribuído e não comprovam quem realizou o contato.", ""]
    L += [f"## Cobrar hoje: {len(recentes)} pedidos sem retorno e acima de 4 horas úteis"]
    for who in sorted({d['responsavel'] for d in recentes}):
        ds = [d for d in recentes if d["responsavel"] == who]
        L.append(f"- **{who}** ({len(ds)}): " + ", ".join(f"{d['nome']} ({d['horas_uteis']}h)" for d in ds[:8]) + ("…" if len(ds) > 8 else ""))
    if antigos:
        L.append(f"- Esquecidos há mais de 14 dias: {len(antigos)} negócios (decidir: ligar ou marcar como perdido).")
    L.append("")
    L += ["## Pedidos que precisam de gente"]
    inval = [q for q in quarentena if q['motivo'] == 'assinatura_invalida']
    L.append(f"- {len(inval)} pedidos chegaram sem confirmação de origem e NÃO viraram negócio (não dá para confirmar que vieram do formulário): "
             + ", ".join(f"{q['nome']} <{q['email']}>" for q in inval) + f". Se forem verdadeiros, o total da semana sobe de {p['pessoas_distintas']} para até {p['pessoas_distintas'] + len(inval)}. Pedir ao marketing para conferir.")
    L.append(f"- {len(repetidos)} pessoas pediram de novo, mas já tinham negócio antigo e o CRM não abre outro: "
             + ", ".join(r['nome'] for r in repetidos[:12]) + ("…" if len(repetidos) > 12 else ""))
    L.append(f"- {len(lixo)} negócios abertos que não são venda (teste, suporte, fornecedor, spam) estão na fila do time.")
    return "\n".join(L) + "\n"


def enviar(texto):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if url:
        req = urllib.request.Request(url, data=json.dumps({"text": texto}).encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
        return "slack"
    if os.environ.get("SMTP_HOST"):
        import smtplib
        from email.message import EmailMessage
        m = EmailMessage(); m["Subject"] = texto.splitlines()[0].lstrip("# "); m["From"] = os.environ["SMTP_FROM"]; m["To"] = os.environ["SMTP_TO"]
        m.set_content(texto)
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", 587))) as s:
            s.starttls(); s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(m)
        return "email"
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("MESA_DB", "mesa_certa.db"))
    ap.add_argument("--agora", help='"AAAA-MM-DD HH:MM" em Brasília (padrão: agora)')
    ap.add_argument("--enviar", action="store_true")
    ap.add_argument("--saida", default="relatorios")
    x = ap.parse_args()
    agora = dt.datetime.strptime(x.agora, "%Y-%m-%d %H:%M") if x.agora else (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).replace(tzinfo=None)
    c = a.conectar(x.db)
    texto = montar(c, agora)
    pathlib.Path(x.saida).mkdir(exist_ok=True)
    caminho = pathlib.Path(x.saida) / f"{agora:%Y-%m-%d}.md"
    caminho.write_text(texto, encoding="utf-8")
    print(texto)
    if x.enviar:
        canal = enviar(texto)
        print(f"[enviado por {canal}]" if canal else "[nada enviado: defina SLACK_WEBHOOK_URL ou SMTP_*]")
