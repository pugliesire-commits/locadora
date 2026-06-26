from fastapi import APIRouter, Depends, HTTPException
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
    return f"{d.day} de {MESES_PT[d.month]} de {d.year}"

def formatar_data(d):
    if not d: return "___"
    return d.strftime("%d/%m/%Y")

@router.get("/{locacao_id}")
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
  .assinatura {{ margin-top: 60px; }}
  .linha {{ border-top: 1px solid #000; width: 300px; margin: 40px auto 4px; }}
  .centro {{ text-align: center; }}
  .checkbox-area {{ display: flex; gap: 20px; align-items: center; }}
  @media print {{ .no-print {{ display: none; }} }}
  .btn-assinar {{ background: #9eff1f; color: #000; border: none; padding: 12px 32px; font-size: 15px; font-weight: 800; border-radius: 8px; cursor: pointer; display: block; margin: 30px auto; }}
  .btn-imprimir {{ background: #378ADD; color: #fff; border: none; padding: 10px 24px; font-size: 13px; font-weight: 700; border-radius: 8px; cursor: pointer; display: block; margin: 10px auto; }}
  .assinatura-box {{ background: #f9f9f9; border: 2px dashed #ccc; border-radius: 10px; padding: 24px; margin: 20px 0; text-align: center; display: none; }}
  .assinatura-box input {{ width: 80%; padding: 10px; font-size: 14px; margin: 8px 0; border: 1px solid #ccc; border-radius: 6px; display: block; margin: 8px auto; }}
  .confirmado {{ background: #e8ffe8; border: 2px solid #2a2; border-radius: 10px; padding: 20px; text-align: center; display: none; }}
</style>
</head>
<body>

<div class="no-print" style="text-align:center;margin-bottom:20px">
  <button class="btn-imprimir" onclick="window.print()">🖨️ Imprimir / Salvar PDF</button>
</div>

<h1>CONTRATO DE LOCAÇÃO DE VEÍCULOS</h1>

<p><strong>LOCADOR:</strong> LOCA MAIS CAR LOCAÇÃO DE VEICULOS LTDA, portador do CNPJ 57.800.204/0001-24, residente na Avenida Rodrigues Alves, 180, Bairro Rosário, São João da Boa Vista – SP, CEP 13870-320.</p>

<p><strong>LOCATÁRIO:</strong> <span class="campo">{cli.nome or "___"}</span><br>
CPF: <span class="campo">{cli.cpf or "___"}</span><br>
Endereço: <span class="campo">{cli.endereco or "___"}</span><br>
Bairro: <span class="campo">{cli.bairro or "___"}</span><br>
Cidade: <span class="campo">{cli.cidade or "___"}</span><br>
Estado: <span class="campo">{cli.estado or "___"}</span><br>
CEP: <span class="campo">{cli.cep or "___"}</span><br>
Estado Civil: <span class="campo">{cli.estado_civil or "___"}</span></p>

<p><strong>CONDUTOR(ES) AUTORIZADO(S):</strong> {cli.nome or "___"}, CPF {cli.cpf or "___"}.</p>

<h2>CLÁUSULA 1 – DO OBJETO E FINALIDADE</h2>
<p><strong>1.1.</strong> O presente contrato tem por objeto a locação de veículo de propriedade do <strong>LOCADOR</strong> ao <strong>LOCATÁRIO</strong>, para utilização em atividades lícitas, podendo, a exclusivo critério do <strong>LOCATÁRIO</strong>, ser empregado no transporte privado individual de passageiros por meio de plataformas digitais (ex.: Uber, 99), ou em quaisquer outras atividades permitidas por lei, sem qualquer ingerência do <strong>LOCADOR</strong>.</p>

<p><strong>1.2.</strong> O veículo objeto da presente locação possui as seguintes características:</p>
<ul>
  <li><strong>Marca/Modelo:</strong> {vei.marca or "___"} {vei.modelo or "___"}</li>
  <li><strong>Ano/Modelo:</strong> {vei.ano or "___"}</li>
  <li><strong>Placa:</strong> {vei.placa or "___"}</li>
  <li><strong>Chassi:</strong> {vei.chassi or "___"}</li>
  <li><strong>Cor:</strong> {vei.cor or "___"}</li>
  <li><strong>RENAVAM:</strong> {vei.renavam or "___"}</li>
  <li><strong>Quilometragem na entrega:</strong> {int(vei.quilometragem or 0):,} km</li>
</ul>

<p><strong>1.3.</strong> O <strong>LOCATÁRIO</strong> declara, neste ato, ter recebido o veículo em perfeitas condições de uso, conservação, funcionamento e limpeza, conforme verificado em inspeção prévia e detalhado no Termo de Vistoria (Anexo I), que passa a integrar o presente instrumento para todos os fins de direito.</p>

<p><strong>1.4.</strong> A utilização do veículo dar-se-á por conta e risco exclusivo do <strong>LOCATÁRIO</strong>, que exercerá suas atividades com total independência, assumindo integral responsabilidade pela forma de uso do bem.</p>

<h2>CLÁUSULA 2ª – DA NATUREZA DO CONTRATO E INEXISTÊNCIA DE VÍNCULO EMPREGATÍCIO</h2>
<p><strong>2.1.</strong> O presente instrumento é um contrato de locação de bem móvel, de natureza estritamente civil, regido pelos artigos 565 e seguintes do Código Civil, não se configurando, em qualquer hipótese, como um contrato de trabalho.</p>
<p><strong>2.2.</strong> As partes declaram que não há entre si qualquer vínculo de emprego, uma vez que estão ausentes os requisitos caracterizadores da relação de emprego previstos no art. 3º da CLT, especialmente a subordinação.</p>
<p><strong>2.3.</strong> O <strong>LOCATÁRIO</strong> possui total autonomia para definir seus horários de trabalho, locais, frequência e aceitação de corridas, não estando sujeito a qualquer poder diretivo, fiscalizatório ou disciplinar por parte do <strong>LOCADOR</strong>.</p>
<p><strong>2.4.</strong> O valor pago pelo <strong>LOCATÁRIO</strong> tem natureza de aluguel pela utilização do bem, e não de salário. Todos os riscos da atividade econômica de transporte por aplicativo são de responsabilidade exclusiva do <strong>LOCATÁRIO</strong>.</p>
<p><strong>2.5.</strong> O <strong>LOCADOR</strong> não exerce atividade de transporte de passageiros, limitando-se exclusivamente à locação de veículos, inexistindo qualquer participação, ingerência ou proveito direto sobre a atividade desempenhada pelo <strong>LOCATÁRIO</strong>.</p>
<p><strong>2.6.</strong> O <strong>LOCATÁRIO</strong> poderá exercer suas atividades com outros veículos, plataformas ou atividades econômicas, inexistindo qualquer exclusividade em relação ao <strong>LOCADOR</strong>.</p>
<p><strong>2.7.</strong> O <strong>LOCADOR</strong> não estabelece metas, jornadas, roteiros, padrões de atendimento ou qualquer diretriz operacional ao <strong>LOCATÁRIO</strong>, inexistindo poder diretivo, fiscalizatório ou disciplinar.</p>

<h2>CLÁUSULA 3ª – DO PRAZO</h2>
<p><strong>3.1.</strong> O prazo da locação tem início em <span class="campo">{data_inicio}</span> e término em <span class="campo">{data_fim}</span>.</p>
<p><strong>3.2.</strong> Caso o <strong>LOCATÁRIO</strong> deseje prorrogar o contrato, deverá notificar o <strong>LOCADOR</strong> com antecedência mínima de 30 (trinta) dias do vencimento. A prorrogação dependerá de acordo entre as partes e da celebração de um termo aditivo.</p>

<h2>CLÁUSULA 4ª – DO VALOR, PAGAMENTO E QUILOMETRAGEM</h2>
<p><strong>4.1.</strong> O valor da locação é de:<br>
<span class="campo">{periodo} – {valor_fmt}</span><br>
FORMA DE PAGAMENTO: PIX<br>
PIX – 57800204000100 - CNPJ</p>
<p><strong>4.2.</strong> O valor estipulado na cláusula 4.1 dá direito ao <strong>LOCATÁRIO</strong> a uma franquia de 8.000 (oito mil) quilômetros por mês.</p>
<p><strong>4.3.</strong> A quilometragem excedente será cobrada à parte, no valor de R$ 0,50 (cinquenta centavos) por quilômetro rodado.</p>
<p><strong>4.4.</strong> O não pagamento do aluguel na data estipulada implicará em multa de 10% sobre o valor devido, acrescida de juros de mora de 1% ao mês e correção monetária pelo IGPM/FGV.</p>
<p><strong>4.5.</strong> O atraso no pagamento por período superior a 2 (dois) dias autoriza o <strong>LOCADOR</strong>, mediante prévia notificação, a promover o bloqueio do veículo por sistema de rastreamento, bem como sua imediata retomada.</p>
<p><strong>4.6.</strong> O valor do aluguel é fixo e invariável, não estando vinculado ao faturamento, lucro, volume de corridas ou êxito financeiro do <strong>LOCATÁRIO</strong>.</p>
<p><strong>4.7.</strong> O <strong>LOCATÁRIO</strong> declara estar ciente de que assume integralmente todos os riscos de sua atividade econômica.</p>
<p><strong>4.8.</strong> O valor da locação é devido pela simples disponibilização do veículo, independentemente de sua efetiva utilização.</p>

<h2>CLÁUSULA 5ª – DAS OBRIGAÇÕES DO LOCADOR</h2>
<p><strong>5.1.</strong> Entregar o veículo ao <strong>LOCATÁRIO</strong> em perfeitas condições de uso e com a documentação regular.</p>
<p><strong>5.2.</strong> Manter o seguro do veículo vigente durante toda a vigência contratual.</p>
<p><strong>5.3.</strong> Realizar e custear as manutenções preventivas decorrentes do plano de revisão do fabricante.</p>

<h2>CLÁUSULA 6ª – DOS DEVERES, USO E PROIBIÇÕES EXPRESSAS DO LOCATÁRIO</h2>
<p><strong>6.1.</strong> O <strong>LOCATÁRIO</strong> compromete-se a conduzir o veículo com o máximo zelo, prudência e diligência, respeitando integralmente o Código de Trânsito Brasileiro.</p>
<p><strong>6.2.</strong> Responsabilizar-se por todas as despesas de uso regular do veículo, como recarga elétrica, lavagem e produtos de limpeza.</p>
<p><strong>6.3.</strong> Manter o veículo em perfeito estado de conservação e limpeza.</p>
<p><strong>6.4.</strong> A devolução do veículo em condições de sujeira excessiva acarretará a cobrança de uma taxa de higienização simples no valor de R$ 200,00.</p>
<p><strong>6.5.</strong> Caso seja identificado odor de cigarro, vômito, dejetos de animais ou danos ao estofado, será cobrada uma taxa de higienização especial no valor de R$ 1.200,00.</p>
<p><strong>6.6.</strong> É terminantemente proibido ao <strong>LOCATÁRIO</strong>: dirigir sob influência de álcool ou substâncias psicoativas; praticar direção perigosa; utilizar o veículo para atos ilícitos; fumar no interior do veículo.</p>
<p><strong>6.7.</strong> É igualmente vedado ceder, emprestar, sublocar ou permitir que pessoa não autorizada conduza o veículo, bem como realizar qualquer modificação sem autorização prévia.</p>

<h2>CLÁUSULA 7ª – DAS MULTAS DE TRÂNSITO</h2>
<p><strong>7.1.</strong> O <strong>LOCATÁRIO</strong> é o único e exclusivo responsável por todas as multas e infrações de trânsito ocorridas durante a vigência do contrato.</p>
<p><strong>7.2.</strong> O <strong>LOCATÁRIO</strong> obriga-se a efetuar o pagamento das multas até a data de seu vencimento.</p>

<h2>CLÁUSULA 8ª – DOS SINISTROS, DANOS E SEGURO</h2>
<p><strong>8.1.</strong> Em caso de acidente, roubo, furto ou incêndio, o <strong>LOCATÁRIO</strong> deverá comunicar o <strong>LOCADOR</strong> imediatamente ou em no máximo 1 hora após o conhecimento do fato.</p>
<p><strong>8.2.</strong> O <strong>LOCATÁRIO</strong> será responsável pelo pagamento da franquia do seguro, no valor de 6% do valor do veículo constante na Tabela FIPE.</p>

<h2>CLÁUSULA 9ª – AUSÊNCIA DE GARANTIA DE DISPONIBILIDADE</h2>
<p><strong>9.1.</strong> O <strong>LOCADOR</strong> não garante a disponibilidade contínua do veículo em casos de manutenção preventiva ou corretiva, recalls, sinistros ou atos de autoridade.</p>

<h2>CLÁUSULA 10ª – DA RESPONSABILIDADE PERANTE TERCEIROS</h2>
<p><strong>10.1.</strong> O <strong>LOCATÁRIO</strong> é o único e exclusivo responsável por quaisquer danos materiais, morais ou corporais causados a terceiros em decorrência da utilização do veículo.</p>

<h2>CLÁUSULA 11ª – DA MANUTENÇÃO PREVENTIVA</h2>
<p><strong>11.1.</strong> O <strong>LOCATÁRIO</strong> obriga-se a apresentar o veículo para a realização das manutenções preventivas periódicas conforme o plano de revisões do fabricante.</p>

<h2>CLÁUSULA 12ª – DA HABILITAÇÃO E CONDIÇÕES PARA CONDUÇÃO</h2>
<p><strong>12.1.</strong> O <strong>LOCATÁRIO</strong> declara possuir Carteira Nacional de Habilitação (CNH) válida, na categoria exigida pela legislação brasileira.</p>

<h2>CLÁUSULA 13ª – DO RASTREAMENTO E BLOQUEIO</h2>
<p><strong>13.1.</strong> O <strong>LOCATÁRIO</strong> declara estar ciente e de acordo que o veículo possui sistema de rastreamento e monitoramento.</p>

<h2>CLÁUSULA 14ª – DA AUSÊNCIA DE SOCIEDADE OU PARCERIA</h2>
<p>O presente contrato não estabelece qualquer vínculo societário, associação, parceria ou relação de cooperação empresarial entre as partes.</p>

<h2>CLÁUSULA 15ª – DA RESCISÃO</h2>
<p><strong>15.1.</strong> A violação de qualquer cláusula deste contrato será considerada falta grave e quebra contratual, autorizando o <strong>LOCADOR</strong> a rescindir o contrato de pleno direito.</p>
<p><strong>15.2.</strong> Em caso de rescisão, o <strong>LOCATÁRIO</strong> deverá devolver o veículo imediatamente, sob pena de multa diária de R$ 250,00.</p>

<h2>CLÁUSULA 16ª – DA PRIVACIDADE E PROTEÇÃO DE DADOS (LGPD)</h2>
<p><strong>16.1.</strong> O <strong>LOCATÁRIO</strong> declara ciência e consente que o <strong>LOCADOR</strong> realize o tratamento de seus dados pessoais e dados de geolocalização do veículo, nos termos da LGPD.</p>

<h2>CLÁUSULA 17ª – DO FORO</h2>
<p><strong>17.1.</strong> Fica eleito o foro da comarca de São João da Boa Vista, Estado de São Paulo, para dirimir quaisquer litígios decorrentes deste contrato.</p>

<p>E, por estarem justas e contratadas, as partes assinam o presente instrumento em 2 (duas) vias de igual teor e forma.</p>
<p>São João da Boa Vista, <span class="campo">{data_hoje}</span></p>

<div class="assinatura">
  <div class="centro">
    <div class="linha"></div>
    <p>LOCA MAIS CAR LOCAÇÃO DE VEICULOS LTDA</p>
  </div>
  <div class="centro" style="margin-top:40px">
    <div class="linha"></div>
    <p><strong>{cli.nome or "LOCATÁRIO"}</strong> (LOCATÁRIO)</p>
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

<h2 style="margin-top:40px;text-align:center">APÊNDICE – TERMO DE VISTORIA DE ENTREGA E DEVOLUÇÃO</h2>

<table>
  <thead>
    <tr>
      <th>Item</th>
      <th>Condição</th>
      <th>Observações</th>
    </tr>
  </thead>
  <tbody>
    {"".join([f'<tr><td>{item}</td><td><label><input type="radio" name="item_{i}_cond" value="sim"> Sim</label> &nbsp; <label><input type="radio" name="item_{i}_cond" value="nao"> Não</label></td><td><input type="text" style="width:100%;border:none;border-bottom:1px solid #ccc"></td></tr>' for i, item in enumerate(["Pneus","Estepe","Macaco/Chave de Roda","Vidros/Parabrisa","Retrovisores","Faróis/Lanternas","Banco dianteiro/traseiro","Estofamento interno","Painel de instrumentos","Ar-condicionado","Rádio/Multimídia","Documentos do veículo","Chave reserva","Carroceria/Lataria"])])}
  </tbody>
</table>

<div style="margin-top:40px;display:flex;justify-content:space-between">
  <div>
    <div class="linha" style="width:250px;margin:40px 0 4px 0"></div>
    <p>Assinatura LOCADORA</p>
  </div>
  <div>
    <div class="linha" style="width:250px;margin:40px 0 4px 0"></div>
    <p>Assinatura LOCATÁRIO</p>
  </div>
</div>

<div class="no-print" style="margin-top:40px;border-top:2px solid #ccc;padding-top:20px">
  <h2 style="text-align:center">✍️ Assinatura Digital</h2>
  <div id="area-assinar">
    <button class="btn-assinar" onclick="document.getElementById('area-assinar').style.display='none';document.getElementById('form-assinar').style.display='block'">Clique aqui para assinar este contrato</button>
  </div>
  <div class="assinatura-box" id="form-assinar">
    <p><strong>Para assinar, confirme seus dados:</strong></p>
    <input type="text" id="ass-nome" placeholder="Digite seu nome completo"/>
    <input type="text" id="ass-cpf" placeholder="Digite seu CPF (000.000.000-00)"/>
    <button class="btn-assinar" onclick="assinarContrato()">✓ Confirmar Assinatura</button>
    <p style="font-size:11px;color:#666;margin-top:10px">Ao clicar em confirmar, você declara ter lido e concordado com todos os termos deste contrato.</p>
  </div>
  <div class="confirmado" id="confirmado">
    <h2>✅ Contrato Assinado!</h2>
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
      body: JSON.stringify({{nome, cpf, locacao_id: {locacao_id}}})
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
    alert('Erro de conexão. Tente novamente.');
  }}
}}
</script>
</body>
</html>"""
    return html

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
