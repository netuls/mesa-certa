"""Testes rápidos (python3 -m unittest). Rodam em segundos e sem rede."""
import unittest

from horas_uteis import horas_uteis as h
from triagem import classificar, corrigir_acentos


class HorasUteis(unittest.TestCase):
    def test_sexta_tarde_a_segunda_cedo(self):
        self.assertAlmostEqual(h("2026-10-09 17:00:00", "2026-10-12 09:00:00"), 2.0)

    def test_fim_de_semana_nao_conta(self):
        self.assertEqual(h("2026-10-10 12:00:00", "2026-10-11 12:00:00"), 0)

    def test_antes_de_abrir_so_conta_a_partir_das_8(self):
        self.assertAlmostEqual(h("2026-10-05 07:00:00", "2026-10-05 09:00:00"), 1.0)

    def test_dia_util_inteiro_sao_10h(self):
        self.assertAlmostEqual(h("2026-10-05 09:00:00", "2026-10-06 09:00:00"), 10.0)


class Triagem(unittest.TestCase):
    def cat(self, msg, nome="Ana", email="ana@gmail.com", rest="Pizzaria"):
        return classificar({"nome": nome, "email": email, "restaurante": rest, "mensagem": msg})[0]

    def test_vendas_curtas_e_com_a_palavra_testar(self):
        for m in ("Quero testar o sistema de vocês. Como começo?", "Quanto custa?", "Podem me ligar?", "Queria saber valores",
                  "Preciso de emissão de nota fiscal integrada com o cardápio. Vocês fazem isso?"):
            self.assertEqual(self.cat(m), "venda", m)

    def test_nao_vendas(self):
        self.assertEqual(self.cat("Preciso cancelar um pedido que entrou duplicado"), "suporte")
        self.assertEqual(self.cat("Agência de marketing digital, atendemos o setor de alimentação. Vamos conversar?"), "fornecedor")
        self.assertEqual(self.cat("Compre seguidores baratos!"), "spam")
        self.assertEqual(self.cat("teste", nome="Teste", email="teste@teste.com"), "teste")
        self.assertEqual(self.cat("???", nome="x", rest="."), "teste")

    def test_acentos(self):
        self.assertEqual(corrigir_acentos("SÃ©rgio Mendes"), "Sérgio Mendes")
        self.assertEqual(corrigir_acentos("Sérgio"), "Sérgio")


if __name__ == "__main__":
    unittest.main()


class TriagemSemBarrarCliente(unittest.TestCase):
    """O erro caro é barrar cliente real. Estas frases PARECEM lixo mas são venda."""
    def _cat(self, msg):
        return classificar({"nome": "Maria Souza", "email": "maria@gmail.com", "restaurante": "Cantina Sul", "mensagem": msg})[0]

    def test_perguntas_de_quem_quer_comprar_continuam_venda(self):
        for msg in ("Minha impressora fiscal é compatível com o sistema de vocês?",
                    "Preciso saber se vocês integram com a minha maquininha Stone.",
                    "Meu fornecedor de insumos indicou vocês, quero conhecer o sistema.",
                    "Vi que vocês têm suporte 24h, queria entender melhor antes de contratar.",
                    "Quero testar o sistema no meu restaurante antes de assinar, tem período de teste?",
                    "Preciso cancelar o sistema que uso hoje e trocar pelo de vocês, quanto custa?"):
            self.assertEqual(self._cat(msg), "venda", msg)

    def test_padroes_conhecidos_de_lixo(self):
        self.assertEqual(self._cat("Não consigo entrar no sistema, aparece erro de login."), "suporte")
        self.assertEqual(self._cat("Ganhe R$ 3000 por semana sem sair de casa! Clique no link"), "spam")
        self.assertEqual(self._cat("Bom dia, represento uma empresa de embalagens, posso enviar o catálogo?"), "fornecedor")
        self.assertEqual(self._cat("teste de envio"), "teste")


class AmostrasDeTriagem(unittest.TestCase):
    def test_nenhuma_amostra_barra_cliente_real(self):
        import os
        from medir_triagem import medir
        pasta = os.path.join(os.path.dirname(__file__), "amostras")
        for nome in ("amostra-ajuste.csv", "amostra-reservada.csv", "amostra-cega.csv"):
            n, ok, erros, conf = medir(os.path.join(pasta, nome))
            barrados = [m for e, r, m in erros if e == "venda"]
            self.assertEqual(barrados, [], nome)


