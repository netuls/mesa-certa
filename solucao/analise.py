"""Cálculos do resumo semanal. Só lê o banco (nunca escreve). Horários de Brasília, exceto pedidos_formulario (UTC)."""
import collections
import datetime as dt
import sqlite3

from horas_uteis import horas_uteis
from triagem_ia import classificar_final as classificar

ETAPAS = ["Novo", "Contato", "Reunião marcada", "Reunião realizada", "Perdido"]
SLA_H = 4.0


def conectar(db):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    return c


def brt(utc):
    return dt.datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ") - dt.timedelta(hours=3)


def categorias_por_email(c):
    """e-mail -> categoria (venda/teste/spam/fornecedor/suporte), a partir do que o formulário disse."""
    m = {}
    for r in c.execute("select * from pedidos_formulario order by id"):
        e = dict(r)
        m.setdefault((e["email"] or "").strip().lower(), classificar(e)[0])
    return m


def categoria_do_deal(d, mapa):
    k = (d["email"] or "").strip().lower()
    if k in mapa:
        return mapa[k]
    return classificar({"nome": d["nome"], "email": d["email"], "restaurante": d["restaurante"], "mensagem": "x"})[0]


def funil(c):
    q = dict(c.execute("select etapa, count(*) from negocios_crm group by 1").fetchall())
    return {e: q.get(e, 0) for e in ETAPAS}


def pedidos_semana(c, ini, fim):
    """ini/fim: datetime em Brasília, fim exclusivo. Devolve dicionário com a ponte completa."""
    ini_s, fim_s = ini.strftime("%Y-%m-%d %H:%M:%S"), fim.strftime("%Y-%m-%d %H:%M:%S")
    deals = [dict(r) for r in c.execute("select * from negocios_crm")]
    mexidos = [d for d in deals if ini_s <= d["atualizado_em"] < fim_s]
    criados = [d for d in deals if ini_s <= d["criado_em"] < fim_s]
    eventos = {}
    for r in c.execute("select * from pedidos_formulario order by id"):
        e = dict(r); e["brt"] = brt(e["criado_em"]); e["cat"] = classificar(e)[0]
        eventos.setdefault(e["event_id"], e)
    ev_sem = [e for e in eventos.values() if ini <= e["brt"] < fim]
    por_email_ev = {(e["email"] or "").strip().lower(): e for e in eventos.values()}
    manuais = [d for d in criados if d["origem"] != "Site"]
    site = [d for d in criados if d["origem"] == "Site"]
    sem_evento = [d for d in site if d["email"].strip().lower() not in por_email_ev]   # janela que o formulário não cobre
    lixo = [d for d in site if d["email"].strip().lower() in por_email_ev
            and por_email_ev[d["email"].strip().lower()]["cat"] != "venda"]
    vendas_ev = [e for e in ev_sem if e["cat"] == "venda"]
    pessoas = {e["email"].strip().lower() for e in vendas_ev} | {d["email"].strip().lower() for d in sem_evento}
    tem_tri = c.execute("select name from sqlite_master where name='triagem'").fetchone()
    status = dict(c.execute("select event_id,status_crm from triagem").fetchall()) if tem_tri else {}
    em_crm = {d["email"].strip().lower() for d in deals}
    # sem negócio no CRM antes da nossa sincronização = não estava na cópia do CRM; 'criado' = a ferramenta abriu o negócio
    sem_negocio = [e for e in vendas_ev if e["email"].strip().lower() not in em_crm]
    criados_ferramenta = [e for e in vendas_ev if status.get(e["event_id"]) == "criado"]
    return {"mexidos": len(mexidos), "criados": len(criados), "antigos_mexidos": len(mexidos) - len([d for d in mexidos if d in criados]),
            "manuais": len(manuais), "site": len(site), "lixo": len(lixo),
            "lixo_por_tipo": dict(collections.Counter(por_email_ev[d["email"].strip().lower()]["cat"] for d in lixo)),
            "sem_evento_domingo_noite": len(sem_evento), "eventos_semana": len(ev_sem),
            "eventos_por_categoria": dict(collections.Counter(e["cat"] for e in ev_sem)),
            "vendas_submissoes": len(vendas_ev), "pessoas_distintas": len(pessoas),
            "sem_negocio": [(e["nome"], e["event_id"]) for e in sem_negocio],
            "criados_pela_ferramenta": len(criados_ferramenta)}


