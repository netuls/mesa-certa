"""Painel web Mesa Certa. Somente leitura: não altera o CRM nem o banco original."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import json, sqlite3, datetime as dt, csv, io

BASE = Path(__file__).resolve().parent
DB = Path(__import__('os').environ.get('MESA_DB', BASE / 'mesa_certa.db'))
import os

HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', os.environ.get('PANEL_PORT', '10000')))
AS_OF = dt.datetime(2026, 10, 12, 8, 0, 0)  # referência exigida no enunciado
FORM_FIM_UTC = '2026-10-12T00:00:00Z'  # fim do lote do webhook (domingo 21h em Brasília)
STAGES = ['Novo', 'Contato', 'Reunião marcada', 'Reunião realizada', 'Perdido']

try:
    from horas_uteis import horas_uteis
    from triagem_ia import classificar_final as classificar
except ImportError:
    def horas_uteis(a, b):
        a = dt.datetime.strptime(a, '%Y-%m-%d %H:%M:%S') if isinstance(a, str) else a
        b = dt.datetime.strptime(b, '%Y-%m-%d %H:%M:%S') if isinstance(b, str) else b
        total = 0.0
        while a < b:
            if a.weekday() < 5 and 8 <= a.hour < 18:
                total += min((b-a).total_seconds(), 60) / 3600
            a += dt.timedelta(minutes=1)
        return total
    def classificar(e):
        s = ' '.join(str(e.get(k) or '') for k in ('nome','email','restaurante','mensagem')).lower()
        if any(x in s for x in ('teste','testando','asdf','@mesacerta.com.br')): return ('teste','marcador de teste')
        if any(x in s for x in ('esqueci minha senha','impressora','sou cliente e','problema no pagamento')): return ('suporte','pedido de suporte')
        if any(x in s for x in ('fornecedora','tráfego pago','preço de atacado','oferecemos')): return ('fornecedor','oferta de fornecedor')
        if any(x in s for x in ('bit.ly','ganhe dinheiro','renda extra')): return ('spam','conteúdo suspeito')
        return ('venda','pedido comercial')

def conn():
    if not DB.exists(): raise FileNotFoundError(f'Banco não encontrado: {DB}')
    c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    return c

def get_data():
    c = conn()
    try:
        deals = [dict(r) for r in c.execute('SELECT * FROM negocios_crm ORDER BY criado_em DESC')]
        forms = [dict(r) for r in c.execute('SELECT * FROM pedidos_formulario ORDER BY criado_em DESC')]
        stages_raw = {r['etapa']: r['n'] for r in c.execute('SELECT etapa, COUNT(*) n FROM negocios_crm GROUP BY etapa')}
        funnel = [{'etapa': s, 'quantidade': stages_raw.get(s, 0)} for s in STAGES]
        # Classificação dos pedidos do formulário para não cobrar o SDR por suporte/teste/fornecedor.
        category_by_email = {}
        for e in reversed(forms): category_by_email[(e.get('email') or '').strip().lower()] = classificar(e)[0]
        def category(d):
            email = (d.get('email') or '').strip().lower()
            return category_by_email.get(email, classificar({**d, 'mensagem': ''})[0])
        active = [d for d in deals if d.get('etapa') != 'Perdido']
        pending = []
        for d in deals:
            if d.get('origem') != 'Site' or d.get('etapa') != 'Novo' or d.get('primeiro_contato_em') or category(d) != 'venda': continue
            h = round(horas_uteis(d['criado_em'], AS_OF), 1)
            if h > 4:
                pending.append({**d, 'horas_uteis': h, 'categoria': category(d)})
        # SLA por SDR: apenas oportunidades de site criadas na janela da semana de referência.
        start, end = '2026-10-05 00:00:00', '2026-10-12 00:00:00'
        sdr = {}
        for d in deals:
            if d.get('origem') != 'Site' or not (start <= d['criado_em'] < end) or category(d) != 'venda': continue
            who = d.get('responsavel') or 'Sem responsável'
            x = sdr.setdefault(who, {'responsavel': who, 'no_prazo': 0, 'atrasados': 0, 'sem_retorno': 0, 'dentro_prazo': 0, 'total': 0})
            if d.get('primeiro_contato_em'):
                h = horas_uteis(d['criado_em'], d['primeiro_contato_em'])
                x['total'] += 1
                if h <= 4: x['no_prazo'] += 1
                else: x['atrasados'] += 1
            else:
                h = horas_uteis(d['criado_em'], AS_OF)
                if h > 4: x['sem_retorno'] += 1; x['total'] += 1
                else: x['dentro_prazo'] += 1
        sdr_list = sorted(sdr.values(), key=lambda x: x['responsavel'])
        for x in sdr_list:
            x['pct_no_prazo'] = round(x['no_prazo'] / x['total'] * 100) if x['total'] else None
        # Pedidos de demonstração da semana: pessoas distintas (pelo e-mail) com pedido de venda no formulário,
        # mais os negócios de venda do site criados depois que o formulário parou de valer (o lote vai até 12/10 00:00 UTC).
        def brt(s):
            return (dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ') - dt.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        mail = lambda x: (x.get('email') or '').strip().lower()
        form_semana = {mail(e) for e in forms if e.get('criado_em') and start <= brt(e['criado_em']) < end and classificar(e)[0] == 'venda'}
        so_crm = {mail(d) for d in deals if d.get('origem') == 'Site' and brt(FORM_FIM_UTC) <= d['criado_em'] < end
                  and category(d) == 'venda' and mail(d) not in form_semana}
        pedidos_demo = {'pessoas': len(form_semana | so_crm), 'do_formulario': len(form_semana), 'so_no_crm': len(so_crm)} if form_semana else None
        # Os dados do formulário fornecidos no banco cobrem 28/09 a 04/10 até que o lote do webhook seja importado.
        form_dates = [e['criado_em'] for e in forms if e.get('criado_em')]
        form_range = {'inicio': min(form_dates) if form_dates else None, 'fim': max(form_dates) if form_dates else None}
        counts = {}
        for e in forms: counts[classificar(e)[0]] = counts.get(classificar(e)[0], 0) + 1
        # Pessoas diferentes (pelo e-mail) entre os pedidos comerciais: a mesma pessoa pode ter enviado o formulário mais de uma vez.
        pessoas_venda = len({mail(e) for e in forms if classificar(e)[0] == 'venda'})
        return {
            'as_of': AS_OF.strftime('%d/%m/%Y %H:%M'), 'total': len(deals), 'ativos': len(active),
            'novos': stages_raw.get('Novo', 0), 'reunioes': stages_raw.get('Reunião marcada',0) + stages_raw.get('Reunião realizada',0),
            'perdidos': stages_raw.get('Perdido',0), 'pedidos_demo': pedidos_demo, 'funnel': funnel, 'sdr': sdr_list,
            'pending': sorted(pending, key=lambda x: x['horas_uteis'], reverse=True),
            'deals': deals, 'form_count': len(forms), 'form_range': form_range, 'form_categories': counts,
            'form_pessoas_venda': pessoas_venda,
            'source_warning': 'A base local do formulário cobre 28/09 a 04/10/2026. O indicador de 125 pessoas para 05–11/10 é a estimativa documentada em respostas.md e não foi recalculado a partir do lote de webhook desta semana.',
            'last_updated': max((d.get('atualizado_em') or '' for d in deals), default='')
        }
    finally: c.close()


HTML = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mesa Certa | Registro de contatos</title>
<style>
body{font-family:system-ui,Arial,sans-serif;background:#f4f6fa;color:#1a2540;margin:0;padding:24px}
main{max-width:900px;margin:auto;background:white;padding:24px;border-radius:16px;box-shadow:0 8px 28px #17243d0a}
h1{margin-top:0}p{color:#667085}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
label{display:block;font-weight:600;font-size:14px}input,select,textarea{width:100%;box-sizing:border-box;margin-top:6px;padding:10px;border:1px solid #ccd3df;border-radius:8px;font:inherit}
button{margin-top:16px;background:#4767f5;color:white;border:0;padding:11px 16px;border-radius:8px;font-weight:700;cursor:pointer}
table{border-collapse:collapse;width:100%;margin-top:18px}th,td{text-align:left;border-bottom:1px solid #e7ebf2;padding:9px;font-size:13px}
.notice{background:#eef2ff;padding:12px;border-radius:8px;margin:14px 0}.msg{margin-top:12px;font-weight:600}
</style></head><body><main>
<a href="/">← Voltar ao painel</a><h1>Registro de contatos realizados</h1>
<p>Registre quem realmente fez o contato. Essa informação fica separada do responsável pelo negócio e não altera o banco original do CRM.</p>
<div class="notice">Para registros antigos, não invente quem ligou. Cadastre apenas contatos que possam ser confirmados.</div>
<form id="f"><div class="grid">
<label>ID do negócio<input name="deal_id" type="number" min="1" required></label>
<label>Quem realizou o contato<input name="realizado_por" required placeholder="Nome do atendente"></label>
<label>Canal<select name="canal" required><option value="ligação">Ligação</option><option value="whatsapp">WhatsApp</option><option value="e-mail">E-mail</option></select></label>
<label>Data e hora<input name="realizado_em" type="datetime-local" required></label>
</div><label style="margin-top:14px">Observação (opcional)<textarea name="observacao" rows="2"></textarea></label>
<button type="submit">Salvar contato</button><div class="msg" id="msg" role="status"></div></form>
<h2>Contatos registrados</h2><div style="overflow:auto"><table><thead><tr><th>Negócio</th><th>Quem contatou</th><th>Canal</th><th>Data/hora</th><th>Observação</th></tr></thead><tbody id="rows"></tbody></table></div>
</main><script>
const $=x=>document.getElementById(x);
async function load(){const r=await fetch('/api/contatos');const d=await r.json();$('rows').innerHTML=d.contatos.map(x=>`<tr><td>${x.deal_id}</td><td>${esc(x.realizado_por)}</td><td>${esc(x.canal)}</td><td>${esc(x.realizado_em)}</td><td>${esc(x.observacao||'')}</td></tr>`).join('')||'<tr><td colspan="5">Nenhum contato registrado.</td></tr>'}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
$('f').addEventListener('submit',async e=>{e.preventDefault();const o=Object.fromEntries(new FormData(e.target));o.realizado_em=o.realizado_em.replace('T',' ')+':00';const r=await fetch('/api/contatos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)});const d=await r.json();$('msg').textContent=r.ok?'Contato salvo.':(d.error||'Não foi possível salvar.');if(r.ok){e.target.reset();load()}});
load();
</script></body></html>"""

