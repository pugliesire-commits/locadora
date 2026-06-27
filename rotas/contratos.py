from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from modelos.database import get_db
from modelos.locacao import Locacao
from modelos.cliente import Cliente
from modelos.veiculo import Veiculo
from modelos.usuario import Usuario
from datetime import datetime
from typing import Optional
import jwt
import os

router = APIRouter(prefix="/contratos", tags=["Contratos"])

MESES_PT = {1:"janeiro",2:"fevereiro",3:"marco",4:"abril",5:"maio",6:"junho",7:"julho",8:"agosto",9:"setembro",10:"outubro",11:"novembro",12:"dezembro"}

def formatar_data_extenso(d):
    if not d: return "___"
    try:
        if isinstance(d, str): d = datetime.strptime(d[:10], "%Y-%m-%d")
        return f"{d.day} de {MESES_PT[d.month]} de {d.year}"
    except: return str(d)

def formatar_data(d):
    if not d: return "___"
    try:
        if isinstance(d, str): return d[8:10]+"/"+d[5:7]+"/"+d[:4]
        return d.strftime("%d/%m/%Y")
    except: return str(d)

def formatar_datetime(d):
    if not d: return "___"
    try: return d.strftime("%d/%m/%Y %H:%M")
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

    periodo_label = "DIARIO" if loc.periodo == "diario" else "SEMANAL" if loc.periodo == "semanal" else "MENSAL"
    valor_fmt = f"R$ {loc.valor_periodo:.2f}".replace(".", ",")
    data_inicio = formatar_data_extenso(loc.data_inicio)
    data_fim = formatar_data_extenso(loc.data_fim)
    data_hoje = formatar_data_extenso(datetime.now())

    # Status assinaturas
    loc_assinado = loc.contrato_assinado or False
    loc_nome = loc.contrato_assinado_nome or ""
    loc_em = formatar_datetime(loc.contrato_assinado_em) if loc.contrato_assinado_em else ""
    loca_assinado = loc.locador_assinado or False
    loca_nome = loc.locador_assinado_nome or ""
    loca_em = formatar_datetime(loc.locador_assinado_em) if loc.locador_assinado_em else ""

    status_locatario = f'<span style="color:green;font-weight:700">✓ Assinado por {loc_nome} em {loc_em}</span>' if loc_assinado else '<span style="color:#cc0000">⚠ Aguardando assinatura do locatário</span>'
    status_locador = f'<span style="color:green;font-weight:700">✓ Assinado por {loca_nome} em {loca_em}</span>' if loca_assinado else '<span style="color:#cc0000">⚠ Aguardando assinatura do locador</span>'

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Contrato de Locacao #{locacao_id}</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 13px; color: #000; max-width: 820px; margin: 0 auto; padding: 30px 40px; line-height: 1.7; }}
  h1 {{ text-align: center; font-size: 15px; font-weight: bold; margin-bottom: 24px; text-transform: uppercase; }}
  h2 {{ font-size: 13px; font-weight: bold; margin-top: 22px; margin-bottom: 6px; text-transform: uppercase; }}
  p {{ margin: 6px 0; text-align: justify; }}
  ul {{ margin: 6px 0 6px 20px; }}
  li {{ margin: 4px 0; }}
  .campo {{ font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  table th, table td {{ border: 1px solid #000; padding: 6px 10px; font-size: 12px; }}
  table th {{ background: #f0f0f0; text-align: center; }}
  .linha {{ border-top: 1px solid #000; margin-bottom: 6px; }}
  .centro {{ text-align: center; }}
  .bloco-assinatura {{ display: flex; justify-content: space-between; margin-top: 60px; }}
  .assinante {{ text-align: center; width: 45%; }}
  @media print {{ .no-print {{ display: none; }} body {{ padding: 20px; }} }}
  .btn-imprimir {{ background: #007bff; color: #fff; border: none; padding: 10px 24px; font-size: 13px; font-weight: 700; border-radius: 8px; cursor: pointer; margin: 5px; }}
  .btn-assinar {{ background: #28a745; color: #fff; border: none; padding: 12px 32px; font-size: 15px; font-weight: 800; border-radius: 8px; cursor: pointer; display: block; margin: 20px auto; }}
  .btn-locador {{ background: #1a1a2e; color: #9eff1f; border: 2px solid #9eff1f; padding: 12px 32px; font-size: 15px; font-weight: 800; border-radius: 8px; cursor: pointer; display: block; margin: 20px auto; }}
  .assinatura-box {{ background: #f9f9f9; border: 2px dashed #aaa; border-radius: 10px; padding: 24px; margin: 20px 0; text-align: center; display: none; }}
  .assinatura-box input {{ width: 80%; padding: 10px; font-size: 14px; margin: 8px auto; border: 1px solid #ccc; border-radius: 6px; display: block; }}
  .confirmado {{ background: #e8ffe8; border: 2px solid #2a2; border-radius: 10px; padding: 20px; text-align: center; }}
  .status-box {{ background: #f5f5f5; border: 1px solid #ddd; border-radius: 10px; padding: 16px 20px; margin: 20px 0; }}
  .status-box h3 {{ font-size: 13px; margin-bottom: 10px; color: #333; }}
  .status-linha {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee; }}
  .status-linha:last-child {{ border-bottom: none; }}
  .secao-digital {{ margin-top: 40px; border-top: 2px solid #ccc; padding-top: 20px; }}
</style>
</head>
<body>

<div class="no-print" style="text-align:center;margin-bottom:20px;background:#f5f5f5;padding:12px;border-radius:8px">
  <button class="btn-imprimir" onclick="window.print()">Imprimir / Salvar PDF</button>
</div>

<h1>CONTRATO DE LOCACAO DE VEICULOS</h1>

<p><strong>LOCADOR:</strong> LOCA MAIS CAR LOCACAO DE VEICULOS LTDA, portador do CNPJ 57.800.204/0001-24, residente na Avenida Rodrigues Alves, 180, Bairro Rosario, Sao Joao da Boa Vista - SP, CEP 13870-320.</p>

<p style="margin-top:12px"><strong>LOCATARIO:</strong> <span class="campo">{cli.nome or "___"}</span><br>
CPF: <span class="campo">{cli.cpf or "___"}</span><br>
Endereco: <span class="campo">{cli.endereco or "___"}</span><br>
Bairro: <span class="campo">{cli.bairro or "___"}</span><br>
Cidade: <span class="campo">{cli.cidade or "___"}</span><br>
Estado: <span class="campo">{cli.estado or "___"}</span><br>
CEP: <span class="campo">{cli.cep or "___"}</span><br>
Estado Civil: <span class="campo">{cli.estado_civil or "___"}</span></p>

<p style="margin-top:10px"><strong>CONDUTOR(ES) AUTORIZADO(S):</strong> {cli.nome or "___"}, CPF {cli.cpf or "___"}.</p>

<h2>CLAUSULA 1 - DO OBJETO E FINALIDADE</h2>
<p><strong>1.1.</strong> O presente contrato tem por objeto a locacao de veiculo de propriedade do <strong>LOCADOR</strong> ao <strong>LOCATARIO</strong>, para utilizacao em atividades licitas, podendo, a exclusivo criterio do <strong>LOCATARIO</strong>, ser empregado no transporte privado individual de passageiros por meio de plataformas digitais (ex.: Uber, 99), ou em quaisquer outras atividades permitidas por lei, sem qualquer ingerencia do <strong>LOCADOR</strong>.</p>
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
<p><strong>1.3.</strong> O <strong>LOCATARIO</strong> declara, neste ato, ter recebido o veiculo em perfeitas condicoes de uso, conservacao, funcionamento e limpeza, conforme verificado em inspecao previa e detalhado no Termo de Vistoria (Anexo I), que passa a integrar o presente instrumento para todos os fins de direito.</p>
<p><strong>1.4.</strong> A utilizacao do veiculo dar-se-a por conta e risco exclusivo do <strong>LOCATARIO</strong>, que exercera suas atividades com total independencia, assumindo integral responsabilidade pela forma de uso do bem.</p>

<h2>CLAUSULA 2 - DA NATUREZA DO CONTRATO E INEXISTENCIA DE VINCULO EMPREGATICIO</h2>
<p><strong>2.1.</strong> O presente instrumento e um contrato de locacao de bem movel, de natureza estritamente civil, regido pelos artigos 565 e seguintes do Codigo Civil, nao se configurando, em qualquer hipotese, como um contrato de trabalho.</p>
<p><strong>2.2.</strong> As partes declaram que nao ha entre si qualquer vinculo de emprego, uma vez que estao ausentes os requisitos caracterizadores da relacao de emprego previstos no art. 3 da CLT, especialmente a subordinacao.</p>
<p><strong>2.3.</strong> O <strong>LOCATARIO</strong> possui total autonomia para definir seus horarios de trabalho, locais, frequencia e aceitacao de corridas, nao estando sujeito a qualquer poder diretivo, fiscalizatorio ou disciplinar por parte do <strong>LOCADOR</strong>.</p>
<p><strong>2.4.</strong> O valor pago pelo <strong>LOCATARIO</strong> tem natureza de aluguel pela utilizacao do bem, e nao de salario. Todos os riscos da atividade economica de transporte por aplicativo sao de responsabilidade exclusiva do <strong>LOCATARIO</strong>.</p>
<p><strong>2.5.</strong> O <strong>LOCADOR</strong> nao exerce atividade de transporte de passageiros, limitando-se exclusivamente a locacao de veiculos, inexistindo qualquer participacao, ingerencia ou proveito direto sobre a atividade desempenhada pelo <strong>LOCATARIO</strong>.</p>
<p><strong>2.6.</strong> O <strong>LOCATARIO</strong> podera exercer suas atividades com outros veiculos, plataformas ou atividades economicas, inexistindo qualquer exclusividade em relacao ao <strong>LOCADOR</strong>.</p>
<p><strong>2.7.</strong> O <strong>LOCADOR</strong> nao estabelece metas, jornadas, roteiros, padroes de atendimento ou qualquer diretriz operacional ao <strong>LOCATARIO</strong>, inexistindo poder diretivo, fiscalizatorio ou disciplinar.</p>

<h2>CLAUSULA 3 - DO PRAZO</h2>
<p><strong>3.1.</strong> O prazo da locacao tem inicio em <span class="campo">{data_inicio}</span> e termino em <span class="campo">{data_fim}</span>.</p>
<p><strong>3.2.</strong> Caso o <strong>LOCATARIO</strong> deseje prorrogar o contrato, devera notificar o <strong>LOCADOR</strong> com antecedencia minima de 30 (trinta) dias do vencimento. A prorrogacao dependera de acordo entre as partes e da celebracao de um termo aditivo.</p>

<h2>CLAUSULA 4 - DO VALOR, PAGAMENTO E QUILOMETRAGEM</h2>
<p><strong>4.1.</strong> O valor da locacao e de: <span class="campo">{periodo_label} - {valor_fmt}</span><br>
FORMA DE PAGAMENTO: PIX<br>
PIX - 57800204000100 - CNPJ</p>
<p><strong>4.2.</strong> O valor estipulado na clausula 4.1 da direito ao <strong>LOCATARIO</strong> a uma franquia de 8.000 (oito mil) quilometros por mes, considerada como periodo de 30 (trinta) dias corridos a contar do inicio da locacao, sendo a quilometragem controlada de forma global no periodo, independentemente da forma de pagamento semanal.</p>
<p><strong>4.3.</strong> A quilometragem excedente sera cobrada a parte, no valor de R$ 0,50 (cinquenta centavos) por quilometro rodado. A apuracao e o pagamento do valor excedente ocorrerao no primeiro dia util do mes subsequente.</p>
<p><strong>4.4.</strong> O nao pagamento do aluguel na data estipulada implicara em multa de 10% (dez por cento) sobre o valor devido, acrescida de juros de mora de 1% (um por cento) ao mes e correcao monetaria pelo IGPM/FGV.</p>
<p><strong>4.5.</strong> O atraso no pagamento por periodo superior a 2 (dois) dias autoriza o <strong>LOCADOR</strong>, mediante previa notificacao, inclusive por meio eletronico, com concessao de prazo de 24 (vinte e quatro) horas para regularizacao, a promover o bloqueio do veiculo por sistema de rastreamento, bem como sua imediata retomada, independentemente de ordem judicial, sem prejuizo da cobranca dos valores devidos e da rescisao contratual.</p>
<p><strong>4.6.</strong> As partes ajustam expressamente que o valor do aluguel e fixo e invariavel, nao estando, sob qualquer pretexto, vinculado ao faturamento, lucro, volume de corridas ou exito financeiro do <strong>LOCATARIO</strong> em sua atividade profissional.</p>
<p><strong>4.7.</strong> O <strong>LOCATARIO</strong> declara estar ciente de que, na qualidade de profissional autonomo, assume integralmente todos os riscos de sua atividade economica. A ausencia de faturamento, a baixa demanda de passageiros, problemas com plataformas de transporte, a interrupcao ou cessacao de suas atividades profissionais, ainda que temporaria, bem como a decisao pessoal de nao utilizar o veiculo, nao o eximem do pagamento pontual e integral do aluguel, uma vez que a contraprestacao e devida pela simples disponibilizacao do veiculo para seu uso exclusivo.</p>
<p><strong>4.8.</strong> O valor da locacao e devido pela simples disponibilizacao do veiculo, independentemente de sua efetiva utilizacao, do volume de corridas realizadas, da receita obtida ou de qualquer resultado economico do <strong>LOCATARIO</strong>.</p>

<h2>CLAUSULA 5 - DAS OBRIGACOES DO LOCADOR</h2>
<p><strong>5.1.</strong> Entregar o veiculo ao <strong>LOCATARIO</strong> em perfeitas condicoes de uso e com a documentacao regular.</p>
<p><strong>5.2.</strong> Manter o seguro do veiculo vigente, durante toda a vigencia contratual, com cobertura minima para colisao, roubo, furto, incendio, danos decorrentes de fenomenos da natureza, bem como responsabilidade civil facultativa por danos materiais e corporais a terceiros (minimo de R$ 30.000,00), incluindo assistencia 24 horas, servico de guincho, cobertura para despesas medico-hospitalares, auxilio retorno a domicilio e cobertura para vidros, conforme condicoes da apolice contratada.</p>
<p><strong>5.3.</strong> Realizar e custear as manutencoes preventivas decorrentes do plano de revisao do fabricante.</p>

<h2>CLAUSULA 6 - DOS DEVERES, USO E PROIBICOES EXPRESSAS DO LOCATARIO</h2>
<p><strong>6.1.</strong> O <strong>LOCATARIO</strong> compromete-se a conduzir o veiculo com o maximo zelo, prudencia e diligencia, sendo sua obrigacao respeitar integralmente todas as disposicoes do Codigo de Transito Brasileiro (Lei n 9.503/97) e demais legislacoes aplicaveis.</p>
<p><strong>6.2.</strong> Responsabilizar-se por todas as despesas de uso regular do veiculo, como recarga eletrica, lavagem e produtos de limpeza.</p>
<p><strong>6.3.</strong> Manter o veiculo em perfeito estado de conservacao e limpeza.</p>
<p><strong>6.4.</strong> A devolucao do veiculo em condicoes de sujeira excessiva (ex: barro, areia, residuos de alimentos) acarretara a cobranca de uma taxa de higienizacao simples no valor de R$ 200,00 (duzentos reais).</p>
<p><strong>6.5.</strong> Caso seja identificado odor de cigarro, vomito, dejetos de animais ou danos ao estofado (manchas, rasgos, queimaduras), sera cobrada uma taxa de higienizacao especial e reparo no valor de R$ 1.200,00 (mil e duzentos reais), sem prejuizo da apuracao de custos excedentes para o conserto.</p>
<p><strong>6.6.</strong> E terminantemente proibido ao <strong>LOCATARIO</strong>, sob pena de rescisao imediata do contrato e aplicacao das penalidades cabiveis:</p>
<p>a) Dirigir sob influencia de alcool ou qualquer outra substancia psicoativa que determine dependencia;</p>
<p>b) Praticar direcao perigosa, incluindo, mas nao se limitando a exceder os limites de velocidade, realizar manobras arriscadas, participar de corridas, disputas ou "rachas";</p>
<p>c) Utilizar o veiculo para a pratica de qualquer ato ilicito, incluindo o transporte de armas, drogas, produtos de contrabando ou quaisquer outros itens de origem ou natureza ilicita, bem como para a pratica de qualquer crime ou contravencao penal;</p>
<p>d) Fumar no interior do veiculo.</p>
<p><strong>6.7.</strong> E igualmente vedado ao <strong>LOCATARIO</strong>:</p>
<p>a) Utilizar o veiculo para fins diversos do transporte remunerado de passageiros;</p>
<p>b) Ceder, emprestar, sublocar ou permitir que qualquer pessoa nao autorizada neste contrato conduza o veiculo;</p>
<p>c) Realizar qualquer modificacao no veiculo, como instalacao de acessorios, retirada de peliculas, adesivos, bancos, etc., sem autorizacao previa e expressa do <strong>LOCADOR</strong>.</p>
<p><strong>6.8.</strong> O <strong>LOCADOR</strong> nao possui qualquer responsabilidade, direta ou indireta, sobre a conduta do <strong>LOCATARIO</strong> ou sobre os itens por ele transportados. O <strong>LOCATARIO</strong> assume integralmente a responsabilidade civil e criminal por quaisquer atos ilicitos que venha a cometer na conducao do veiculo, isentando o <strong>LOCADOR</strong> de qualquer envolvimento ou onus, inclusive perante terceiros e autoridades administrativas ou judiciais.</p>
<p><strong>6.9.</strong> O descumprimento de qualquer item desta clausula sera considerado falta grave e quebra contratual, autorizando o <strong>LOCADOR</strong> a, imediatamente: a) rescindir o contrato de pleno direito; b) proceder ao bloqueio e a retomada do veiculo, onde quer que ele se encontre; c) cobrar do <strong>LOCATARIO</strong> a integralidade de todos os danos, prejuizos, multas contratuais e administrativas, e custos judiciais ou extrajudiciais que venham a ocorrer.</p>
<p><strong>6.10.</strong> O uso do veiculo se da por conta e risco exclusivo do <strong>LOCATARIO</strong>, inexistindo qualquer responsabilidade do <strong>LOCADOR</strong> sobre a forma de utilizacao do bem.</p>

<h2>CLAUSULA 7 - DAS MULTAS DE TRANSITO</h2>
<p><strong>7.1.</strong> O <strong>LOCATARIO</strong> e o unico e exclusivo responsavel por todas as multas e infracoes de transito ocorridas durante a vigencia do contrato, mesmo que a notificacao seja recebida pelo <strong>LOCADOR</strong> apos o termino da locacao.</p>
<p><strong>7.2.</strong> Na hipotese de o veiculo estar ou vier a ser registrado em nome de Pessoa Juridica, o <strong>LOCATARIO</strong> declara-se ciente de que a nao indicacao do condutor infrator no prazo legal acarreta a imposicao de uma nova multa (Multa NIC), cujo valor e o dobro da multa originaria, conforme o Art. 257, paragrafo 8 do Codigo de Transito Brasileiro.</p>
<p>a) Caso o <strong>LOCATARIO</strong> nao realize a indicacao no prazo, ele assume a responsabilidade pelo pagamento integral tanto da multa originaria quanto da multa em dobro (NIC).</p>
<p><strong>7.3.</strong> O <strong>LOCATARIO</strong> obriga-se a efetuar o pagamento das multas ate a data de seu vencimento, devendo encaminhar ao <strong>LOCADOR</strong> o respectivo comprovante de pagamento no mesmo prazo.</p>
<p><strong>7.4.</strong> Caso o <strong>LOCATARIO</strong> nao realize o pagamento no prazo, o <strong>LOCADOR</strong> fica autorizado a efetuar o pagamento da multa e de eventuais encargos incidentes, podendo cobrar o reembolso imediato do <strong>LOCATARIO</strong>.</p>

<h2>CLAUSULA 8 - DOS SINISTROS, DANOS E SEGURO</h2>
<p><strong>8.1.</strong> Em caso de acidente, roubo, furto ou incendio, o <strong>LOCATARIO</strong> devera comunicar o <strong>LOCADOR</strong> por telefone imediatamente ou em, no maximo, 1 (uma) hora apos o conhecimento do fato, e apresentar o Boletim de Ocorrencia (B.O.) em ate 24 (vinte e quatro) horas.</p>
<p><strong>8.2.</strong> O descumprimento dos prazos estabelecidos no item anterior implicara na perda de qualquer protecao ou cobertura do seguro, tornando o <strong>LOCATARIO</strong> o unico e integral responsavel por todos os danos e prejuizos.</p>
<p><strong>8.3.</strong> O <strong>LOCATARIO</strong> sera responsavel pelo pagamento da franquia do seguro, no valor de 6% (seis por cento) do valor do veiculo constante na Tabela FIPE vigente a epoca do sinistro, sempre que o seguro for acionado por sua culpa.</p>
<p><strong>8.4.</strong> A protecao do seguro nao cobre os danos a acessorios e itens especificos, sendo de responsabilidade do <strong>LOCATARIO</strong> o custo de reposicao de: pneus, estepe, rodas, calotas, antena, radio/multimidia, tapetes, macaco, chave de roda, triangulo, manuais, documento do veiculo (CRLV), chaves e o cabo de recarga.</p>
<p><strong>8.5.</strong> Em caso de apreensao ou remocao do veiculo por qualquer autoridade competente, em decorrencia de ato praticado pelo <strong>LOCATARIO</strong>, sera de sua integral e exclusiva responsabilidade:</p>
<p>a) Adotar todas as providencias e arcar com todos os custos para a liberacao do veiculo, incluindo taxas de reboque, diarias de patio, multas, despesas com despachantes e honorarios advocaticios, se necessarios.</p>
<p>b) Continuar pagando o valor integral da locacao, previsto na Clausula 4, durante todo o periodo em que o veiculo permanecer apreendido, uma vez que o <strong>LOCADOR</strong> estara privado do uso e fruicao de seu bem por culpa do <strong>LOCATARIO</strong>.</p>

<h2>CLAUSULA 9 - AUSENCIA DE GARANTIA DE DISPONIBILIDADE</h2>
<p><strong>9.1.</strong> O <strong>LOCADOR</strong> nao garante a disponibilidade continua do veiculo em casos de manutencao preventiva ou corretiva, recalls determinados pelo fabricante, sinistros (colisao, roubo, furto, incendio) ou atos de autoridade.</p>
<p><strong>9.2.</strong> Nesses casos, o <strong>LOCADOR</strong> nao esta obrigado a fornecer veiculo reserva, tampouco a indenizar lucros cessantes, ganhos nao auferidos ou qualquer outra compensacao financeira pela paralisacao temporaria, limitando-se sua obrigacao a adocao das providencias razoaveis para o restabelecimento da disponibilidade do veiculo no menor prazo possivel.</p>
<p><strong>9.3.</strong> Se a indisponibilidade decorrer de culpa exclusiva do <strong>LOCATARIO</strong> (uso indevido, descumprimento de manutencao programada, conducao irregular, violacao contratual), permanecem devidas as obrigacoes financeiras pactuadas, inclusive aluguel e franquia/participacao, sem prejuizo de eventuais perdas e danos.</p>

<h2>CLAUSULA 10 - DA RESPONSABILIDADE PERANTE TERCEIROS</h2>
<p><strong>10.1.</strong> O <strong>LOCATARIO</strong> e o unico e exclusivo responsavel por quaisquer danos materiais, morais ou corporais causados a terceiros em decorrencia da utilizacao do veiculo, obrigando-se a ressarcir integralmente o <strong>LOCADOR</strong> por eventuais prejuizos, condenacoes ou despesas decorrentes de tais eventos.</p>
<p><strong>10.2.</strong> Em caso de danos causados ao veiculo por terceiros, o <strong>LOCATARIO</strong> obriga-se a:</p>
<p>a) Identificar o terceiro, obter seus dados (nome, CPF, telefone, placa do veiculo) e inclui-los no Boletim de Ocorrencia.</p>
<p>b) Caso o terceiro assuma a culpa e pague o conserto integral, o <strong>LOCATARIO</strong> fica isento de custos.</p>
<p>c) Caso o terceiro nao seja identificado (fuga), nao possua seguro ou se recuse a pagar, o <strong>LOCATARIO</strong> sera responsavel pelo pagamento da Franquia/Coparticipacao prevista na Clausula 8.3, independentemente de culpa, para que o <strong>LOCADOR</strong> possa acionar o seguro e recompor o patrimonio.</p>
<p>d) O <strong>LOCATARIO</strong> nao sera responsavel pelo valor excedente a franquia em casos de comprovada ausencia de culpa, cabendo ao <strong>LOCADOR</strong> o direito de regresso contra o terceiro causador do dano.</p>
<p><strong>10.3.</strong> O <strong>LOCATARIO</strong> sera o unico responsavel pelo pagamento integral da franquia/coparticipacao do seguro sempre que o acionamento da apolice for necessario, seja por sua culpa ou pela impossibilidade de responsabilizar um terceiro, conforme item 10.2(c).</p>
<p><strong>10.4.</strong> O valor da franquia/coparticipacao a ser pago pelo <strong>LOCATARIO</strong> em caso de sinistro e de 6% (seis por cento) do valor do veiculo constante na Tabela FIPE vigente a epoca do sinistro, ou o valor estipulado na apolice de seguro vigente na data do ocorrido, o que for maior.</p>

<h2>CLAUSULA 11 - DA MANUTENCAO PREVENTIVA</h2>
<p><strong>11.1.</strong> O <strong>LOCATARIO</strong> obriga-se a apresentar o veiculo para a realizacao das manutencoes preventivas periodicas, conforme o plano de revisoes do fabricante.</p>
<p><strong>11.2.</strong> As manutencoes corretivas decorrentes de desgaste natural e uso regular do veiculo serao de responsabilidade do <strong>LOCADOR</strong>, enquanto aquelas oriundas de mau uso, negligencia, imprudencia, impericia ou descumprimento das obrigacoes contratuais pelo <strong>LOCATARIO</strong> serao integralmente suportadas por este, incluindo custos com pecas, mao de obra e eventuais lucros cessantes do <strong>LOCADOR</strong>.</p>

<h2>CLAUSULA 12 - DA HABILITACAO E CONDICOES PARA CONDUCAO</h2>
<p><strong>12.1.</strong> O <strong>LOCATARIO</strong> declara, sob as penas da lei, possuir Carteira Nacional de Habilitacao (CNH) valida, na categoria exigida pela legislacao brasileira para a conducao do veiculo objeto deste contrato.</p>
<p><strong>12.2.</strong> E obrigacao do <strong>LOCATARIO</strong> manter sua CNH devidamente regular e valida durante toda a vigencia deste contrato, providenciando sua renovacao tempestiva antes do vencimento.</p>
<p><strong>12.3.</strong> O <strong>LOCATARIO</strong> obriga-se a comunicar o <strong>LOCADOR</strong>, de forma imediata e por escrito, sobre qualquer suspensao, cassacao, bloqueio ou impedimento de seu direito de dirigir, bem como sobre o vencimento de sua CNH.</p>
<p><strong>12.4.</strong> A conducao do veiculo com a CNH vencida, suspensa, cassada ou em categoria inadequada constitui falta grave e quebra contratual, autorizando o <strong>LOCADOR</strong> a rescindir o contrato imediatamente e retomar o veiculo.</p>
<p><strong>12.5.</strong> O <strong>LOCATARIO</strong> declara estar ciente de que a conducao do veiculo em situacao de irregularidade da CNH pode acarretar a perda total da cobertura do seguro. Em tal hipotese, o <strong>LOCATARIO</strong> assumira integral e exclusivamente a responsabilidade por todos os danos causados ao veiculo e a terceiros, isentando o <strong>LOCADOR</strong> de qualquer onus.</p>

<h2>CLAUSULA 13 - DO RASTREAMENTO E BLOQUEIO</h2>
<p><strong>13.1.</strong> O <strong>LOCATARIO</strong> declara estar ciente e de acordo que o veiculo possui sistema de rastreamento e monitoramento, que podera ser utilizado pelo <strong>LOCADOR</strong> para fins de seguranca e gestao, incluindo o bloqueio remoto em caso de inadimplencia ou violacao contratual.</p>
<p><strong>13.2.</strong> O <strong>LOCADOR</strong> fica autorizado a bloquear o funcionamento do veiculo em caso de inadimplencia (Clausula 4.5), uso irregular ou termino do contrato sem a devida devolucao.</p>

<h2>CLAUSULA 14 - DA AUSENCIA DE SOCIEDADE OU PARCERIA</h2>
<p>O presente contrato nao estabelece qualquer vinculo societario, associacao, parceria, joint venture ou relacao de cooperacao empresarial entre as partes, limitando-se a locacao de bem movel.</p>

<h2>CLAUSULA 15 - DA RESCISAO</h2>
<p><strong>15.1.</strong> A violacao de qualquer clausula deste contrato, especialmente as de conduta (Clausula 6) e de comunicacao de sinistro (Clausula 8), sera considerada falta grave e quebra contratual, autorizando o <strong>LOCADOR</strong> a rescindir o contrato de pleno direito, retomar o veiculo e cobrar as multas e prejuizos cabiveis.</p>
<p><strong>15.2.</strong> Em caso de rescisao, o <strong>LOCATARIO</strong> devera devolver o veiculo imediatamente, sob pena de multa diaria de R$ 250,00 (duzentos e cinquenta reais), sem prejuizo das demais medidas cabiveis.</p>
<p><strong>15.3.</strong> O presente contrato sera rescindido de pleno direito, mediante notificacao previa, ainda que por meio eletronico, nas seguintes hipoteses:</p>
<p>a) Inadimplencia do <strong>LOCATARIO</strong> por mais de 2 (dois) dias;</p>
<p>b) Uso do veiculo para fins diversos dos previstos neste contrato;</p>
<p>c) Conducao do veiculo por pessoa nao autorizada;</p>
<p>d) Suspensao ou cassacao da CNH do <strong>LOCATARIO</strong>;</p>
<p>e) Falta de pagamento de multas ou da franquia do seguro.</p>
<p><strong>15.4.</strong> A rescisao do contrato nao exime o <strong>LOCATARIO</strong> do pagamento de todos os debitos pendentes.</p>
<p><strong>15.5.</strong> O nao pagamento de qualquer debito na data de vencimento autoriza o <strong>LOCADOR</strong>, apos previa notificacao ao <strong>LOCATARIO</strong> nos termos da lei, a realizar o protesto do contrato e a inscrever o nome do <strong>LOCATARIO</strong> nos cadastros de orgaos de protecao ao credito (SPC, Serasa, etc.), correndo por conta do devedor todas as despesas de cobranca.</p>
<p><strong>15.6.</strong> Caso qualquer das partes decida rescindir este contrato antes do prazo final estipulado na Clausula 3.1, sem que haja justa causa motivada por descumprimento da outra parte, sera aplicada a seguinte multa compensatoria: a parte que der causa a rescisao antecipada pagara a outra uma multa no valor de 20% (vinte por cento) do total dos alugueis que seriam devidos ate o termino do prazo contratual.</p>

<h2>CLAUSULA 16 - DA PRIVACIDADE E PROTECAO DE DADOS (LGPD)</h2>
<p><strong>16.1.</strong> O <strong>LOCATARIO</strong> declara ciencia e consente, de forma livre, informada e inequivoca, que o <strong>LOCADOR</strong>, na qualidade de Controlador, realize o tratamento de seus dados pessoais (nome, CPF, CNH, endereco, telefone) e dados de geolocalizacao do veiculo, coletados atraves de dispositivo de rastreamento (GPS).</p>
<p><strong>16.2.</strong> O tratamento dos dados tem como base legal a execucao deste contrato (Art. 7, V, LGPD) e o legitimo interesse do <strong>LOCADOR</strong> (Art. 7, IX, LGPD), com as seguintes finalidades:</p>
<p>a) Monitorar o veiculo para fins de seguranca, prevencao a fraudes, roubo, furto e para sua pronta recuperacao.</p>
<p>b) Verificar o cumprimento da franquia de quilometragem, identificar o local de infracoes de transito e, em caso de inadimplemento ou quebra contratual, facilitar o bloqueio e a retomada do veiculo.</p>
<p>c) Compartilhar dados com autoridades policiais, judiciais ou de transito, quando legalmente requisitado.</p>
<p><strong>16.3.</strong> O <strong>LOCADOR</strong> podera compartilhar os dados do <strong>LOCATARIO</strong> e do veiculo com seguradoras (em caso de sinistro), empresas de gestao de multas, prestadores de servico de rastreamento e, se necessario, com escritorios de advocacia para cobranca ou outras medidas judiciais.</p>
<p><strong>16.4.</strong> Os dados serao armazenados em ambiente seguro pelo prazo necessario para o cumprimento das finalidades contratuais e legais. O <strong>LOCATARIO</strong>, na qualidade de titular, podera exercer seus direitos previstos na LGPD (confirmacao, acesso, correcao, etc.) atraves de solicitacao direta ao <strong>LOCADOR</strong>.</p>
<p><strong>16.5.</strong> O <strong>LOCATARIO</strong> declara ter sido inequivocamente informado da existencia do equipamento de rastreamento e concorda que o monitoramento visa exclusivamente a protecao do bem e a correta execucao contratual, nao representando violacao a sua privacidade ou intimidade.</p>

