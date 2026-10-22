# Medição da triagem (quem é venda e quem não é)

Feita em 21–22/10/2026 por um assistente de IA (não por pessoa da empresa). Script: `python3 medir_triagem.py amostras/<arquivo>.csv`. Todas as amostras foram escritas e etiquetadas pelo mesmo assistente que mexeu nas regras; **nenhuma foi rotulada por pessoa do comercial**.

## Regras originais
| Amostra | Acerto | Cliente real barrado | Lixo que passou |
|---|---|---|---|
| Mensagens do lote (184 pedidos) | 182 de 184 (99%) | 0 | 0 (2 casos ambíguos) |
| 22 mensagens novas (`amostra-ajuste`) | 8 de 22 (36%) | 1 ("integrar com a minha maquininha") | 13 |
| 48 mensagens novas (`amostra-reservada`) | 25 de 48 (52%) | 2 | 21 |

As regras só reconheciam as frases que já existiam nos dados.

## Regras ajustadas (versão entregue)
Ampliei os vocabulários de suporte, fornecedor, spam e teste e corrigi duas regras largas demais (`impressora` e `maquininhas?`), usando só a `amostra-ajuste`.

| Amostra | Acerto | Cliente real barrado | Lixo que passou |
|---|---|---|---|
| Lote real (281 linhas de pedidos) | 0 decisões mudaram em relação às regras antigas | — | — |
| `amostra-ajuste` | 22 de 22 | 0 | 0 |
| `amostra-reservada` | 48 de 48 | 0 | 0 |
| **`amostra-cega`** (50 mensagens, escrita **depois** de congelar as regras) | **23 de 50 (46%)** | **0** | **27 de 28** |

**Como ler isso**
- Os 100% da reservada **não valem como prova**: o mesmo autor escreveu a amostra e depois as regras, já conhecendo a amostra. Ficam só como teste de regressão.
- A medida honesta é a **amostra cega: 46%**. As regras **não barram cliente real** (22 de 22 vendas passaram), mas **deixam passar quase todo o lixo escrito de jeito novo** (27 de 28): só "kkkkkk" foi pego.
- Ou seja: o sistema erra para o lado barato (um SDR perde um minuto com lixo) e quase nunca para o lado caro (descartar cliente). Mas a promessa "suporte, fornecedor, spam e teste não entram na fila" só vale para frases de padrão conhecido.
- Depois da cega, **não mexi mais nas regras**, para não contaminá-la. Os hashes ficam em `amostras/*.sha256` (a cega e as regras congeladas) para provar que não foram alterados.

## Por que não consertei de vez
Regras por palavras não alcançam frases novas ("Meu painel não abre", "Sou designer e faço logotipos"). Cobrir isso pede um modelo de linguagem classificando só o que as regras deixam passar como venda, medido com uma amostra rotulada por pessoa. Não fiz aqui porque não há chave de IA nem acesso externo neste ambiente, e uma medição feita pelo mesmo assistente que escreve as frases não seria independente.

## O que fazer
1. Uma pessoa do comercial rotula 100 pedidos reais (venda ou não). Rodar `medir_triagem.py` nessa amostra.
2. Se o acerto em lixo continuar baixo, adicionar o passo com IA, mantendo a regra "na dúvida, venda" e medindo na mesma amostra.
3. Enquanto isso, a seção "O que precisa de você" do resumo e a fila do time continuam sendo a rede de segurança.

---

# Atualização de 22/10/2026: segunda camada de regras

Feita por um assistente de IA, de novo sem pessoa do comercial.

**O que mudou em `triagem.py`**
- Nova camada de sinais gerais (sem acento, sem depender de frase exata): jeito de golpe/propaganda (link sem "http", "chama no zap", "ganhe", "retorno de X%"), de quem oferece serviço ("sou designer", "nossa empresa", "temos... para locação"), de quem já usa e tem problema ("não abre", "sumiram", "reembolso", "senha expirou") e de teste ("hello world", "qwerty", "pode ignorar").
- **Trava de segurança:** se a mensagem mostra vontade de comprar ("quanto custa", "quero conhecer", "sou dono de...", "tenho uma pizzaria"), ela continua como venda, mesmo com palavra de lixo. Isso mantém a regra "na dúvida, venda".
- "parceria", "represento" e "catálogo" saíram da camada forte (um cliente real também escreve isso) e passaram para a camada com trava.

**Medição**
| Amostra | Antes | Depois | Cliente real barrado |
|---|---|---|---|
| Pedidos reais (299 linhas) | — | 0 decisões mudaram | 0 |
| `amostra-cega` (50) | 46% | 100% | 0 |
| **`amostra-cega-2`** (56, escrita **antes** desta mudança, hash em `amostras/amostra-cega-2.sha256`) | **46%** | **95%** (53 de 56) | **0** |

- A `amostra-cega` **deixa de valer como prova**: foi usada para diagnosticar e agora serve só como teste de regressão (como a ajuste e a reservada).
- O número honesto é o da `amostra-cega-2`: **95%**. Os 3 lixos que ainda passam: "o valor ficou diferente do real" (suporte), "preço especial" e "interesse em ser nosso parceiro" (fornecedor). Palavras como *valor*, *preço* e *interesse* disparam a trava de compra. **Não ajustei as regras para essas 3**, para não gastar a amostra.
- Ao rodar nos pedidos reais, a primeira versão barrou 20 clientes ("Sou dono de churrascaria...", "Estou comparando sistemas..."). Foi corrigido antes de entregar; agora o teste automático cobre essas frases.

**Limites que continuam valendo**
- A amostra foi escrita pelo mesmo assistente que escreveu as regras, só que antes. Um comercial rotulando 100 pedidos reais continua sendo a prova de verdade.
- Regras não leem frases de padrão totalmente novo. Para chegar perto de 100%, o próximo passo continua sendo um modelo de linguagem só nos casos que as regras deixam como venda.
- Hash das regras desta versão: `amostras/regras-congeladas-v2.sha256`.

---

# Passo com IA (`triagem_ia.py`): implementado, ainda não medido

**Onde entra:** no `sincronizar_crm.py`, antes de criar o negócio, só para pedidos que as regras deixaram como venda e que ainda não foram ao CRM.
**Por que ali:** é onde as regras erram (frases novas), e é um volume pequeno (as mensagens que sobram como venda, uma vez cada; a resposta fica guardada em `triagem_ia_cache.json`).
**Trava:** a IA só tira da venda com confiança "alta". Erro, demora, resposta estranha ou dúvida mantêm a venda. Sem `ANTHROPIC_API_KEY`, nada muda. Só o texto da mensagem é enviado.

**O que foi testado:** a lógica (17 testes automáticos), com um servidor de mentira no lugar do modelo. **O que NÃO foi testado:** o acerto do modelo de verdade. Não havia chave neste ambiente, então não existe número de acerto da IA.

**Como medir (quem tiver a chave):**
1. `ANTHROPIC_API_KEY=... python3 medir_triagem.py amostras/amostra-cega-2.csv` (só regras) e depois o mesmo comando com `--ia` (regras e IA). Comparar acerto, cliente real barrado e lixo que passou.
2. Para uma prova independente, usar mensagens reais marcadas por alguém do comercial, num arquivo no mesmo formato (`etiqueta|mensagem`).
3. Só confiar na IA se ela não barrar nenhum cliente real na amostra. A `amostra-cega-2` já foi usada neste relatório, então vale como segunda medição, não como prova nova.
