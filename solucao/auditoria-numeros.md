# Auditoria dos números (feita em 22/10/2026, por um assistente de IA)

Recalculado **por fora do código da solução**, direto no banco original (`dados/mesa_certa.original.db`) e no lote do formulário, com outro método de contar horas úteis (passo de 1 minuto, em vez de somar o trecho de cada dia).

| O que | Resultado da auditoria |
|---|---|
| Planilha da gestora | As 7 linhas somam 187 e são o número de negócios **mexidos** (`atualizado_em`) por dia. Confere. |
| 187 → 142 | 45 dos 187 já existiam antes da semana; 142 foram criados nela. Confere. |
| Limpeza de terça | 22 negócios antigos foram fechados às 02:14 de 06/10 por `automacao_limpeza`. Confere. |
| 9 digitados à mão | 9 negócios com origem "Manual" entre os criados. Confere. |
| 125 pessoas | 118 pessoas distintas no formulário + 7 negócios só no CRM (domingo à noite) = 125. Confere. |
| Retorno em 4h úteis, semana 05–11/10 | SDR 1: 17 no prazo, 6 atrasados, 5 sem retorno; SDR 2: 12/5/7; SDR 3: 17/5/1. **Confere exatamente.** |
| Retorno em 4h úteis, últimas 4 semanas | 58%, 41% e 67%. Confere. |
| Retorno por hora de chegada | **Não confere como estava escrito** (47% contra 78%). Nas 4 semanas dá cerca de 44% (08–14h) contra 74% (14–18h); na semana isolada, 50% contra 57%. Texto corrigido em `respostas.md`. |

## Integridade dos dados (nada encontrado que invalide os números)
- Nenhum contato anterior à criação do negócio; `primeiro_contato_em` bate com a primeira entrada "Contato" do histórico em todos os negócios; o último passo do histórico é sempre a etapa atual.
- 49 contatos foram feitos fora do horário útil. A conta de horas úteis já trata isso (o relógio só anda dentro do expediente).
- 10 e-mails aparecem em mais de um negócio no CRM (4 de teste e 6 de pessoas reais: Thiago Santos, Bruno Gonçalves, Fábio Dias, Rodrigo Almeida, Patrícia Pereira, Sérgio Cardoso). Conferi: os 6 reais enviaram o formulário duas vezes, com 3 a 8 minutos de diferença (a ponte os chama de "enviaram duas vezes"); a contagem por e-mail distinto os conta uma vez só.
- 6 e-mails têm maiúscula ou espaço. A normalização usada (minúsculas, sem espaços) já cobre.
- 20 negócios "Perdido" nunca tiveram contato: 7 são anteriores à semana e 13 foram criados nela, e os 13 são lixo (5 pelo nome/e-mail de teste, 8 pela mensagem: suporte, fornecedor, spam e teste), fechados pelo time. Por isso nenhum entra na tabela de "sem retorno", que só tem negócios ainda em "Novo".
- 32 negócios da semana ainda estavam dentro das 4 horas úteis às 08h de segunda (chegaram sexta à tarde ou no fim de semana) e ficam fora da conta, como dito em `suposicoes.md`.

## O que a auditoria não cobre
- O lixo foi identificado por mim com um método parecido com o da solução (mensagens e nome/e-mail de teste); uma diferença de um ou dois negócios pode existir. As tabelas bateram exatamente, então é improvável.
- Não é uma auditoria feita por pessoa da empresa.