<h2>CLAUSULA 17 - DO FORO</h2>
<p><strong>17.1.</strong> Fica eleito o foro da comarca de Sao Joao da Boa Vista, Estado de Sao Paulo, para dirimir quaisquer litigios decorrentes deste contrato.</p>

<p style="margin-top:20px">E, por estarem justas e contratadas, as partes assinam o presente instrumento em 2 (duas) vias de igual teor e forma.</p>
<p>Sao Joao da Boa Vista, <span class="campo">{data_hoje}</span></p>

<div class="bloco-assinatura">
  <div class="assinante">
    <div class="linha"></div>
    <p>LOCA MAIS CAR LOCACAO DE VEICULOS LTDA</p>
    <p style="font-size:11px;color:#555">{status_locador}</p>
  </div>
  <div class="assinante">
    <div class="linha"></div>
    <p><strong>{cli.nome or "LOCATARIO"}</strong> (LOCATARIO)</p>
    <p style="font-size:11px;color:#555">{status_locatario}</p>
  </div>
</div>

<div style="display:flex;justify-content:space-between;margin-top:40px">
  <div style="width:45%">
    <div style="border-top:1px solid #000;margin-top:50px;margin-bottom:6px"></div>
    <p>Nome: ___________________________ CPF: _______________</p>
  </div>
  <div style="width:45%">
    <div style="border-top:1px solid #000;margin-top:50px;margin-bottom:6px"></div>
    <p>Nome: ___________________________ CPF: _______________</p>
  </div>