HTML = r'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#101a2e"><title>Mesa Certa • Painel Comercial</title>
<style>
:root{--navy:#101a2e;--navy2:#17243d;--bg:#f4f6fa;--card:#fff;--ink:#1a2540;--muted:#75809a;--line:#e7ebf2;--blue:#4767f5;--cyan:#38bdf8;--green:#159b72;--orange:#d97706;--red:#d94f5c;--shadow:0 8px 28px #17243d0a}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}button,input,select{font:inherit}.app{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh}.sidebar{background:var(--navy);color:#fff;padding:26px 17px;display:flex;flex-direction:column;gap:28px}.brand{display:flex;gap:11px;align-items:center;padding:0 8px}.brand-icon{width:40px;height:40px;border-radius:13px;background:linear-gradient(135deg,#6c83ff,#3d57e8);display:grid;place-items:center;font-size:20px;font-weight:900}.brand b{font-size:17px;letter-spacing:-.4px}.brand small{display:block;color:#a8b4d0;font-size:11px;margin-top:3px}.nav-label{color:#7e8ba8;text-transform:uppercase;font-size:10px;font-weight:800;letter-spacing:1.3px;padding:0 12px;margin-bottom:7px}.nav{display:grid;gap:6px}.nav a{color:#aeb9d0;text-decoration:none;display:flex;align-items:center;gap:12px;padding:12px;border-radius:10px;font-size:13px;font-weight:600}.nav a.active,.nav a:hover{background:#263555;color:#fff}.nav .ico{width:20px;text-align:center;font-size:17px}.side-foot{margin-top:auto;background:#1a2945;border:1px solid #2a3b5d;padding:14px;border-radius:13px;color:#c3cce0;font-size:12px;line-height:1.5}.status-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#37c997;margin-right:7px}.main{padding:30px clamp(18px,3vw,42px);min-width:0}.topbar{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:27px}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:var(--blue);font-weight:800;margin-bottom:7px}.topbar h1{margin:0;font-size:clamp(23px,3vw,30px);letter-spacing:-1px}.sub{color:var(--muted);font-size:13px;margin-top:8px}.actions{display:flex;gap:10px;align-items:center}.btn{border:1px solid var(--line);background:#fff;border-radius:10px;padding:10px 14px;font-size:12px;font-weight:700;color:var(--ink);cursor:pointer}.btn.primary{background:var(--blue);color:#fff;border-color:var(--blue)}.btn:hover{filter:brightness(.98);transform:translateY(-1px)}.notice{display:flex;gap:12px;align-items:flex-start;background:#fff8e8;border:1px solid #f5dfad;color:#8a5a09;padding:13px 16px;border-radius:12px;font-size:12px;line-height:1.5;margin-bottom:22px}.notice strong{display:block;font-size:12px;margin-bottom:2px}.metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:15px;margin-bottom:19px}.metric{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:18px;box-shadow:var(--shadow);min-width:0}.metric-top{display:flex;align-items:center;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:650;gap:6px}.metric-icon{width:34px;height:34px;display:grid;place-items:center;border-radius:10px;background:#edf0ff;color:var(--blue);font-size:17px}.metric:nth-child(2) .metric-icon{background:#e8f8f2;color:var(--green)}.metric:nth-child(3) .metric-icon{background:#fff2df;color:var(--orange)}.metric:nth-child(4) .metric-icon{background:#ffebed;color:var(--red)}.metric-num{font-size:30px;font-weight:800;letter-spacing:-1.2px;margin:15px 0 4px}.metric-foot{font-size:11px;color:var(--muted)}.grid{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);gap:17px;margin-bottom:18px}.panel{background:#fff;border:1px solid var(--line);border-radius:15px;padding:20px;box-shadow:var(--shadow);min-width:0}.panel-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:20px}.panel h2{font-size:15px;margin:0;letter-spacing:-.25px}.panel-desc{font-size:11px;color:var(--muted);margin-top:5px}.pill{display:inline-flex;align-items:center;border-radius:7px;padding:5px 8px;font-size:10px;font-weight:800;background:#edf0ff;color:var(--blue);white-space:nowrap}.chart{display:grid;gap:15px}.barrow{display:grid;grid-template-columns:135px minmax(50px,1fr) 30px;align-items:center;gap:12px;font-size:12px}.barlabel{color:#56617a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.bartrack{height:10px;background:#f0f2f7;border-radius:99px;overflow:hidden}.barfill{height:100%;border-radius:99px;background:linear-gradient(90deg,#506cf4,#8294ff);min-width:2px}.barvalue{text-align:right;font-weight:800}.legend{display:flex;gap:12px;flex-wrap:wrap;margin-top:18px;color:var(--muted);font-size:10px}.legend span:before{content:'';display:inline-block;width:7px;height:7px;border-radius:2px;background:var(--blue);margin-right:5px}.sdr-list{display:grid;gap:14px}.sdr-row{border:1px solid #edf0f5;border-radius:11px;padding:12px}.sdr-top{display:flex;justify-content:space-between;gap:8px;align-items:center;font-size:12px;font-weight:750;margin-bottom:10px}.sdr-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.sdr-stats div{background:#f7f8fb;border-radius:8px;padding:8px}.sdr-stats b{display:block;font-size:15px}.sdr-stats small{display:block;color:var(--muted);font-size:10px;margin-top:3px}.progress{height:5px;background:#edf0f5;border-radius:9px;overflow:hidden;margin-top:10px}.progress span{height:100%;display:block;background:var(--green);border-radius:9px}.table-panel{padding:0;overflow:hidden}.table-panel .panel-head{padding:20px 20px 0}.table-controls{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.control{border:1px solid var(--line);border-radius:9px;background:#fff;padding:9px 11px;font-size:12px;color:var(--ink);outline:none}.control:focus{border-color:#a8b5ff;box-shadow:0 0 0 3px #4767f51a}.search{min-width:210px;flex:1}.table-wrap{overflow:auto;margin-top:15px}table{border-collapse:collapse;width:100%;white-space:nowrap;font-size:12px}thead{background:#f8f9fc;color:#7b849a;font-size:10px;text-transform:uppercase;letter-spacing:.7px}th{text-align:left;font-weight:800;padding:12px 18px}td{padding:14px 18px;border-top:1px solid #f0f2f6;color:#4c5872}td strong{color:#1b2741;font-weight:700}.tag{display:inline-block;border-radius:6px;padding:5px 8px;font-size:10px;font-weight:800}.tag.novo{background:#fff1d8;color:#a66400}.tag.contato{background:#e8efff;color:#3556cf}.tag.reuniao{background:#e3f8ef;color:#12835f}.tag.perdido{background:#ffeaec;color:#c03b4a}.tag.atraso{background:#ffeaec;color:#c03b4a}.tag.ok{background:#e3f8ef;color:#12835f}.empty{text-align:center;padding:30px;color:var(--muted)}.table-foot{display:flex;justify-content:space-between;align-items:center;padding:13px 20px;color:var(--muted);font-size:11px;border-top:1px solid var(--line)}.lower{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:17px;margin-top:18px}.category-list{display:grid;gap:13px}.catrow{display:grid;grid-template-columns:90px 1fr 25px;gap:10px;align-items:center;font-size:12px}.catbar{height:8px;background:#f0f2f7;border-radius:8px;overflow:hidden}.catbar span{display:block;height:100%;border-radius:8px;background:#7b8cff}.small-note{font-size:11px;color:var(--muted);line-height:1.55;margin-top:15px}.footer{text-align:center;font-size:10px;color:#929bb0;padding:25px 0 5px}.toast{position:fixed;bottom:20px;right:20px;background:#17243d;color:#fff;border-radius:10px;padding:12px 16px;font-size:12px;box-shadow:0 10px 30px #101a2e30;display:none}.mobile-menu{display:none}
@media(max-width:1100px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.sdr-list{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:760px){.app{grid-template-columns:1fr}.sidebar{display:none}.main{padding:20px 14px}.topbar{align-items:flex-start}.actions .btn:not(.primary){display:none}.metrics{gap:9px}.metric{padding:14px}.metric-num{font-size:25px}.metric-top{font-size:11px}.metric-icon{width:29px;height:29px}.sdr-list{grid-template-columns:1fr}.lower{grid-template-columns:1fr}.barrow{grid-template-columns:112px minmax(30px,1fr) 25px;gap:7px}.panel{padding:15px}.table-panel{padding:0}.table-panel .panel-head{padding:16px 15px 0}.table-foot{padding:12px 15px}.search{min-width:100%}.sub{max-width:280px;line-height:1.5}.topbar h1{font-size:23px}}
</style></head><body><div class="app">
<aside class="sidebar"><div class="brand"><div class="brand-icon">M</div><div><b>Mesa Certa</b><small>Inteligência comercial</small></div></div><div><div class="nav-label">Workspace</div><nav class="nav"><a class="active" href="#visao"><span class="ico">▦</span>Visão geral</a><a href="#funil"><span class="ico">◫</span>Funil comercial</a><a href="#sla"><span class="ico">◷</span>Prazo de atendimento</a><a href="#pendencias"><span class="ico">☷</span>Fila de pendências</a><a href="#dados"><span class="ico">⇄</span>Conferência de dados</a></nav></div><div class="side-foot"><span class="status-dot"></span><b>Banco conectado</b><br>Modo de leitura: seguro<br><span style="color:#8391ad">Referência: 12/10/2026 às 08h</span></div></aside>
<main class="main"><header class="topbar" id="visao"><div><div class="eyebrow">Resumo executivo</div><h1>Visão geral comercial</h1><div class="sub">Acompanhe o funil, os retornos e os pedidos que precisam de atenção.</div></div><div class="actions"><button class="btn" id="exportBtn">↓ Exportar CSV</button><button class="btn primary" id="refreshBtn">↻ Atualizar dados</button></div></header>
<div class="notice" id="dataNotice"><span style="font-size:18px">⚠</span><div><strong>Conferência da semana</strong><span id="noticeText">Carregando a cobertura dos dados...</span></div></div>
<section class="metrics"><article class="metric"><div class="metric-top">Negócios no CRM <span class="metric-icon">▦</span></div><div class="metric-num" id="mTotal">—</div><div class="metric-foot">Todos os negócios registrados</div></article><article class="metric"><div class="metric-top">Pessoas com pedido de demo <span class="metric-icon">✉</span></div><div class="metric-num" id="mWeeklyRequests">125</div><div class="metric-foot">Estimativa documentada · 05–11/10</div></article><article class="metric"><div class="metric-top">Em andamento <span class="metric-icon">↗</span></div><div class="metric-num" id="mActive">—</div><div class="metric-foot">Exclui negócios perdidos</div></article><article class="metric"><div class="metric-top">Sem retorno no prazo <span class="metric-icon">◷</span></div><div class="metric-num" id="mPending">—</div><div class="metric-foot">Pedidos de venda com mais de 4h úteis</div></article><article class="metric"><div class="metric-top">Reuniões no funil <span class="metric-icon">▤</span></div><div class="metric-num" id="mMeetings">—</div><div class="metric-foot">Marcadas ou realizadas</div></article></section>
<section class="grid"><article class="panel" id="funil"><div class="panel-head"><div><h2>Funil comercial</h2><div class="panel-desc">Quantidade de negócios em cada etapa atual do CRM</div></div><span class="pill">ESTADO ATUAL</span></div><div class="chart" id="funnelChart"></div><div class="legend"><span>Negócios por etapa</span></div></article><article class="panel" id="sla"><div class="panel-head"><div><h2>Prazo de atendimento por SDR</h2><div class="panel-desc">Pedidos de venda criados de 05 a 11/10</div></div><span class="pill">SLA 4H ÚTEIS</span></div><div class="sdr-list" id="sdrList"></div><div class="small-note">O cálculo considera segunda a sexta, das 08h às 18h. Testes, suporte e fornecedores são excluídos. Atrasos são calculados com os registros disponíveis.</div></article></section>
<section class="panel table-panel" id="pendencias"><div class="panel-head"><div><h2>Fila que precisa de atenção</h2><div class="panel-desc">Oportunidades de venda sem primeiro contato e com prazo vencido na data de referência.</div><div class="table-controls"><input class="control search" id="searchPending" placeholder="Buscar nome, restaurante ou responsável..."><select class="control" id="pendingOwner"><option value="">Todos os responsáveis</option></select></div></div><span class="pill" id="pendingPill">0 pendências</span></div><div class="table-wrap"><table><thead><tr><th>Contato / restaurante</th><th>Responsável</th><th>Entrada</th><th>Horas úteis</th><th>Status</th></tr></thead><tbody id="pendingBody"></tbody></table></div><div class="table-foot"><span id="pendingCount">Carregando...</span><span>Referência: 12/10/2026, 08h</span></div></section>
<section class="lower"><article class="panel" id="dados"><div class="panel-head"><div><h2>Pedidos recebidos pelo formulário</h2><div class="panel-desc">Cobertura da base local, antes de importar o lote adicional</div></div><span class="pill" id="formPill">— registros</span></div><div class="category-list" id="categoryList"></div><div class="small-note" id="formRange"></div></article><article class="panel"><div class="panel-head"><div><h2>Negócios recentes</h2><div class="panel-desc">Últimas atualizações encontradas no CRM</div></div><span class="pill">CRM</span></div><div class="table-wrap" style="margin-top:0"><table><thead><tr><th>Restaurante</th><th>Etapa</th><th>Responsável</th></tr></thead><tbody id="recentBody"></tbody></table></div></article></section>
<section class="panel" style="margin-top:18px" id="todos"><div class="panel-head"><div><h2>Todos os negócios</h2><div class="panel-desc">Pesquise e filtre os registros carregados do banco local.</div><div class="table-controls"><input class="control search" id="searchDeals" placeholder="Buscar nome, e-mail ou restaurante..."><select class="control" id="stageFilter"><option value="">Todas as etapas</option><option>Novo</option><option>Contato</option><option>Reunião marcada</option><option>Reunião realizada</option><option>Perdido</option></select><select class="control" id="ownerFilter"><option value="">Todos os responsáveis</option></select></div></div><span class="pill" id="dealsPill">— negócios</span></div><div class="table-wrap"><table><thead><tr><th>Contato</th><th>Restaurante</th><th>Etapa</th><th>Responsável</th><th>Origem</th><th>Última atualização</th></tr></thead><tbody id="dealsBody"></tbody></table></div><div class="table-foot"><span id="dealsCount">—</span><span>Os filtros atuam nos dados carregados.</span></div></section>
<div class="footer">Mesa Certa · Painel de apoio à decisão · Dados locais em modo de leitura</div></main></div><div class="toast" id="toast"></div>
<script>
let DATA=null;const $=id=>document.getElementById(id);const fmt=n=>Number(n||0).toLocaleString('pt-BR');const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function toast(s){$('toast').textContent=s;$('toast').style.display='block';setTimeout(()=>$('toast').style.display='none',3000)}
function stageClass(s){if(s==='Novo')return'novo';if(s==='Contato')return'contato';if(s.includes('Reunião'))return'reuniao';if(s==='Perdido')return'perdido';return''}
async function load(){ $('refreshBtn').disabled=true;$('refreshBtn').textContent='Carregando…';try{const r=await fetch('/api/dashboard');if(!r.ok)throw new Error(await r.text());DATA=await r.json();render();toast('Dados atualizados com sucesso.')}catch(e){toast('Não foi possível carregar os dados: '+e.message)}finally{$('refreshBtn').disabled=false;$('refreshBtn').textContent='↻ Atualizar dados'}}
function render(){const d=DATA;$('mTotal').textContent=fmt(d.total);$('mActive').textContent=fmt(d.ativos);$('mPending').textContent=fmt(d.pending.length);$('mMeetings').textContent=fmt(d.reunioes);$('noticeText').textContent=d.source_warning;
const max=Math.max(1,...d.funnel.map(x=>x.quantidade));$('funnelChart').innerHTML=d.funnel.map(x=>`<div class="barrow"><div class="barlabel">${escapeHtml(x.etapa)}</div><div class="bartrack"><div class="barfill" style="width:${x.quantidade/max*100}%"></div></div><div class="barvalue">${fmt(x.quantidade)}</div></div>`).join('');
$('sdrList').innerHTML=d.sdr.length?d.sdr.map(x=>`<div class="sdr-row"><div class="sdr-top"><span>${escapeHtml(x.responsavel)}</span><span class="tag ${x.atrasados+x.sem_retorno?'atraso':'ok'}">${x.pct_no_prazo==null?'Sem base':x.pct_no_prazo+'% no prazo'}</span></div><div class="sdr-stats"><div><b>${fmt(x.no_prazo)}</b><small>No prazo</small></div><div><b>${fmt(x.atrasados)}</b><small>Atrasados</small></div><div><b>${fmt(x.sem_retorno)}</b><small>Sem retorno</small></div></div><div class="progress"><span style="width:${x.pct_no_prazo||0}%"></span></div></div>`).join(''):'<div class="empty">Não há negócios nessa janela de datas.</div>';
const owners=[...new Set(d.deals.map(x=>x.responsavel).filter(Boolean))].sort();for(const id of ['pendingOwner','ownerFilter']){const el=$(id);const current=el.value;el.innerHTML='<option value="">'+(id==='pendingOwner'?'Todos os responsáveis':'Todos os responsáveis')+'</option>'+owners.map(x=>`<option value="${escapeHtml(x)}">${escapeHtml(x)}</option>`).join('');el.value=current}
$('pendingPill').textContent=fmt(d.pending.length)+' pendências';renderPending();$('formPill').textContent=fmt(d.form_count)+' registros';const catNames={venda:'Oportunidades',teste:'Testes',suporte:'Suporte',fornecedor:'Fornecedores',spam:'Spam'};const maxCat=Math.max(1,...Object.values(d.form_categories));$('categoryList').innerHTML=Object.entries(d.form_categories).map(([k,v])=>`<div class="catrow"><span>${catNames[k]||k}</span><div class="catbar"><span style="width:${v/maxCat*100}%"></span></div><b>${fmt(v)}</b></div>`).join('');$('formRange').textContent='Período registrado: '+(d.form_range.inicio||'—')+' até '+(d.form_range.fim||'—')+'. As datas do formulário são armazenadas em UTC.';
$('recentBody').innerHTML=d.deals.slice(0,5).map(x=>`<tr><td><strong>${escapeHtml(x.restaurante||'—')}</strong></td><td><span class="tag ${stageClass(x.etapa)}">${escapeHtml(x.etapa)}</span></td><td>${escapeHtml(x.responsavel||'—')}</td></tr>`).join('');renderDeals();}
function renderPending(){const q=$('searchPending').value.toLowerCase(),owner=$('pendingOwner').value;const rows=DATA.pending.filter(x=>(!owner||x.responsavel===owner)&&[x.nome,x.restaurante,x.responsavel,x.email].join(' ').toLowerCase().includes(q));$('pendingBody').innerHTML=rows.length?rows.slice(0,100).map(x=>`<tr><td><strong>${escapeHtml(x.nome||'—')}</strong><br><span style="color:#8992a7;font-size:10px">${escapeHtml(x.restaurante||'—')}</span></td><td>${escapeHtml(x.responsavel||'Sem responsável')}</td><td>${escapeHtml(x.criado_em)}</td><td><strong>${String(x.horas_uteis).replace('.',',')}h</strong></td><td><span class="tag atraso">Atrasado</span></td></tr>`).join(''):'<tr><td colspan="5" class="empty">Nenhuma pendência corresponde aos filtros.</td></tr>';$('pendingCount').textContent=`Exibindo ${rows.length} de ${DATA.pending.length} pendências`}
function renderDeals(){const q=$('searchDeals').value.toLowerCase(),stage=$('stageFilter').value,owner=$('ownerFilter').value;const rows=DATA.deals.filter(x=>(!stage||x.etapa===stage)&&(!owner||x.responsavel===owner)&&[x.nome,x.email,x.restaurante,x.telefone].join(' ').toLowerCase().includes(q));$('dealsBody').innerHTML=rows.length?rows.slice(0,200).map(x=>`<tr><td><strong>${escapeHtml(x.nome||'—')}</strong><br><span style="color:#8992a7;font-size:10px">${escapeHtml(x.email||'')}</span></td><td>${escapeHtml(x.restaurante||'—')}</td><td><span class="tag ${stageClass(x.etapa)}">${escapeHtml(x.etapa)}</span></td><td>${escapeHtml(x.responsavel||'—')}</td><td>${escapeHtml(x.origem||'—')}</td><td>${escapeHtml(x.atualizado_em||'—')}</td></tr>`).join(''):'<tr><td colspan="6" class="empty">Nenhum negócio encontrado.</td></tr>';$('dealsPill').textContent=fmt(rows.length)+' negócios';$('dealsCount').textContent=`Exibindo ${Math.min(rows.length,200)} de ${rows.length} resultados${rows.length>200?' (limite visual de 200 linhas)':''}`}
['searchPending','pendingOwner'].forEach(id=>$(id).addEventListener(id==='pendingOwner'?'change':'input',renderPending));['searchDeals','stageFilter','ownerFilter'].forEach(id=>$(id).addEventListener(id==='searchDeals'?'input':'change',renderDeals));$('refreshBtn').addEventListener('click',load);$('exportBtn').addEventListener('click',()=>{if(!DATA)return;const rows=[['deal_id','nome','email','restaurante','etapa','responsavel','origem','criado_em','atualizado_em'],...DATA.deals.map(x=>[x.deal_id,x.nome,x.email,x.restaurante,x.etapa,x.responsavel,x.origem,x.criado_em,x.atualizado_em])];const csv=rows.map(r=>r.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(';')).join('\r\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));a.download='mesa-certa-negocios.csv';a.click();URL.revokeObjectURL(a.href);toast('Arquivo CSV preparado.')});load();
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, code, body, ctype):
        body = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ('/', '/index.html'):
            # Prefere o index.html externo para facilitar edicoes visuais; usa o HTML embutido como fallback.
            index_file = BASE / 'index.html'
            page = index_file.read_text(encoding='utf-8') if index_file.exists() else HTML
            return self.send_bytes(200, page, 'text/html; charset=utf-8')
        if path == '/api/dashboard':
            try: return self.send_bytes(200, json.dumps(get_data(), ensure_ascii=False).encode(), 'application/json; charset=utf-8')
            except Exception as e: return self.send_bytes(500, json.dumps({'error':str(e)},ensure_ascii=False), 'application/json; charset=utf-8')
        if path == '/health': return self.send_bytes(200, json.dumps({'ok':DB.exists(),'database':DB.name}), 'application/json')
        return self.send_bytes(404, 'Não encontrado', 'text/plain; charset=utf-8')
    def do_POST(self):
        return self.send_bytes(404, 'Não encontrado', 'text/plain; charset=utf-8')
    def log_message(self, fmt, *args): print('[%s] %s' % (self.log_date_time_string(), fmt % args))

if __name__ == '__main__':
    print(f'Mesa Certa iniciado na porta {PORT}', flush=True)
    print(f'Banco em modo somente leitura: {DB}', flush=True)

    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
        print('Servidor pronto para receber conexões.', flush=True)
        server.serve_forever()
    except Exception as e:
        print(f'Erro ao iniciar o servidor: {e}', flush=True)
        raise
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
