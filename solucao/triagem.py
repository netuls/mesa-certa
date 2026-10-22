"""Decide se um pedido do formulário é venda. Regras explícitas, em ordem. Na dúvida, venda (perder cliente custa mais que ligar para um lixo).
Categorias: venda | teste | spam | fornecedor | suporte."""
import re

TESTE_ID = re.compile(r"(^|[._@\s])(teste|test)\w*([._@\s]|$)|@mesacerta\.com\.br|@teste\.com|dev\.teste|\b(asdf|fulano)\b", re.I)
TRIVIAIS = {"teste", "testando o formulário", "asdf", "ghjkl", "aaaaaa", "123", "???", ".", ""}
# mensagem que é só teste: "teste de envio", "só testando...", "só vendo se chegou", letras repetidas ("xxxxx", "aaa bbb ccc")
TESTE_MSG = re.compile(r"^\W*((só|apenas) )?(testando|teste|test|vendo se (chegou|funciona))\b|^(\w)\5{3,}$|^(\w)\6{2}( (\w)\8{2})+$", re.I)
SPAM = re.compile(
    r"bit\.ly|https?://|www\.|seguidores|ganhe (dinheiro|r\$|\d)|renda extra|sem sair de casa|trabalhando de casa|"
    r"clique (aqui|no link|agora)|sorteado|retire seu prêmio|receba seu prêmio|ganhar um iphone|empréstimo|bitcoin|cripto", re.I)
FORNECEDOR = re.compile(
    r"fornecedora|tráfego pago|venda de (insumos|uniformes|embalagens)|insumos com preço|preço de atacado|desconto (para|de) atacado|"
    r"oferecemos|apresentar (nossos|nossas)|agência de (marketing|publicidade)|plataforma de fotos|"
    r"somos (uma )?(distribuidora|fabricante|fornecedor|agência)|queremos fornecer|vendemos|fazemos (criação|sites?|desenvolvimento)|"
    r"trabalhamos com (consultoria|marketing|seo)|orçamento especial|condições especiais|"
    r"(empresa|vendemos|oferecemos|oferta).{0,40}(maquininhas?|máquinas? de cartão)|maquininhas? (de cartão )?com taxas|máquinas? de cartão sem", re.I)
SUPORTE = re.compile(
    r"esqueci (minha )?senha|impressora não (está )?imprim|parou de atualizar|sou cliente (e|de)|já sou cliente|acesso foi bloqueado|"
    r"problema no pagamento|como altero|cancelar um pedido|"
    r"não consigo (entrar|acessar|logar)|dificuldade de entrar|erro de login|redefinir (a |minha )?senha|senha não (funciona|chega)|"
    r"fora do ar|travou|não (estou )?receb|não estão chegando|segunda via|estorno|cobraram|cobrança veio|"
    r"cancelar (a |minha )?assinatura|trocar o e-mail do cadastro|exportar (o )?relatório|já uso o sistema", re.I)

# ---------------------------------------------------------------------------
# Segunda camada: sinais mais gerais (funcionam com frases que nunca vimos).
# Só valem quando a mensagem NÃO mostra vontade de comprar (INTENCAO_COMPRA).
# Escritas sem acento: o texto é normalizado antes (sem acento, minúsculo).
# ---------------------------------------------------------------------------
import unicodedata


def _norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


INTENCAO_COMPRA = re.compile(
    r"quanto (\w+ )?(custa|fica|cobra\w*)|\bvalor(es)?\b|\bpreco|tabela de preco|(quero|queria|gostaria de|preciso de|pedir|solicitar) (receber )?(uma )?proposta|\bcontratar\b|demonstracao|"
    r"\bconhecer\b|tenho interesse|interesse (no|em|na)|falar com (um |o )?(consultor|vendedor)|contato de (um )?vendedor|agendar|reuniao|"
    r"quero (saber|entender|ver|experimentar|testar|migrar|trocar|receber|resolver|uma alternativa)|"
    r"gostaria de (saber|conhecer|ver)|queria (saber|entender|conhecer|ver|detalhes)|alternativa|"
    r"vo(ce|cê)s (tem|fazem|atendem|oferecem|integram|emitem|aceitam pix)|voces (tem|fazem|atendem|oferecem|integram|emitem)|"
    r"(tenho|abri|vou abrir|sou dono|sou dona|minha) (um |uma |de |do |da )?(restaurante|bar|lanchonete|pizzaria|padaria|cafeteria|"
    r"hamburgueria|sorveteria|buffet|delivery|food|loja|rede|cantina|acaiteria|marmita)|sou (dono|dona|proprietari\w+|gerente|socio|socia)|(meu|minha) (negocio|restaurante|loja|bar|delivery|empresa|operacao|unidade)|comparando (sistemas|solucoes|plataformas)|avaliando (sistemas|solucoes)|pesquisando (sistemas|solucoes)|plano mais barato|teste gratis|versao gratuita|periodo (de teste|gratis)", re.I)