</div>

<h2 style="text-align:center;margin-top:40px">APENDICE - TERMO DE VISTORIA DE ENTREGA E DEVOLUCAO</h2>
<p style="text-align:center">Checklist de vistoria do veiculo:</p>
<table>
  <thead>
    <tr><th>Item</th><th>Condicao na Entrega</th><th>Observacoes</th></tr>
  </thead>
  <tbody>
    {"".join([f'<tr><td>{item}</td><td style="text-align:center"><label><input type="radio" name="item_{i}" value="sim"> Sim</label> &nbsp;&nbsp; <label><input type="radio" name="item_{i}" value="nao"> Nao</label></td><td><input type="text" style="width:95%;border:none;border-bottom:1px solid #ccc;outline:none"></td></tr>' for i, item in enumerate(["Pneus","Estepe","Macaco/Chave de Roda","Vidros/Parabrisa","Retrovisores","Faróis/Lanternas","Banco dianteiro/traseiro","Estofamento interno","Painel de instrumentos","Ar-condicionado","Radio/Multimidia","Documentos do veiculo","Chave reserva","Carroceria/Lataria"])])}
  </tbody>
</table>

<div style="display:flex;justify-content:space-between;margin-top:50px">
  <div style="width:40%;text-align:center">
    <div style="border-top:1px solid #000;margin-bottom:6px"></div>
    <p>Assinatura LOCADORA</p>
  </div>
  <div style="width:40%;text-align:center">
    <div style="border-top:1px solid #000;margin-bottom:6px"></div>
    <p>Assinatura LOCATARIO</p>
  </div>