class TriagemSegundaCamada(unittest.TestCase):
    def _cat(self, msg):
        return classificar({"nome": "Maria Souza", "email": "maria@gmail.com", "restaurante": "Cantina Sul", "mensagem": msg})[0]

    def test_lixo_de_frase_nova(self):
        casos = {"Meu painel não abre, fica carregando e nada.": "suporte",
                 "Sou designer e faço logotipos e identidade visual.": "fornecedor",
                 "Emagreça 10kg em 30 dias com nosso chá": "spam",
                 "hello world": "teste"}
        for msg, esperado in casos.items():
            self.assertEqual(self._cat(msg), esperado, msg)

    def test_cliente_real_que_parece_lixo_continua_venda(self):
        for msg in ("Sou dono de churrascaria e quero reduzir erro de pedido na cozinha.",
                    "Estou comparando sistemas para o delivery do meu negócio. Podemos conversar essa semana?",
                    "Já tenho um sistema, mas ele trava muito. Vocês são melhores? Quero conhecer.",
                    "Boa tarde, represento uma rede de franquias de açaí e queremos contratar o sistema para todas as lojas."):
            self.assertEqual(self._cat(msg), "venda", msg)


class PassoComIA(unittest.TestCase):
    """O passo de IA só pode tirar da venda com confiança alta; qualquer falha mantém a regra. Sem chave, nada roda."""
    def setUp(self):
        import tempfile, os
        from unittest import mock
        self.mock = mock
        self.tmp = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"TRIAGEM_IA_CACHE": os.path.join(self.tmp, "cache.json")})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_interpretar(self):
        import triagem_ia as ia
        self.assertEqual(ia.interpretar('{"categoria":"suporte","confianca":"alta"}')[0], "suporte")
        self.assertEqual(ia.interpretar('{"categoria":"suporte","confianca":"baixa"}')[0], "venda")
        self.assertEqual(ia.interpretar('{"categoria":"churrasco","confianca":"alta"}')[0], "venda")
        self.assertEqual(ia.interpretar("não sei")[0], "venda")
        self.assertEqual(ia.interpretar(None)[0], "venda")

    def test_pergunta_uma_vez_so_e_falha_nao_decide(self):
        import triagem_ia as ia
        chamadas = []
        def ok(msg):
            chamadas.append(msg); return '{"categoria":"fornecedor","confianca":"alta"}'
        self.assertEqual(ia.consultar("Vendo coifas", chamar=ok)[0], "fornecedor")
        self.assertEqual(ia.consultar("vendo   coifas", chamar=ok)[0], "fornecedor")
        self.assertEqual(len(chamadas), 1)
        def cai(msg): raise TimeoutError()
        self.assertIsNone(ia.consultar("outra mensagem", chamar=cai))
        self.assertIsNone(ia.consultar("outra mensagem", chamar=cai))

    def test_sem_chave_nao_faz_nada(self):
        import os, triagem_ia as ia
        with self.mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            self.assertFalse(ia.habilitada())
            self.assertIsNone(ia.consultar("qualquer coisa"))

    def test_chamada_http_manda_so_a_mensagem(self):
        import os, json, threading, triagem_ia as ia
        from http.server import BaseHTTPRequestHandler, HTTPServer
        visto = {}
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                visto["chave"] = self.headers.get("x-api-key")
                visto["corpo"] = self.rfile.read(int(self.headers["Content-Length"])).decode()
                b = json.dumps({"content": [{"type": "text", "text": '{"categoria":"spam","confianca":"alta"}'}]}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.handle_request, daemon=True).start()
        with self.mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "chave-de-teste"}), \
             self.mock.patch.object(ia, "URL", f"http://127.0.0.1:{srv.server_port}/v1/messages"):
            self.assertEqual(ia.consultar("ganhe dinheiro rápido")[0], "spam")
        srv.server_close()
        self.assertEqual(visto["chave"], "chave-de-teste")
        self.assertIn("ganhe dinheiro rápido", visto["corpo"])
        self.assertNotIn("maria@gmail.com", visto["corpo"])

    def test_reclassifica_so_pendentes_sem_tentativa(self):
        import os, sqlite3, triagem_ia as ia
        c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
        c.executescript("""CREATE TABLE pedidos_formulario(event_id TEXT, mensagem TEXT);
          CREATE TABLE triagem(event_id TEXT PRIMARY KEY, categoria TEXT, motivo TEXT, status_crm TEXT, deal_id INTEGER, tentativas INTEGER DEFAULT 0, atualizado_em TEXT);
          INSERT INTO pedidos_formulario VALUES('a','Meu painel está fora'),('b','Quero conhecer o sistema'),('c','Meu painel está fora');
          INSERT INTO triagem(event_id,categoria,status_crm,tentativas) VALUES('a','venda','pendente',0),('b','venda','pendente',0),('c','venda','pendente',2);""")
        def fake(msg):
            return '{"categoria":"suporte","confianca":"alta"}' if "painel" in msg else '{"categoria":"venda","confianca":"alta"}'
        with self.mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x"}), self.mock.patch.object(ia, "_chamar_api", fake):
            self.assertEqual(ia.reclassificar_pendentes(c), 1)
        est = {r["event_id"]: (r["categoria"], r["status_crm"]) for r in c.execute("select * from triagem")}
        self.assertEqual(est["a"], ("suporte", "nao_enviar"))
        self.assertEqual(est["b"], ("venda", "pendente"))
        self.assertEqual(est["c"], ("venda", "pendente"))      # já tentou o CRM: não mexe
