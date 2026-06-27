from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from modelos.database import get_db
from modelos.locacao import Locacao
from modelos.cliente import Cliente
from modelos.veiculo import Veiculo
from datetime import datetime

router = APIRouter(prefix="/contratos", tags=["Contratos"])

MESES_PT = {1:"janeiro",2:"fevereiro",3:"março",4:"abril",5:"maio",6:"junho",7:"julho",8:"agosto",9:"setembro",10:"outubro",11:"novembro",12:"dezembro"}

def formatar_data_extenso(d):
    if not d: return "___"
    try:
        if isinstance(d, str): d = datetime.strptime(d[:10], "%Y-%m-%d")
        return f"{d.day} de {MESES_PT[d.month]} de {d.year}"
    except: return str(d)

def formatar_data(d):
    if not d: return "___"
    try:
        if isinstance(d, str): return d[:10].split("-")[-1]+"/"+d[5:7]+"/"+d[:4]
        return d.strftime("%d/%m/%Y")
    except: return str(d)

@router.get("/{locacao_id}", response_class=HTMLResponse)
def gerar_contrato(locacao_id: int, db: Session = Depends(get_db)):
    loc = db.query(Locacao).filter(Locacao.id == locacao_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Locacao nao encontrada")
    cli = db.query(Cliente).filter(Cliente.id == loc.cliente_id).first()
    vei = db.query(Veiculo).filter(Veiculo.id == loc.veiculo_id).first()
    if not cli or not vei:
        raise HTTPException(status_code=404, detail="Cliente ou veiculo nao encontrado")

    periodo = "DIARIO" if loc.periodo == "diario" else "SEMANAL" if loc.periodo == "semanal" else "MENSAL"
    valor_fmt = f"R$ {loc.valor_periodo:.2f}".replace(".",",")
    data_inicio = formatar_data_extenso(loc.data_inicio)
    data_fim = formatar_data_extenso(loc.data_fim)
    data_hoje = formatar_data_extenso(datetime.now())

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Contrato de Locacao #{locacao_id}</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 13px; color: #000; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
  h1 {{ text-align: center; font-size: 16px; margin-bottom: 20px; }}
  h2 {{ font-size: 13px; margin-top: 20px; }}
  p {{ margin: 8px 0; text-align: justify; }}
  .campo {{ font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  table th, table td {{ border: 1px solid #000; padding: 6px 10px; font-size: 12px; }}
  table th {{ background: #f0f0f0; }}
  .linha {{ border-top: 1px solid #000; width: 300px; margin: 40px auto 4px; }}
  .centro {{ text-align: center; }}
  @media print {{ .no-print {{ display: none; }} }}
  .btn-assinar {{ background: #28a745; color: #fff; border: none; padding: 12px 32px; font-size: 15px; font-weight: 800; border-radius: 8px; cursor: pointer; display: block; margin: 30px auto; }}
  .btn-imprimir {{ background: #007bff; color: #fff; border: none; padding: 10px 24px; font-size: 13px; font-weight: 700; border-radius: 8px; cursor: pointer; display: block; margin: 10px auto; }}
  .assinatura-box {{ background: #f9f9f9; border: 2px dashed #ccc; border-radius: 10px; padding: 24px; margin: 20px 0; text-align: center; display: none; }}
  .assinatura-box input {{ width: 80%; padding: 10px; font-size: 14px; margin: 8px auto; border: 1px solid #ccc; border-radius: 6px; display: block; }}
  .confirmado {{ background: #e8ffe8; border: 2px solid #2a2; border-radius: 10px; padding: 20px; text-align: center; display: none; }}
</style>
</head>
<body>

<div class="no-print" style="text-align:center;margin-bottom:20px">
  <button class="btn-imprimir" onclick="window.print()">Imprimir / Salvar PDF</button>
</div>

<h1>CONTRATO DE LOCACAO DE VEICULOS</h1>

<p><strong>LOCADOR:</strong> LOCA MAIS CAR LOCACAO DE VEICULOS LTDA, CNPJ 57.800.204/0001-24, Avenida Rodrigues Alves, 180, Bairro Rosario, Sao Joao da Boa Vista - SP, CEP 13870-320.</p>

<p><strong>LOCATARIO:</strong> <span class="campo">{cli.nome or "___"}</span><br>
CPF: <span class="campo">{cli.cpf or "___"}</span><br>
Endereco: <span class="campo">{cli.endereco or "___"}</span><br>
Bairro: <span class="campo">{cli.bairro or "___"}</span><br>
Cidade: <span class="campo">{cli.cidade or "___"}</span><br>
Estado: <span class="campo">{cli.estado or "___"}</span><br>
CEP: <span class="campo">{cli.cep or "___"}</span><br>
Estado Civil: <span class="campo">{cli.estado_civil or "___"}</span></p>

<p><strong>CONDUTOR(ES) AUTORIZADO(S):</strong> {cli.nome or "___"}, CPF {cli.cpf or "___"}.</p>

<h2>CLAUSULA 1 - DO OBJETO E FINALIDADE</h2>
<p><strong>1.1.</strong> O presente contrato tem por objeto a locacao de veiculo de propriedade do <strong>LOCADOR</strong> ao <strong>LOCATARIO</strong>, para utilizacao em atividades licitas, podendo ser empregado no transporte privado individual de passageiros por meio de plataformas digitais (ex.: Uber, 99), ou em quaisquer outras atividades permitidas por lei.</p>
<p><strong>1.2.</strong> O veiculo objeto da presente locacao possui as seguintes caracteristicas:</p>
<ul>
  <li><strong>Marca/Modelo:</strong> {vei.marca or "___"} {vei.modelo or "___"}</li>
  <li><strong>Ano/Modelo:</strong> {vei.ano or "___"}</li>
  <li><strong>Placa:</strong> {vei.placa or "___"}</li>
  <li><strong>Chassi:</strong> {vei.chassi or "___"}</li>
  <li><strong>Cor:</strong> {vei.cor or "___"}</li>
  <li><strong>RENAVAM:</strong> {vei.renavam or "___"}</li>
  <li><strong>Quilometragem na entrega:</strong> {int(vei.quilometragem or 0):,} km</li>
</ul>
<p><strong>1.3.</strong> O <strong>LOCATARIO</strong> declara ter recebido o veiculo em perfeitas condicoes de uso, conservacao, funcionamento e limpeza, conforme verificado em inspecao previa e detalhado no Termo de Vistoria (Anexo I).</p>

<h2>CLAUSULA 2 - DA NATUREZA DO CONTRATO</h2>
<p><strong>2.1.</strong> O presente instrumento e um contrato de locacao de bem movel, de natureza estritamente civil, regido pelos artigos 565 e seguintes do Codigo Civil, nao se configurando como contrato de trabalho.</p>
<p><strong>2.2.</strong> O <strong>LOCATARIO</strong> possui total autonomia para definir seus horarios de trabalho, locais, frequencia e aceitacao de corridas.</p>

<h2>CLAUSULA 3 - DO PRAZO</h2>
<p><strong>3.1.</strong> O prazo da locacao tem inicio em <span class="campo">{data_inicio}</span> e termino em <span class="campo">{data_fim}</span>.</p>
<p><strong>3.2.</strong> Caso o <strong>LOCATARIO</strong> deseje prorrogar o contrato, devera notificar o <strong>LOCADOR</strong> com antecedencia minima de 30 dias do vencimento.</p>

<h2>CLAUSULA 4 - DO VALOR, PAGAMENTO E QUILOMETRAGEM</h2>
<p><strong>4.1.</strong> O valor da locacao e de: <span class="campo">{periodo} - {valor_fmt}</span><br>
FORMA DE PAGAMENTO: PIX<br>
PIX - 57800204000100 - CNPJ</p>
<p><strong>4.2.</strong> O valor da locacao da direito ao <strong>LOCATARIO</strong> a uma franquia de 8.000 (oito mil) quilometros por mes.</p>
<p><strong>4.3.</strong> A quilometragem excedente sera cobrada a parte, no valor de R$ 0,50 (cinquenta centavos) por quilometro rodado.</p>
<p><strong>4.4.</strong> O nao pagamento do aluguel na data estipulada implicara em multa de 10% sobre o valor devido, acrescida de juros de mora de 1% ao mes.</p>
<p><strong>4.5.</strong> O atraso no pagamento por periodo superior a 2 (dois) dias autoriza o <strong>LOCADOR</strong> a promover o bloqueio do veiculo por sistema de rastreamento.</p>

<h2>CLAUSULA 5 - DAS OBRIGACOES DO LOCADOR</h2>
<p><strong>5.1.</strong> Entregar o veiculo ao <strong>LOCATARIO</strong> em perfeitas condicoes de uso e com a documentacao regular.</p>
<p><strong>5.2.</strong> Manter o seguro do veiculo vigente durante toda a vigencia contratual.</p>
<p><strong>5.3.</strong> Realizar e custear as manutencoes preventivas decorrentes do plano de revisoes do fabricante.</p>

<h2>CLAUSULA 6 - DOS DEVERES E PROIBICOES DO LOCATARIO</h2>
<p><strong>6.1.</strong> O <strong>LOCATARIO</strong> compromete-se a conduzir o veiculo com o maximo zelo, prudencia e diligencia, respeitando o Codigo de Transito Brasileiro.</p>
<p><strong>6.2.</strong> E terminantemente proibido: dirigir sob influencia de alcool; praticar direcao perigosa; utilizar o veiculo para atos ilicitos; fumar no interior do veiculo; ceder ou emprestar o veiculo a terceiros.</p>

<h2>CLAUSULA 7 - DAS MULTAS DE TRANSITO</h2>
<p><strong>7.1.</strong> O <strong>LOCATARIO</strong> e o unico e exclusivo responsavel por todas as multas e infracoes de transito ocorridas durante a vigencia do contrato.</p>

<h2>CLAUSULA 8 - DOS SINISTROS, DANOS E SEGURO</h2>
<p><strong>8.1.</strong> Em caso de acidente, roubo, furto ou incendio, o <strong>LOCATARIO</strong> devera comunicar o <strong>LOCADOR</strong> imediatamente ou em no maximo 1 hora apos o conhecimento do fato.</p>
<p><strong>8.2.</strong> O <strong>LOCATARIO</strong> sera responsavel pelo pagamento da franquia do seguro, no valor de 6% do valor do veiculo constante na Tabela FIPE.</p>

<h2>CLAUSULA 9 - DA MANUTENCAO PREVENTIVA</h2>
<p><strong>9.1.</strong> O <strong>LOCATARIO</strong> obriga-se a apresentar o veiculo para a realizacao das manutencoes preventivas periodicas conforme o plano de revisoes do fabricante.</p>

<h2>CLAUSULA 10 - DA HABILITACAO</h2>
<p><strong>10.1.</strong> O <strong>LOCATARIO</strong> declara possuir Carteira Nacional de Habilitacao (CNH) valida, na categoria exigida pela legislacao brasileira.</p>

<h2>CLAUSULA 11 - DO RASTREAMENTO E BLOQUEIO</h2>
<p><strong>11.1.</strong> O <strong>LOCATARIO</strong> declara estar ciente e de acordo que o veiculo possui sistema de rastreamento e monitoramento.</p>

<h2>CLAUSULA 12 - DA RESCISAO</h2>
<p><strong>12.1.</strong> A violacao de qualquer clausula deste contrato sera considerada falta grave e quebra contratual, autorizando o <strong>LOCADOR</strong> a rescindir o contrato de pleno direito.</p>
<p><strong>12.2.</strong> Em caso de rescisao, o <strong>LOCATARIO</strong> devera devolver o veiculo imediatamente, sob pena de multa diaria de R$ 250,00.</p>

<h2>CLAUSULA 13 - DA PRIVACIDADE E PROTECAO DE DADOS (LGPD)</h2>
<p><strong>13.1.</strong> O <strong>LOCATARIO</strong> declara ciencia e consente que o <strong>LOCADOR</strong> realize o tratamento de seus dados pessoais e dados de geolocalizacao do veiculo, nos termos da LGPD.</p>

<h2>CLAUSULA 14 - DO FORO</h2>
<p><strong>14.1.</strong> Fica eleito o foro da comarca de Sao Joao da Boa Vista, Estado de Sao Paulo, para dirimir quaisquer litigios decorrentes deste contrato.</p>

<p>E, por estarem justas e contratadas, as partes assinam o presente instrumento em 2 (duas) vias de igual teor e forma.</p>
<p>Sao Joao da Boa Vista, <span class="campo">{data_hoje}</span></p>

<div style="margin-top:60px">
  <div class="centro">
    <div class="linha"></div>
    <p>LOCA MAIS CAR LOCACAO DE VEICULOS LTDA</p>
  </div>
  <div class="centro" style="margin-top:40px">
    <div class="linha"></div>
    <p><strong>{cli.nome or "LOCATARIO"}</strong> (LOCATARIO)</p>
  </div>
</div>

<p style="margin-top:40px"><strong>Testemunhas:</strong></p>
<div style="display:flex;gap:40px;margin-top:20px">
  <div>
    <div class="linha" style="margin:40px 0 4px 0;width:250px"></div>
    <p>Nome: _________________________ CPF: _____________</p>
  </div>
  <div>
    <div class="linha" style="margin:40px 0 4px 0;width:250px"></div>
    <p>Nome: _________________________ CPF: _____________</p>
  </div>
</div>

<h2 style="margin-top:40px;text-align:center">APENDICE - TERMO DE VISTORIA DE ENTREGA E DEVOLUCAO</h2>
<table>
  <thead>
    <tr><th>Item</th><th>Condicao</th><th>Observacoes</th></tr>
  </thead>
  <tbody>
    {"".join([f'<tr><td>{item}</td><td><label><input type="radio" name="item_{i}" value="sim"> Sim</label> &nbsp; <label><input type="radio" name="item_{i}" value="nao"> Nao</label></td><td><input type="text" style="width:100%;border:none;border-bottom:1px solid #ccc"></td></tr>' for i,item in enumerate(["Pneus","Estepe","Macaco/Chave de Roda","Vidros/Parabrisa","Retrovisores","Faróis/Lanternas","Banco dianteiro/traseiro","Estofamento interno","Painel de instrumentos","Ar-condicionado","Radio/Multimidia","Documentos do veiculo","Chave reserva","Carroceria/Lataria"])])}
  </tbody>
</table>

<div style="margin-top:40px;display:flex;justify-content:space-between">
  <div><div class="linha" style="width:250px;margin:40px 0 4px 0"></div><p>Assinatura LOCADORA</p></div>
  <div><div class="linha" style="width:250px;margin:40px 0 4px 0"></div><p>Assinatura LOCATARIO</p></div>
</div>

<div class="no-print" style="margin-top:40px;border-top:2px solid #ccc;padding-top:20px">
  <h2 style="text-align:center">Assinatura Digital</h2>
  <div id="area-assinar">
    <button class="btn-assinar" onclick="document.getElementById('area-assinar').style.display='none';document.getElementById('form-assinar').style.display='block'">Clique aqui para assinar este contrato</button>
  </div>
  <div class="assinatura-box" id="form-assinar">
    <p><strong>Para assinar, confirme seus dados:</strong></p>
    <input type="text" id="ass-nome" placeholder="Digite seu nome completo"/>
    <input type="text" id="ass-cpf" placeholder="Digite seu CPF (000.000.000-00)"/>
    <button class="btn-assinar" onclick="assinarContrato()">Confirmar Assinatura</button>
    <p style="font-size:11px;color:#666;margin-top:10px">Ao clicar em confirmar, voce declara ter lido e concordado com todos os termos deste contrato.</p>
  </div>
  <div class="confirmado" id="confirmado">
    <h2>Contrato Assinado!</h2>
    <p id="msg-confirmado"></p>
    <p style="font-size:12px;color:#666">Data e hora: <span id="data-assinatura"></span></p>
  </div>
</div>

<script>
async function assinarContrato() {{
  const nome = document.getElementById('ass-nome').value.trim();
  const cpf = document.getElementById('ass-cpf').value.trim();
  if(!nome || !cpf) {{ alert('Preencha nome e CPF para assinar.'); return; }}
  try {{
    const res = await fetch('/contratos/{locacao_id}/assinar', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{nome, cpf}})
    }});
    if(res.ok) {{
      document.getElementById('form-assinar').style.display = 'none';
      document.getElementById('confirmado').style.display = 'block';
      document.getElementById('msg-confirmado').textContent = nome + ' assinou este contrato digitalmente.';
      document.getElementById('data-assinatura').textContent = new Date().toLocaleString('pt-BR');
    }} else {{
      alert('Erro ao registrar assinatura. Tente novamente.');
    }}
  }} catch(e) {{
    alert('Erro de conexao. Tente novamente.');
  }}
}}
</script>
</body>
</html>"""
    return HTMLResponse(content=html)

@router.post("/{locacao_id}/assinar")
def assinar_contrato(locacao_id: int, dados: dict, db: Session = Depends(get_db)):
    loc = db.query(Locacao).filter(Locacao.id == locacao_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Locacao nao encontrada")
    from datetime import datetime
    loc.contrato_assinado = True
    loc.contrato_assinado_nome = dados.get("nome")
    loc.contrato_assinado_cpf = dados.get("cpf")
    loc.contrato_assinado_em = datetime.now()
    db.commit()
    return {"mensagem": "Contrato assinado com sucesso!"}
