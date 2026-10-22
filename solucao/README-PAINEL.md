# Painel web Mesa Certa

## Como iniciar no Windows
1. Instale o Python 3.10 ou superior, se ainda não tiver.
2. Confirme que `mesa_certa.db` está nesta pasta (`solucao/`).
3. Dê dois cliques em `INICIAR-PAINEL.bat`.
4. Abra `http://127.0.0.1:8080` no navegador.

Também é possível iniciar pelo terminal: `python app.py` (porta 8080 por padrão; `PANEL_PORT` permite mudar).

## O que existe no painel
- Indicadores do funil comercial e gráficos em barras.
- Indicadores de SLA por SDR para oportunidades de 05 a 11/10/2026.
- Fila de oportunidades sem primeiro contato e com prazo vencido, calculada na referência do enunciado (12/10/2026 às 08h).
- Pesquisa e filtros por etapa/responsável.
- Conferência da cobertura da base de formulário e categorias identificadas.
- Tabela de negócios e exportação CSV.

## Importante sobre a base
O painel abre o SQLite em **modo somente leitura** e não modifica o CRM. A base de trabalho começa com o retrato inicial de 391 negócios e 100 pedidos de formulário. Por isso, o painel avisa que não tem a cobertura do formulário da semana 05–11/10 e não inventa esse total. O painel é opcional para inspeção; o canal principal para a gestora é o resumo semanal por Slack/e-mail. Valide o estado final do CRM pela API antes de usar números como evidência definitiva.

## Privacidade
O servidor escuta apenas em `127.0.0.1`, para uso local. Não publique na internet sem autenticação e controles de acesso: a tabela contém dados pessoais de contatos.


## Indicador de pedidos de demonstração
O painel exibe 125 pessoas distintas como estimativa documentada para 05–11/10/2026, conforme `respostas.md`. Esse valor é apresentado com ressalva: não é recalculado a partir da base local de formulários, que cobre 28/09–04/10. Para validação independente, importe e reconcilie o lote de webhook da semana analisada.

## Sobre a triagem
O painel não mostra mais o aviso sobre a triagem, porque ele é voltado para a gestora. A medição e as ressalvas continuam em `medicao-triagem.md`.

## O que o painel não tem
Não há chat nem assistente de perguntas neste painel. Uma versão anterior da documentação citava um chatbot de perguntas frequentes; ele não faz parte desta entrega. O canal principal da gestora continua sendo o resumo semanal por Slack ou e-mail.


## Carga do lote sem segredo
`INICIAR-PAINEL.bat` roda `importar_lote.py`, que não precisa de `WEBHOOK_SECRET`: nesse modo as assinaturas não são conferidas e só as 3 já conhecidas como inválidas (`lote-assinaturas-invalidas.txt`, sem o segredo) ficam de fora. É só para o painel local. O `receptor.py` continua exigindo `WEBHOOK_SECRET` e conferindo toda assinatura.
