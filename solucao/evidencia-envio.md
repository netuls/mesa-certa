# Evidência do envio do resumo (teste)

Teste feito em 21/10/2026, por volta de 23h48 (Brasília). O canal real (Slack ou e-mail) não foi usado: um servidor local fingindo ser o Slack (`http://127.0.0.1:9009/hook`) recebeu o envio.

- Comando: `SLACK_WEBHOOK_URL=http://127.0.0.1:9009/hook python3 relatorio_semanal.py --agora "2026-10-12 08:00" --enviar`
- Resultado: saiu com código 0 e imprimiu `[enviado por slack]`.
- O servidor falso recebeu o resumo inteiro (2.938 caracteres), começando por "Resumo da semana 05/10 a 11/10".

**O que isso prova:** o script monta a mensagem e a entrega por HTTP para o endereço configurado.
**O que não prova:** que a mensagem aparece bem formatada no Slack da empresa (o Slack pode exibir o Markdown de forma diferente) nem o envio por e-mail (SMTP). Com o endereço real, faça um envio de teste antes de agendar.
