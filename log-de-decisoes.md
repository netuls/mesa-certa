# Log de decisões

**Início do trabalho:** quarta-feira, 21/10/2026, por volta das 14h.

**Nota sobre os horários:** não anotei o horário exato de cada passo na hora. Este log foi reconstruído depois, a partir do histórico das minhas conversas com o assistente de IA, e por isso lista os passos na ordem em que aconteceram, sem horário individual.

**Nota sobre autoria e uso de IA:** o enunciado permite IA em tudo, e usei. A análise e o código da solução (receptor, triagem, sincronizador, verificador, relatório) foram produzidos por um assistente de IA em uma conversa anterior; recebi esse material pronto e o usei como base. Depois, pedi a um assistente de IA que conferisse a entrega contra o enunciado. **Foi o assistente quem executou** as correções e as verificações (hook, prova no CRM de teste, recontagem do 125, medição da triagem, teste do envio); eu pedi, li os resultados e decidi o que entregar. Ainda preciso reproduzir essas verificações por conta própria e estudar o código linha por linha antes da conversa final.

## Parte A: o que fiz, na ordem

1. **Li o enunciado e recebi a entrega pronta** (pasta `entrega-mesa-certa`, de outro chat com IA). **Decisão:** usar como base, conferir contra o enunciado e estudar o código antes da conversa final.
2. **Pedi um índice do projeto** para entender onde está cada arquivo. **A IA sugeriu** um `INDEX.md`. **Recusei:** achei confuso. Pedi uma versão mais simples, e a IA gerou um mapa interativo, com caminhos por objetivo e uma lista de pendências.
3. **Conferi a entrega contra o enunciado, com a IA.** Os 7 testes passam e não há chave ou senha nos arquivos. **Pendências que identifiquei:** preencher este log, estudar o código e trocar o termo técnico “UTC” em `respostas.md` por linguagem simples.
4. **Pedi um site de apresentação** do projeto. **Escolhi** usar as cores da imagem de referência que enviei e o tom de cardápio. **Recusei** a primeira versão por ter termos que eu não entendia, e pedi uma linguagem mais objetiva e sem jargão.
5. **Pedi um roteiro para explicar o projeto** na entrevista e um Claude Doc com esse roteiro.
6. **Pedi um relatório de entrega** bonito e profissional para enviar ao gestor.
7. **Revisei este log.** Percebi que a versão original tinha o horário em branco e descrevia decisões que eu não tomei sozinho. **Decisão:** reescrever em primeira pessoa, com a divisão acima, em vez de inventar horários.

## Parte B: decisões da solução recebida (a revisar por mim)

Estas decisões foram tomadas pela IA na conversa anterior. Registro cada uma com o motivo, e vou confirmar que concordo com elas antes de entregar.

1. **O número certo é 125 pessoas, não 187.** A planilha conta negócios por data de atualização, não pedidos recebidos. Dos 187, 45 eram negócios antigos, 22 deles fechados de uma vez por uma limpeza automática na terça.
2. **Pedido com assinatura inválida não vira negócio.** Vai para quarentena e aparece no resumo, porque não dá para provar que veio do formulário (são 3 pedidos; se forem reais, o total sobe para 128).
3. **Triagem por regras explícitas, e não por IA.** Na dúvida, o pedido é tratado como venda. A IA recusou uma regra solta de “atacado/insumos”, que pegaria restaurante legítimo. O teste de 31 mensagens acertou 31, mas foi montado com as mesmas mensagens usadas para criar as regras, então não é medição independente.
4. **No prazo de 4 horas úteis, quem nunca foi ligado conta como atraso.** Contar só quem foi contatado esconderia o problema.
5. **Não acusar o SDR 2.** Ele tem o pior índice, mas o CRM não registra quem ligou, só o responsável pelo negócio.
6. **A ferramenta nunca confia na resposta do CRM.** Depois de qualquer falha, consulta o CRM de novo. A 1ª rodada criou 13 de 14 negócios e a 2ª completou sem duplicar. A prova é o estado final lido pela API: 405 negócios, 6 de 6 conferências corretas.
7. **Ficou de fora de propósito:** assistente que responde perguntas, fechar sozinho o que não é venda, reabrir negócio de e-mail repetido e feriados.

## Registro adicional de validação e empacotamento

**2026-10-21 22:25 (Brasília, horário local calculado a partir do relógio UTC do ambiente):** reuni os documentos, o painel opcional, a cópia original do banco, a planilha e os arquivos do mock/webhook em uma única pasta. **Decisão:** separar a porta do painel (8080) da porta do receptor (8000), para que possam funcionar ao mesmo tempo. **Decisão:** não incluir `.env` nem o segredo do formulário; as credenciais devem ser configuradas fora do pacote.