</div>

<div class="no-print secao-digital" style="margin-top:40px;border-top:2px solid #ccc;padding-top:20px">
  <h2 style="text-align:center">Assinaturas Digitais</h2>

  <div class="status-box">
    <h3>Status do Contrato</h3>
    <div class="status-linha">
      <span><strong>Locatario:</strong> {cli.nome or "___"}</span>
      <span>{status_locatario}</span>
    </div>
    <div class="status-linha">
      <span><strong>Locador:</strong> LOCA MAIS CAR</span>
      <span>{status_locador}</span>
    </div>
  </div>

  {'<div class="confirmado"><h3>✓ Contrato Assinado pelo Locatario</h3><p>'+loc_nome+' assinou em '+loc_em+'</p></div>' if loc_assinado else '''
  <div id="area-assinar-locatario">
    <button class="btn-assinar" onclick="document.getElementById('area-assinar-locatario').style.display='none';document.getElementById('form-assinar').style.display='block'">Clique aqui para assinar como Locatario</button>
  </div>
  <div class="assinatura-box" id="form-assinar">
    <p><strong>Para assinar, confirme seus dados:</strong></p>
    <input type="text" id="ass-nome" placeholder="Digite seu nome completo"/>
    <input type="text" id="ass-cpf" placeholder="Digite seu CPF (000.000.000-00)"/>
    <button class="btn-assinar" onclick="assinarLocatario()">Confirmar Assinatura</button>
    <p style="font-size:11px;color:#666;margin-top:10px">Ao clicar em confirmar, voce declara ter lido e concordado com todos os termos deste contrato.</p>
  </div>
  '''}

  <div style="margin-top:20px">
    {'<div class="confirmado"><h3>✓ Contrato Assinado pelo Locador</h3><p>'+loca_nome+' assinou em '+loca_em+'</p></div>' if loca_assinado else '''
    <div id="area-assinar-locador">
      <button class="btn-locador" onclick="assinarLocador()">🔑 Assinar como Locador (Admin)</button>
    </div>
    '''}
  </div>

  <div id="msg-resultado" style="margin-top:10px"></div>
