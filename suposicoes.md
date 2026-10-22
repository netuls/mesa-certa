# Suposições (não pude perguntar)

1. **"Pedido de demonstração" = pessoa real que quer comprar**, uma vez por pessoa (e-mail sem maiúsculas e espaços) na semana. Teste, suporte, fornecedor e spam ficam de fora. Quem pede de novo na mesma semana conta uma vez.
2. **Semana = segunda 00:00 a domingo 23:59 em Brasília.** O formulário grava em UTC (+3h); converti antes de contar.
3. **Os 7 negócios de domingo 11/10 depois das 21h** só existem no CRM (o lote do formulário termina 12/10 00:00 UTC = 11/10 21:00 em Brasília). Assumi que são pedidos reais.
4. **Os 9 negócios com origem "Manual"** foram digitados pelo time e não são pedidos do formulário. O SLA deles não conta.
5. **O prazo das 4 horas úteis começa quando o negócio nasce no CRM.** Conferi: a integração cria o negócio em segundos depois do envio do formulário (diferença mediana de 10 segundos), então o relógio não perde tempo ali.
6. **Horário útil = segunda a sexta, 08h–18h, sem feriados.** 12/10 é feriado nacional, mas o cenário trata a segunda como dia de trabalho.
7. **SLA é por *responsável* do negócio.** O CRM não guarda quem ligou. Só considero "contato feito" o que está em `primeiro_contato_em`.
8. **Negócios sem contato com prazo vencido contam como atraso**, não são ignorados. Os que ainda estão dentro das 4 horas ficam de fora da conta.
9. **Negócio que o CRM tem de antes de 28/09** e não tem mensagem do formulário é lixo só se nome ou e-mail forem claramente de teste. Na dúvida, venda.
10. **Pedido de quem já tinha negócio antigo** não abre negócio novo (o CRM não deixa) e não reabre o antigo. Só aparece no resumo.
11. **Pedido com assinatura inválida não vira negócio.** Pode ser erro de configuração do marketing ou falsificação; não decido sozinho.
12. **A limpeza automática de 06/10** (22 negócios fechados de uma vez) é um processo que existe; não sei quem a criou nem por quê.
13. **Os dados de teste (CRM mock, lote do webhook)** representam a semana de 05/10 a 11/10. A "data de hoje" dos negócios que a ferramenta cria (21/10) é a do relógio do mock, não a do cenário.
14. **Uso de IA na triagem.** Assumi que mandar o texto da mensagem (sem nome, e-mail ou telefone) a um modelo externo é aceitável, e que a chave fica por conta de quem opera, já que a empresa não fornece. Sem chave, a triagem funciona só com regras.
15. **O canal do resumo (Slack ou e-mail) ainda não foi escolhido por ela.** Preparei os dois; basta um. Assumi envio toda segunda às 07:00 de Brasília, antes de ela abrir o CRM. O envio real não foi testado: só contra um Slack e um servidor de e-mail simulados.

## As 5 perguntas que eu faria a ela

1. O que você quer contar como "pedido de demonstração": pessoa única, ou cada vez que alguém preenche o formulário? E o cliente que pede de novo semanas depois conta de novo?
2. As 4 horas úteis contam a partir do momento em que a pessoa preenche o formulário, ou a partir de quando o negócio aparece para o SDR?
3. Os negócios de teste, suporte e fornecedor que já estão na fila: você quer que o sistema feche sozinho (como "Perdido") ou prefere uma lista para decidir?
4. Quando alguém que já tem negócio pede demonstração de novo, o que você quer que aconteça: reabrir o negócio, criar um novo (com e-mail diferente) ou só te avisar?
5. A ligação que vale como "retorno" é só a primeira ligação, ou também WhatsApp/e-mail? E quem registra isso no CRM hoje: o SDR responsável ou qualquer um do time?