# Problemas identificados (na ordem em que resolvi)

| # | Problema na fala dela | Tipo | Esforço | O que fiz |
|---|---|---|---|---|
| 1 | "Por que 187 e o marketing diz outro número? Qual é o certo?" | Pergunta explícita | Grande | Reconciliação completa (ver `respostas.md`). Causa principal: a planilha conta negócios **mexidos** na semana, não **pedidos recebidos**. |
| 2 | "Pedido que o marketing manda e nunca chega no CRM" | Implícito | Médio | Receptor de webhook + sincronizador que confere o CRM antes de criar; quarentena para o que não dá para aceitar; sinalização dos pedidos repetidos. |
| 3 | "Fila cheia de coisa que não é venda (suporte, embalagem, teste)" | Implícito | Médio | Triagem por regras explícitas, em duas camadas: as frases já conhecidas e sinais mais gerais (golpe, oferta de serviço, problema de quem já é cliente), sempre com a trava "se a pessoa quer comprar, é venda". Depois das regras, um passo com IA lê só o que ficou como venda e só pode tirar da venda com confiança alta (`solucao/triagem_ia.py`). Numa amostra nova de 56 frases (só regras), escrita antes da mudança, acertou 95% e não barrou nenhum cliente real; nas 299 linhas de pedidos reais (284 pedidos distintos, contando os reenvios), nenhuma decisão mudou (`solucao/medicao-triagem.md`). As frases da amostra foram escritas por IA, então o resultado ainda precisa ser confirmado com pedidos marcados pelo comercial, e algum lixo escrito de jeito novo ainda pode chegar à fila. |
| 4 | "Time não pode mudar o jeito de usar o CRM" | Restrição | Transversal | A solução só escreve pela API do CRM e só cria negócio de venda. Ninguém precisa abrir outra tela. |
| 5 | "Quem está atrasando o retorno em 4h úteis, quanto, e quem está sem retorno agora" | Pergunta explícita | Grande | Cálculo em horas úteis (seg–sex, 08–18), por responsável, contando também quem nunca foi contatado; lista para cobrar hoje. |
| 6 | "Como está o time hoje: quantos em cada fase" | Pergunta explícita | Pequeno | Contagem por etapa no topo do resumo. |
| 7 | "Resumo toda segunda, sozinho, sem abrir outro sistema" | Pedido explícito | Médio | `relatorio_semanal.py` + `rodar_semana.sh` (cron, 07:00 segunda), entrega por Slack ou e-mail. |

## O que decidi NÃO resolver (e por quê)

- **"Perguntar depois e ele responder" (o "sonho").** Ela mesma diz que é sonho. Um agente que responde perguntas sobre o funil exige acesso ao banco, controle de erro e avaliação; com 6–7 horas, preferi acertar os números e o envio. O painel web foi mantido apenas como apoio opcional de inspeção/demonstração; não é o canal principal da gestora, porque ela pediu um resumo que chegue no Slack ou e-mail sem precisar abrir outro sistema.
- **Fechar sozinho os negócios que são lixo no CRM.** Mexer em etapa de negócio de outra pessoa é decisão da gestora (e "Perdido" suja a métrica de perdas). O resumo lista quantos são; fechar é uma pergunta em `suposicoes.md`.
- **Reabrir o negócio de quem pede demonstração de novo (e-mail repetido).** O CRM recusa e-mail repetido. Não criei negócio duplicado nem reabri o antigo sozinho: listo essas pessoas no resumo.
- **Criar negócio a partir de pedido com assinatura inválida.** Não dá para provar que veio do formulário. Fica em quarentena e aparece no resumo.
- **Provar quem ligou.** O CRM só guarda o responsável pelo negócio e quem mexeu por último; não guarda quem fez o primeiro contato. Por isso o SLA é por responsável e digo isso na resposta.
- **Feriados.** Não tratei (12/10 é feriado nacional, mas o cenário trata a segunda como dia de trabalho). Ver `suposicoes.md`.
- **Medir a IA com uma amostra marcada por pessoa.** O passo de IA existe, mas não consegui medir o acerto dele aqui, porque não há chave neste ambiente. O comando para medir está pronto (`python3 medir_triagem.py amostras/amostra-cega-2.csv --ia`); até rodar com a chave, o acerto da IA é desconhecido e a solução se apoia nas regras.

## Se houver mais de um jeito: o que escolhi e o que descartei

- **Entrega do resumo:** escolhi texto (Slack ou e-mail) gerado por script agendado. Descartei planilha com painel (mais um sistema) e bot com perguntas (ver acima).
- **Contagem do "número certo":** escolhi "pessoas distintas" (e-mail normalizado). Descartei "linhas do CRM" (inclui lixo, digitados à mão e repetidos) e "envios do formulário" (inclui reenvio e teste).