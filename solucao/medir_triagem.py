#!/usr/bin/env python3
"""Mede a triagem contra um arquivo de mensagens etiquetadas (etiqueta|mensagem).
Uso: python3 medir_triagem.py amostras/amostra-reservada.csv [--ia]   (--ia: regras + passo com IA, precisa de ANTHROPIC_API_KEY)
Cada mensagem é testada com nome, e-mail e restaurante normais; só a mensagem varia."""
import sys, collections
import triagem
import triagem_ia

def medir(caminho, com_ia=False):
    linhas = [l.rstrip("\n").split("|", 1) for l in open(caminho, encoding="utf-8")][1:]
    acertos, erros, conf = 0, [], collections.Counter()
    for i, (et, msg) in enumerate(linhas):
        ev = {"nome": "Maria Souza", "email": f"maria{i}@gmail.com", "restaurante": "Cantina Sul", "mensagem": msg}
        r, _ = triagem.classificar(ev)
        if com_ia and r == "venda":
            res = triagem_ia.consultar(msg)
            if res: r = res[0]
        conf[(et, r)] += 1
        if r == et: acertos += 1
        else: erros.append((et, r, msg))
    return len(linhas), acertos, erros, conf

if __name__ == "__main__":
    com_ia = "--ia" in sys.argv
    if com_ia and not triagem_ia.habilitada():
        sys.exit("Defina ANTHROPIC_API_KEY para medir com a IA.")
    n, ok, erros, conf = medir([a for a in sys.argv[1:] if not a.startswith("--")][0], com_ia)
    fp = sum(v for (e, r), v in conf.items() if e == "venda" and r != "venda")
    fn = sum(v for (e, r), v in conf.items() if e != "venda" and r == "venda")
    print(f"{ok} de {n} certas ({round(100*ok/n)}%) | cliente real barrado: {fp} | lixo que passou como venda: {fn}")
    for e, r, m in erros: print(f"  etiqueta={e:10} regra={r:10} | {m[:80]}")