SPAM2 = re.compile(
    r"(?<![\w@.-])[\w-]+\.(com|net|org|xyz|top|info|biz|link|site|club)(\.br)?\b|tinyurl|encurtad|"
    r"cham[ae] (no )?(zap|whats\w*|privado|inbox)|no (zap|whats\w*) \(?\d|\(?\d{2}\)? ?9?\d{4}-?\d{4}|"
    r"\bganhe\b|voce (foi |ja )?(ganhou|selecionad|sortead)|parabens, voce|resgate|confirme seus dados|atualize sua senha|"
    r"conta (foi )?(suspensa|bloqueada)|pacote (esta )?retido|regularize agora|dinheiro facil|retorno de \d+ ?%|dobre seu dinheiro|"
    r"\binvista\b|oportunidade unica|investimento com retorno|forex|cassino|bonus de boas|emagre|calvicie|tratamento natural|"
    r"frete gratis|compre ja|curtidas|followers|renda extra|trabalho remoto|faca seu (site|logo)|por \d+ reais", re.I)

FORNECEDOR2 = re.compile(
    r"\b(sou|somos) (da |de |uma |um )?(empresa|equipe|agencia|consultor\w*|designer|fotograf\w*|publicitari\w*|contador\w*|"
    r"corretor\w*|vendedor\w*|representante\w*|fabricante|distribuidor\w*)|"
    r"\b(nossa|nosso) (empresa|equipe|time|servico|produto)|\b(represento|representamos|represent\w+ comerciais?)\b|"
    r"\b(temos|trabalhamos com|prestamos|fazemos|vendo|vendemos|ofereco|oferecemos|atendemos)\b|"
    r"gostar?iamos de (oferecer|propor|apresentar)|propor (uma )?parceria|parceria de divulgacao|\bparcerias?\b|"
    r"posso apresentar|podemos (enviar|apresentar)|enviar amostras?|\baluguel de|\blocacao\b|\d+ ?% de desconto|"
    r"preco especial|direto da fabrica|interessa\?|revenda de|procuro parceiros|ser nosso parceiro|catalogo|"
    r"servico de (dedetizacao|limpeza|seguranca|marketing)|setor alimenticio|ramo de alimentacao", re.I)

SUPORTE2 = re.compile(
    r"(nao|n) (abre|conecta|funciona mais|aparece|carrega|sincroniza|imprime|consigo (emitir|imprimir|cadastrar|gerar|fechar|baixar|editar))|"
    r"parou de|\btrava(r|ndo|ou|m)?\b|fecha sozinho|\blent[oa]\b|sumiram|sumiu|\bbug\b|aparece (um )?erro|(da|deu|dando) erro|erro (na|no) (sistema|app|login|emissao|nota|impressao|pagamento|relatorio)|"
    r"depois da atualizacao|atualizei|desde ontem|\bchamado\b|suporte (nao|nunca|demora)|falar com o suporte|ninguem respond\w*|"
    r"reembolso|vencimento|mensalidade|alterar o cartao|trocar a senha|senha expirou|\bmeu (painel|tablet|caixa|app)\b|"
    r"\bfechei o caixa|ficou diferente|"
    r"como (eu )?(faco|adiciono|cadastro|altero|mudo|configuro|edito|removo|exporto|recupero|cancelo) ", re.I)

TESTE2 = re.compile(
    r"hello world|lorem ipsum|\b(asd\w*|qwer\w*|zxc\w*|hjkl\w*)\b|mensagem de (teste|prova)|"
    r"(e|eh|era) (so |apenas )?um teste|pode ignorar|desconsider\w+|\btestando\b|^\W*(ok|oi+|ola|blz)\W*$", re.I)


def corrigir_acentos(s):
    """UTF-8 lido como Windows-1252 ('SÃ©rgio' -> 'Sérgio'). Só desfaz quando dá certo."""
    if not isinstance(s, str) or not re.search("[ÃÂ]", s):
        return s
    for enc in ("cp1252", "latin-1"):
        try:
            return s.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return s


def classificar(ev):
    msg = (ev.get("mensagem") or "").strip()
    rest = (ev.get("restaurante") or "").strip()
    nome = (ev.get("nome") or "").strip()
    email = (ev.get("email") or "").strip()
    if TESTE_ID.search(f"{nome} {email}") or nome.lower() in ("x", "teste"):
        return "teste", "nome ou e-mail de teste"
    if SPAM.search(msg):
        return "spam", "link ou oferta suspeita"
    if msg.lower() in TRIVIAIS and rest in ("", "."):
        return "teste", "sem mensagem útil e sem restaurante"
    if msg.lower() in TRIVIAIS and msg.lower() not in ("",):
        return "teste", "mensagem sem sentido"
    if TESTE_MSG.search(msg):
        return "teste", "mensagem de teste"
    if FORNECEDOR.search(msg):
        return "fornecedor", "quer vender algo para a Mesa Certa"
    if SUPORTE.search(msg):
        return "suporte", "cliente atual pedindo ajuda"
    # Segunda camada. Se a pessoa mostra vontade de comprar, fica como venda ("na dúvida, venda").
    n = _norm(msg)
    if INTENCAO_COMPRA.search(n):
        return "venda", "pedido comercial"
    if SPAM2.search(n):
        return "spam", "padrão de golpe ou propaganda"
    if TESTE2.search(n):
        return "teste", "mensagem de teste"
    if FORNECEDOR2.search(n):
        return "fornecedor", "oferece um serviço ou produto"
    if SUPORTE2.search(n):
        return "suporte", "problema ou dúvida de quem já usa"
    return "venda", "pedido comercial"
