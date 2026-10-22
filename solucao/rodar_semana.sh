#!/bin/sh
# Toda segunda às 07:00 (Brasília):  0 7 * * 1  cd /caminho/solucao && . ./.env && ./rodar_semana.sh >> semana.log 2>&1
# 1) leva ao CRM o que o webhook recebeu e ainda não está lá; 2) prova no CRM; 3) gera e envia o resumo.
set -e
python3 sincronizar_crm.py
python3 verificar_crm.py --saida estado-final-crm.md
python3 relatorio_semanal.py --enviar
