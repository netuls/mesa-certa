# Projeto Mesa Certa (teste técnico)

Automação para a gestora comercial (não técnica): funil, pedidos de demonstração, SLA de 4h úteis e resumo semanal.

## Regras que valem sempre
- Horários: `pedidos_formulario.criado_em` é **UTC**; `negocios_crm` e `historico_etapas` são **Brasília**. Converta antes de comparar (UTC−3).
- "Semana" = segunda 00:00 a domingo 23:59 em Brasília. Hoje do cenário: segunda 12/10/2026 08:00.
- SLA = primeiro contato em até 4 **horas úteis** (seg–sex, 08–18). Use sempre `solucao/horas_uteis.py`; não reescreva a conta.
- "Pedido de demonstração" = pessoa real (e-mail normalizado) que quer comprar: sem teste, spam, fornecedor ou suporte; uma vez por pessoa.
- Nunca altere `mesa_certa.original.db`. Trabalhe em cópia (`MESA_DB=...`).
- Segredos só por variável de ambiente (ver `solucao/env.example`). Nunca grave token, segredo de webhook ou senha em arquivo. O ZIP não deve conter `.env`.
- O time não muda o jeito de usar o CRM: a solução escreve no CRM só pela API, e só cria negócio de pedido de venda.
- O CRM mock falha de propósito (500 que grava, 200 com erro, 429, demora de 8 s). Nunca confie no código de resposta: confira o CRM de novo. Máximo 5 req/s.
- Pedido com assinatura inválida **não vira negócio**: vai para a quarentena e aparece no resumo.
- Prova de que funcionou = estado final lido pela API (`verificar_crm.py`), não o log da ferramenta. A evidência em `solucao/estado-final-crm.md` foi regerada em 21/10; ao mudar o código de sincronização, regenere-a e confira as seis checagens.

## Como trabalhar
- Mudou `triagem.py`, `triagem_ia.py`, `horas_uteis.py` ou `analise.py`? Rode `cd solucao && python3 -m unittest -q` (o hook já faz isso). O painel local é opcional e deve usar a porta 8080; o receptor usa 8000.
- Para gerar o resumo: use a skill `relatorio-semanal`.
- Registre cada decisão em `log-de-decisoes.md` (horário real, o que a IA sugeriu, o que foi recusado).
- Responda à gestora em linguagem simples, sem jargão (SLA, webhook, UTC...). Diga a definição usada e o que os dados não provam.
- IA na triagem (`triagem_ia.py`): só lê o que as regras deixaram como venda; só tira da venda com confiança "alta"; erro ou dúvida = venda; nunca envie nome, e-mail ou telefone; nunca grave `ANTHROPIC_API_KEY` em arquivo. Ao mexer nas regras ou no prompt, meça de novo (`medir_triagem.py ... --ia`) e registre o número no `log-de-decisoes.md`. Amostras já usadas para ajustar não valem como prova.
