# CRM de teste local

Este mock simula a API do CRM do desafio e começa com 391 negócios gerados a partir de `dados/mesa_certa.original.db`.

## Executar

No terminal, defina um token local de teste (não use token de produção):

- Linux/macOS: `export CRM_TOKEN=local-mock-only`
- PowerShell: `$env:CRM_TOKEN="local-mock-only"`

Depois execute `python crm-mock.py --reset`. A API fica em `http://127.0.0.1:8001`.

O arquivo `crm-mock-estado.json` é criado durante a execução e não deve ser entregue nem versionado. O token é apenas para este mock local; não dá acesso a sistemas reais.