def sla(c, ini, fim, agora):
    """Por responsável. 'no prazo' = primeiro contato em até 4h úteis do nascimento do negócio.
    Só entram negócios cujo prazo JÁ venceu (ou foram contatados); os que ainda estão dentro das 4h ficam à parte."""
    ini_s, fim_s = ini.strftime("%Y-%m-%d %H:%M:%S"), fim.strftime("%Y-%m-%d %H:%M:%S")
    agora_s = agora.strftime("%Y-%m-%d %H:%M:%S")
    por = collections.defaultdict(lambda: collections.Counter())
    atrasos = collections.defaultdict(list)
    mapa = categorias_por_email(c)
    for r in c.execute("select * from negocios_crm where origem='Site' and criado_em>=? and criado_em<?", (ini_s, fim_s)):
        d = dict(r); who = d["responsavel"]
        if categoria_do_deal(d, mapa) != "venda":
            continue                                   # teste/suporte/fornecedor/spam não conta contra o SDR
        if d["primeiro_contato_em"]:
            h = horas_uteis(d["criado_em"], d["primeiro_contato_em"])
            if h <= SLA_H: por[who]["no_prazo"] += 1
            else: por[who]["atrasado"] += 1; atrasos[who].append(h)
        else:
            h = horas_uteis(d["criado_em"], agora_s)
            if h > SLA_H: por[who]["sem_retorno_vencido"] += 1; atrasos[who].append(h)
            else: por[who]["dentro_do_prazo_ainda"] += 1
    out = {}
    for who, k in sorted(por.items()):
        venc = k["no_prazo"] + k["atrasado"] + k["sem_retorno_vencido"]
        xs = sorted(atrasos[who])
        out[who] = {**k, "vencidos": venc, "pct_no_prazo": round(100 * k["no_prazo"] / venc) if venc else None,
                    "mediana_horas_dos_que_estouraram": round(xs[len(xs) // 2], 1) if xs else None}
    return out


def fila_hoje(c, agora, dias=14):
    """Negócios do formulário ainda em 'Novo', sem primeiro contato, que já passaram de 4h úteis. Mais antigos que 'dias' vão à parte."""
    agora_s = agora.strftime("%Y-%m-%d %H:%M:%S")
    corte = (agora - dt.timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    recentes, antigos = [], []
    mapa = categorias_por_email(c)
    for r in c.execute("select * from negocios_crm where etapa='Novo' and primeiro_contato_em is null and origem='Site' order by criado_em"):
        d = dict(r)
        if categoria_do_deal(d, mapa) != "venda":
            continue
        d["horas_uteis"] = round(horas_uteis(d["criado_em"], agora_s), 1)
        if d["horas_uteis"] <= SLA_H: continue
        (recentes if d["criado_em"] >= corte else antigos).append(d)
    return recentes, antigos


def lixo_na_fila(c):
    """Negócios abertos (não 'Perdido') que não são venda: sugestão de fechar."""
    mapa = categorias_por_email(c)
    out = []
    for r in c.execute("select * from negocios_crm where etapa<>'Perdido' order by criado_em"):
        d = dict(r); cat = categoria_do_deal(d, mapa)
        if cat != "venda":
            d["categoria"] = cat; out.append(d)
    return out


def pedidos_para_olhar(c):
    """O que NÃO virou negócio e precisa de gente: quarentena e pedidos repetidos."""
    quarentena = [dict(r) for r in c.execute("select * from quarentena order by id")] if c.execute(
        "select name from sqlite_master where name='quarentena'").fetchone() else []
    repetidos = [dict(r) for r in c.execute(
        "select p.nome,p.email,p.criado_em,t.deal_id from triagem t join pedidos_formulario p using(event_id) "
        "where t.status_crm='repetido_no_crm' order by p.criado_em")] if c.execute(
        "select name from sqlite_master where name='triagem'").fetchone() else []
    return quarentena, repetidos
