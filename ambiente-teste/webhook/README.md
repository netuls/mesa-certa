# Lote de teste do formulário

`lote-webhook.jsonl` contém eventos e assinaturas de teste preparados para o desafio. `enviar-lote.py` reenvia os eventos ao receptor e registra tentativas em `envios.log`. As assinaturas são parte dos dados de teste; nenhum segredo de produção é fornecido aqui.

Para testar somente um pequeno lote: `python enviar-lote.py --limite 10`. Para o lote completo: `python enviar-lote.py`. O receptor deve estar disponível em `http://127.0.0.1:8000/webhook`.

Para novos eventos fora do lote, configure `WEBHOOK_SECRET` por variável de ambiente com o segredo fornecido pelo responsável pelo formulário. Não grave esse valor no repositório.
