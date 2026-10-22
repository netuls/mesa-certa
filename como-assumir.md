# Como assumir (1 página técnica)

## O que existe
O núcleo está em `solucao/`: Python 3 padrão, sem dependências externas, e SQLite. O CRM simulado e o lote de pedidos para reproduzir o teste ficam em `ambiente-teste/`. O banco recebido está preservado em `dados/mesa_certa.original.db`; `solucao/mesa_certa.db` é a cópia de trabalho.

| Arquivo | Papel |
|---|---|
| `receptor.py` | Recebe o webhook do formulário (porta 8000), valida a assinatura e grava o pedido e sua classificação. Assinatura ruim ou corpo ilegível vão para a quarentena. |
| `triagem_ia.py` | Passo com IA: lê só o que as regras deixaram como venda e pode tirá-lo da venda se tiver certeza alta. Roda no `sincronizar_crm.py`, antes de criar o negócio. Só existe se `ANTHROPIC_API_KEY` estiver definida. |
| `triagem.py` | Diz se o pedido é venda, teste, spam, fornecedor ou suporte. Regras em duas camadas, com a trava "se quer comprar, é venda". Também conserta acento quebrado. |
| `sincronizar_crm.py` | Garante que todo pedido de venda tenha negócio no CRM. Pode ser repetido sem duplicar: confere o e-mail antes de criar e confere de novo depois de qualquer erro. |
| `verificar_crm.py` | Prova o resultado pelo estado final lido na API (6 checagens). Sai com erro se alguma falhar. |
| `analise.py`, `horas_uteis.py` | Funil, pedidos da semana, prazo de 4 horas úteis e fila de hoje. Só leitura. |
| `relatorio_semanal.py`, `rodar_semana.sh` | Gera o resumo e envia por Slack ou e-mail. |
| `medir_triagem.py`, `amostras/` | Medem a triagem contra mensagens já etiquetadas. |
| `test_basico.py` | 17 testes (`python3 -m unittest -q`). |
| `app.py`, `index.html` | Painel local opcional, só leitura, na porta 8080. |

## Para subir
1. Copie `env.example` para `.env`, preencha e carregue com `. ./.env`. Segredo só por variável de ambiente, nunca em arquivo.
2. Aponte `MESA_DB` para uma cópia do banco, nunca para o original.
3. Deixe `python3 receptor.py` sempre no ar (systemd ou equivalente).
4. Agende na segunda às 07:00: `0 7 * * 1 cd /caminho/solucao && . ./.env && ./rodar_semana.sh >> semana.log 2>&1`.

A prova de que funciona está em `solucao/estado-final-crm.md`, lida direto da API: 405 negócios, 14 novos, 6 de 6 checagens. Para repetir, siga `ambiente-teste/README-TESTE.md`. O envio foi testado só contra um Slack simulado (`solucao/evidencia-envio.md`).

## Cuidados que já estão resolvidos
- O formulário grava em UTC e o CRM em Brasília; a semana começa às 00:00 de Brasília.
- O mesmo pedido pode chegar mais de uma vez, então o `event_id` é único no banco.
- O CRM falha de propósito e limita a 5 chamadas por segundo. Uma rodada completa leva uns 5 minutos; se estourar o tempo, rode de novo.
- E-mail repetido volta como 409 e aparece no resumo como "repetido no CRM".

## Limites conhecidos
- **Triagem.** Só com regras, numa amostra nova de 56 frases acertou 95% e não barrou nenhum cliente real; nos 299 pedidos reais nada mudou. Essa amostra foi escrita por IA.
- **Passo com IA, ainda sem medição.** Está implementado e testado só com um servidor de mentira. O acerto real dele não foi medido, porque neste ambiente não havia chave. Para medir: `ANTHROPIC_API_KEY=... python3 medir_triagem.py amostras/amostra-cega-2.csv --ia`. Por segurança, qualquer erro, demora ou dúvida do modelo mantém o pedido como venda, e só o texto da mensagem é enviado (nunca nome, e-mail ou telefone).
- **O retrato local do CRM** (`negocios_crm`) não se atualiza sozinho depois da sincronização; a prova é sempre a leitura pela API.
- **Feriados** não são tratados, e o CRM guarda quem é o responsável pelo negócio, não quem ligou.
- **Envio real** por Slack ou e-mail ainda não foi testado.
