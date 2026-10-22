# Mesa Certa — entrega do desafio

Esta pasta reúne documentos, solução, painel opcional e ambiente de teste local. **Não há credenciais de produção nesta entrega.** Configure os segredos apenas em variáveis de ambiente; não envie `.env` para o repositório.

## Estrutura

- `problemas.md`: problemas e decisões de escopo.
- `respostas.md`: respostas para a gestora, definições e limites dos dados.
- `suposicoes.md`: premissas e cinco perguntas para confirmar depois.
- `como-assumir.md`: passagem técnica.
- `guia-para-ela.md`: instruções simples para a gestora.
- `log-de-decisoes.md`: decisões e registro transparente do que foi reconstruído depois.
- `solucao/`: receptor, triagem, sincronização com CRM, análise, relatório, testes e painel local de leitura.
- `ambiente-teste/`: mock do CRM e lote de webhook do desafio.
- `dados/mesa_certa.original.db`: cópia preservada do banco inicial; `dados/planilha-chefia.csv`: planilha usada pela gestora. `solucao/mesa_certa.db` é a cópia de trabalho.
- `.claude/`: instruções fixas, procedimento reutilizável e hook de validação para Claude Code.

## Verificações rápidas

1. Python 3.10 ou superior, sem dependências externas.
2. `cd solucao` e `python -m unittest -v` (17 testes automatizados).
3. `python -m py_compile *.py` (verifica sintaxe).
4. Para abrir o painel opcional no Windows, execute `solucao/INICIAR-PAINEL.bat`; abre `http://127.0.0.1:8080`. Não abra `index.html` diretamente. O receptor de webhook usa a porta 8000.

## Rotina automatizada

A rotina semanal é `solucao/rodar_semana.sh`: sincroniza pedidos aceitos, verifica o estado final pela API do CRM e gera/envia o resumo por Slack ou e-mail. Para operar de verdade, a pessoa responsável deve configurar `MESA_DB`, `WEBHOOK_SECRET`, `CRM_URL`, `CRM_TOKEN` e um canal de envio em variáveis de ambiente, manter `receptor.py` ativo e agendar o script para segunda-feira às 07:00 (horário de Brasília). Os valores reais não fazem parte do pacote.

O mock e o lote de teste permitem verificar o fluxo sem um CRM de produção. Para reproduzir, veja `ambiente-teste/README-TESTE.md`. Nenhum segredo está escrito em arquivo do pacote (inclusive no hook `.claude/hooks/checar.sh`); o segredo do formulário deve ser configurado por variável de ambiente a partir das instruções originais do desafio.

## Evidência e limite importante

`solucao/estado-final-crm.md` foi **regerado em 21/10/2026 (23h44–23h47)** a partir do zip: mock do CRM reiniciado com 391 negócios, lote completo de 201 entregas (196 aceitas, 5 recusadas), sincronização e `verificar_crm.py`. Resultado: 405 negócios, 14 novos, seis checagens aprovadas, o mesmo da execução anterior. As rodadas repetidas da sincronização não duplicaram nada. O banco entregue em `solucao/mesa_certa.db` continua sendo o retrato inicial de 391 negócios; para repetir, siga `ambiente-teste/README-TESTE.md`.

Também foram feitos: teste do envio do resumo contra um Slack simulado (`solucao/evidencia-envio.md`), auditoria dos números por recálculo independente (`solucao/auditoria-numeros.md`) e medição da triagem em amostras (`solucao/medicao-triagem.md`, com ressalvas importantes). O envio real por Slack/e-mail e a triagem com amostra rotulada por pessoa continuam pendentes.