</div>

<script>
const TOKEN = localStorage.getItem('locacar_token') || '';

async function assinarLocatario() {{
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
      document.getElementById('msg-resultado').innerHTML = '<div class="confirmado"><h3>✓ Assinatura registrada!</h3><p>Recarregue a pagina para ver o status atualizado.</p></div>';
      setTimeout(()=>location.reload(), 2000);
    }} else {{
      alert('Erro ao registrar assinatura. Tente novamente.');
    }}
  }} catch(e) {{ alert('Erro de conexao.'); }}
}}

async function assinarLocador() {{
  const token = localStorage.getItem('locacar_token') || '';
  if(!token) {{
    alert('Voce precisa estar logado no painel como administrador para assinar como Locador.');
    return;
  }}
  if(!confirm('Confirmar assinatura como Locador (LOCA MAIS CAR)?')) return;
  try {{
    const res = await fetch('/contratos/{locacao_id}/assinar-locador', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}}
    }});
    if(res.ok) {{
      const data = await res.json();
      document.getElementById('msg-resultado').innerHTML = '<div class="confirmado"><h3>✓ '+data.mensagem+'</h3><p>Recarregando...</p></div>';
      setTimeout(()=>location.reload(), 2000);
    }} else {{
      const err = await res.json();
      alert(err.detail || 'Erro ao assinar. Verifique se voce esta logado como admin.');
    }}
  }} catch(e) {{ alert('Erro de conexao.'); }}
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
    loc.contrato_assinado = True
    loc.contrato_assinado_nome = dados.get("nome")
    loc.contrato_assinado_cpf = dados.get("cpf")
    loc.contrato_assinado_em = datetime.now()
    db.commit()
    return {"mensagem": "Contrato assinado pelo locatario com sucesso!"}

@router.post("/{locacao_id}/assinar-locador")
def assinar_locador(locacao_id: int, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token nao fornecido")
    token = authorization.replace("Bearer ", "")
    try:
        SECRET_KEY = os.environ.get("SECRET_KEY", "locacar_secret")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            raise HTTPException(status_code=401, detail="Usuario nao encontrado")
        if usuario.perfil != "admin":
            raise HTTPException(status_code=403, detail="Apenas administradores podem assinar como locador")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado. Faca login novamente.")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token invalido")
    loc = db.query(Locacao).filter(Locacao.id == locacao_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Locacao nao encontrada")
    loc.locador_assinado = True
    loc.locador_assinado_nome = usuario.nome
    loc.locador_assinado_em = datetime.now()
    db.commit()
    return {"mensagem": f"Contrato assinado por {usuario.nome} em nome da LOCA MAIS CAR!"}