**2026-10-21 22:25 (Brasília):** rodei `python -m py_compile solucao/*.py` e `python -m unittest -v`; os sete testes unitários passaram. Também iniciei o painel em porta alternativa e confirmei que `/` e `/api/dashboard` responderam HTTP 200, com 391 negócios no retrato inicial e aviso explícito de que a base do formulário só cobre 28/09–04/10.

**2026-10-21 22:25 (Brasília):** tentei reproduzir a integração completa com o mock instável e uma amostra de 20 eventos. O receptor aceitou os eventos, mas a rodada de sincronização não terminou dentro do limite de execução disponível, devido às falhas/atrasos deliberadamente injetados pelo mock. **Não considero essa tentativa uma nova comprovação de ponta a ponta.** Mantive a evidência histórica `solucao/estado-final-crm.md` separada e expliquei no README que ela registra uma execução anterior; a prova atual deve ser refeita com `verificar_crm.py` ao executar o lote completo.

**Nota de integridade:** as etapas históricas acima da seção Parte A foram reconstruídas a partir do histórico disponível; não possuo horário exato para cada decisão passada e não inventei esses horários. Os horários detalhados desta seção registram apenas as verificações feitas durante o empacotamento.

## Registro de 21/10/2026 (23h38 em diante), com o assistente de IA

*Horários arredondados a partir do relógio da sessão (a sincronização terminou às 23:47:14 e os negócios novos no CRM têm hora gravada), não medidos minuto a minuto. Em cada linha, digo quem fez: **IA** = o assistente; **eu** = eu mesmo.*

- **23:38** **Eu** pedi ao assistente que conferisse a entrega contra o enunciado. **A IA** achou dois valores de teste escritos no hook `checar.sh` e o reescreveu para procurar só formatos de chave (`sk-…`, `xox…`, `SECRET=`/`TOKEN=`/`PASSWORD=` com valor). O primeiro padrão acusou o texto "local-mock-only" nos READMEs, e **a IA** excluiu os `.md` da checagem. **A IA** testou com um arquivo falso `TOKEN=abcdefgh12345`: o hook bloqueou. **Eu** recebi o zip corrigido.
- **23:42** **Eu** pedi que o assistente refizesse a prova de ponta a ponta. **A IA** fez numa cópia de trabalho, sem mexer na entrega: CRM de teste reiniciado (391 negócios), receptor ligado, lote completo enviado (201 entregas: 196 aceitas, 5 recusadas).
- **23:44–23:47** **A IA** rodou a sincronização com o CRM instável: 14 negócios criados, 11 pedidos repetidos reconhecidos, sem duplicar nas rodadas seguintes. `verificar_crm.py`: 405 negócios, 6 de 6 conferências ok. A IA substituiu `estado-final-crm.md` pela versão nova.
- **23:46** **A IA** mediu a triagem. Resultado ruim, registrado sem esconder: 182 de 184 no lote, mas só 8 de 24 em mensagens novas, e a regra `maquininhas?` tirou um cliente real. **A IA** não alterou as regras, para não ajustá-las às próprias 24 mensagens dela. Ficou como pendência em `medicao-triagem.md`; **a decisão de mexer nelas é minha**, e ainda não tomei.
- **23:48** **A IA** recontou o "125" por fora do código: 118 pessoas distintas no formulário + 7 negócios só no CRM (domingo à noite) = 125. **Eu não refiz essa conta.**
- **23:48** **A IA** testou o envio contra um Slack simulado local: o resumo chegou inteiro. Slack e e-mail reais não foram testados.
- **23:49** **A IA** trocou "assinatura inválida" por "sem confirmação de origem" em `respostas.md` e corrigiu no `LEIA-ME.md` a frase sobre o segredo.
- **23:55** **A IA** corrigiu `problemas.md` e `guia-para-ela.md`, que diziam que o lixo novo não vira negócio; a medição mostrou que só vale para padrões conhecidos.
- **23:58** **Eu** apontei que o log dizia "recontei o 125" em primeira pessoa, mas quem contou foi a IA. **A IA** reescreveu esta seção e a nota de autoria para dizer quem fez cada coisa.

## Registro de 22/10/2026 (a partir de 00:02), com o assistente de IA

*Horários aproximados, a partir do relógio da sessão. Em cada linha, digo quem fez: **IA** = o assistente; **eu** = eu mesmo.*

