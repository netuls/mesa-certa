# Como reproduzir o fluxo com o CRM de teste

Este procedimento é para ambiente local e dados fictícios. Não use tokens reais. O segredo do formulário não está incluído nesta entrega; obtenha o valor de teste das instruções originais do desafio e passe-o apenas por variável de ambiente.

1. Em um terminal, entre em `ambiente-teste/crm-mock` e defina `CRM_TOKEN=local-mock-only` (PowerShell: `$env:CRM_TOKEN="local-mock-only"`). Rode `python crm-mock.py --reset`. O CRM simulado fica em `http://127.0.0.1:8001`.
2. Em outro terminal, entre em `solucao`. Defina `CRM_TOKEN=local-mock-only`, `CRM_URL=http://127.0.0.1:8001`, `WEBHOOK_SECRET` com o segredo de teste fornecido no enunciado original e `MESA_DB` apontando para `mesa_certa.db`. Rode `python receptor.py` (porta 8000).
3. Em um terceiro terminal, entre em `ambiente-teste/webhook` e rode `python enviar-lote.py --limite 10` para uma amostra. Para o lote completo, rode `python enviar-lote.py`.
4. Volte ao terminal de `solucao` e rode `python sincronizar_crm.py`. A execução pode demorar porque o mock injeta falhas, atrasos e limite de chamadas; se for interrompida, rode novamente. O processo foi feito para poder ser repetido.
5. Rode `python verificar_crm.py --saida estado-final-crm.md`. A evidência válida é o estado consultado na API. O comando sai com código diferente de zero se alguma conferência falhar.
6. Rode `python -m unittest -v` para os 17 testes locais.

Para repetir desde o zero, pare os serviços, restaure `solucao/mesa_certa.db` a partir de `dados/mesa_certa.original.db` e rode o mock com `--reset`. O arquivo `crm-mock-estado.json` e `envios.log` são artefatos temporários e não devem ser entregues.
