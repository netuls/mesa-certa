"""Configuração e acesso ao banco. Segredos só por variável de ambiente (nunca no código)."""
import datetime as dt
import os
import sqlite3
import sys

DB = os.environ.get("MESA_DB", "mesa_certa.db")


def exigir(nome):
    v = os.environ.get(nome)
    if not v:
        sys.exit(f"Defina a variável de ambiente {nome} (veja env.example).")
    return v


def conectar():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def preparar(c):
    """Cria só o que é nosso; não altera colunas existentes. Pode rodar quantas vezes quiser."""
    c.executescript("""
    CREATE UNIQUE INDEX IF NOT EXISTS ux_pedidos_event ON pedidos_formulario(event_id);
    CREATE TABLE IF NOT EXISTS triagem (
      event_id TEXT PRIMARY KEY, categoria TEXT NOT NULL, motivo TEXT,
      status_crm TEXT NOT NULL DEFAULT 'pendente',  -- pendente|criado|ja_no_crm|repetido_no_crm|erro_dados|nao_enviar
      deal_id INTEGER, tentativas INTEGER DEFAULT 0, atualizado_em TEXT);
    -- tudo que o receptor NÃO aceitou (assinatura ruim, corpo cortado): guardamos para um humano olhar
    CREATE TABLE IF NOT EXISTS quarentena (
      id INTEGER PRIMARY KEY AUTOINCREMENT, recebido_em TEXT, motivo TEXT, event_id TEXT, nome TEXT, email TEXT, corpo TEXT);
    """)
    c.commit()


def agora_utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