- **00:02** **Eu** pedi duas coisas: auditar os números e melhorar a triagem.
- **00:03** **A IA** recalculou os números por fora do código, direto no banco original (`solucao/auditoria-numeros.md`). Conferiram: planilha de 187 = negócios mexidos, 142 criados, 45 antigos, 22 fechados às 02:14 de terça pela limpeza, 125 pessoas, tabela de retorno por SDR (idêntica) e as taxas das 4 semanas. **Não conferiu:** a frase "47% contra 78%" por hora de chegada; **a IA corrigiu o texto** em `respostas.md` (nas 4 semanas dá cerca de 45% contra 75%; na semana isolada a diferença é pequena).
- **00:05** **A IA** melhorou as regras da triagem assim: congelou uma amostra reservada de 48 mensagens, ajustou as regras só com a amostra de ajuste, conferiu que nenhuma das 281 decisões nos pedidos reais mudou e escreveu uma terceira amostra, **cega**, de 50 mensagens, **depois** de congelar as regras. Resultado: 100% nas duas primeiras (que não valem como prova, porque a mesma IA escreveu amostras e regras) e **46% na cega**, sem barrar nenhum cliente real, mas deixando passar 27 de 28 lixos. **A IA parou de ajustar** para não contaminar a cega. Resultado em `solucao/medicao-triagem.md`.
- **00:06** **A IA** acrescentou 3 testes automáticos (agora 10): frases de cliente real que parecem lixo precisam continuar como venda, e nenhuma amostra pode barrar cliente real. **Eu ainda não li as regras novas de `solucao/triagem.py`**; preciso ler antes da conversa final.
- **Fica por minha conta:** pedir a uma pessoa do comercial que rotule 100 pedidos reais e decidir se entra um passo com IA para o lixo que as regras não pegam.
- **00:12** **Eu** pedi que o painel refletisse a medição da triagem. **A IA** acrescentou, em `solucao/index.html` e no HTML de reserva do `app.py`, uma nota na seção "Pedidos recebidos pelo formulário" com o resultado da amostra cega (46%, sem barrar cliente real). Testou: o painel sobe e a nota aparece. **A IA** também achou que `README-PAINEL.md` descrevia um chatbot de perguntas frequentes que **não existe** neste painel (e a própria IA repetiu isso antes sem conferir o código); removeu o trecho e disse isso no README. **Fica por minha conta:** decidir se apago o resto de código não usado do `app.py` (uma página de "Registro de contatos" sem rota, e uma cópia antiga das regras de triagem usada só se o import falhar).

## Registro de 22/10/2026 (madrugada), com o assistente de IA

*Horários aproximados, a partir do relógio da sessão. **IA** = o assistente; **eu** = eu mesmo.*

- **~03:00** **Eu** pedi que a IA melhorasse o filtro de lixo, porque o painel mostrava um aviso de 46% de acerto em frases novas. **A IA** escreveu e congelou uma amostra nova (`amostra-cega-2`, 56 frases) **antes** de mexer nas regras. Resultado inicial: 46%.
- **~03:10** **A IA** acrescentou uma segunda camada de regras em `triagem.py` (sinais gerais de golpe, oferta de serviço, suporte e teste), com a trava "se a pessoa quer comprar, é venda". Resultado na cega-2: 95% (53 de 56), nenhum cliente real barrado.
- **~03:12** Na primeira versão, o teste com os 299 pedidos reais mostrou 20 clientes barrados. **A IA** corrigiu a trava e conferiu de novo: nenhuma decisão mudou. **A IA** não ajustou as regras aos 3 erros que sobraram, para não gastar a amostra. Hash das regras em `amostras/regras-congeladas-v2.sha256`; testes automáticos agora são 12.
- **~03:20** **Eu** pedi para tirar do painel o aviso da triagem, porque o painel é para a gestora. **A IA** removeu o aviso de `app.py` e `index.html`. A ressalva continua em `medicao-triagem.md` e em `respostas.md`.
- **~03:25** **Eu** pedi uma conferência contra o enunciado. **A IA** apontou: o log não tem horários exatos (foi reconstruído), não há passo de IA na solução, o envio real por Slack ou e-mail não foi testado e alguns textos estavam desatualizados.
- **~03:30** **A IA** atualizou `como-assumir.md`, `guia-para-ela.md`, `problemas.md`, os READMEs e este log, e tirou o `roteiro-conversa-final.md` da entrega.
- **Fica por minha conta:** marcar 50 a 60 pedidos reais como venda ou não venda, decidir se entra um passo com IA só para o que as regras deixam passar, testar o envio com um Slack de verdade e estudar o código antes da conversa final.
- **~03:50** **Eu** pedi para fazer tudo respeitando o enunciado. **A IA** viu que o enunciado trata de IA ("diga onde, por que ali e como mediu") e que a solução não tinha nenhum passo com IA. **A IA** criou `triagem_ia.py`: lê só o que as regras deixam como venda, só tira da venda com confiança alta, erro ou dúvida = venda, só o texto da mensagem sai (sem nome, e-mail ou telefone), sem chave nada muda. Ligou no `sincronizar_crm.py` (antes de criar o negócio, não no receptor, porque o formulário desiste em 5 s) e no `medir_triagem.py --ia`. Testes: 17, com servidor de mentira.
- **~03:55** **A IA** não mediu o acerto da IA: não há chave aqui. Está escrito em `medicao-triagem.md`, `como-assumir.md` e `problemas.md`; **fica por minha conta** rodar a medição com a minha chave antes de confiar no passo. **A IA** também encurtou `quando-usar-o-que.md` para 3 linhas, como pede o enunciado.
