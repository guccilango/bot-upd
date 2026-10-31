# -*- coding: utf-8 -*-
"""Bilingual (PT / EN) Template and Document Chrome Definitions for UPD Records."""

from typing import Any

DOC_CHROME = {
    "pt": {
        "dept_title": "UNIFIED POLICE DEPARTMENT",
        "dept_sub": "GABINETE DO CHEFE DE POLÍCIA · QUARTEL GENERAL",
        "dept_juris": "Estado de San Andreas · Condado de Los Santos",
        "ctrl_label": "Nº DE CONTROLE:",
        "date_label": "DATA DO REGISTRO:",
        "series_label": "SÉRIE:",
        "status_label": "STATUS:",
        "series_doj": "PROCESSO JUDICIAL · DOJ / TRIBUNAL SUPERIOR",
        "series_internal": "REGISTRO INTERNO DEPARTAMENTAL",
        "status_approved": "APROVADO",
        "status_pending": "MINUTA — PENDENTE DE APROVAÇÃO",
        "status_rejected": "REJEITADO",
        "status_revoked": "REVOGADO",
        "stamp_draft": "MINUTA — AGUARDANDO APROVAÇÃO DO COMANDO",
        "stamp_invalid": "DOCUMENTO INVÁLIDO OU REVOGADO",
        "footer_record": "REGISTRO OFICIAL · Nº DE CONTROLE {ctrl}",
        "footer_verify": "VERIFICAÇÃO DE AUTENTICIDADE: Escaneie o QR Code ou consulte o registro oficial da UPD:",
        "footer_sensitive": "USO RESTRITO POLICIAL",
        "footer_dept": "Unified Police Department · Condado de Los Santos",
        "footer_page": "Página {cur} de {total}",
        "sig_issuer_role": "OFICIAL REQUERENTE / DECLARANTE",
        "sig_approver_role": "AUTORIDADE DE COMANDO RESPONSÁVEL",
        "sig_awaiting": "[ AGUARDANDO CONTRA-ASSINATURA DO COMANDO ]",
        "sig_required": "PATENTE MÍNIMA EXIGIDA: {req}",
        "sig_countersigned": "Contra-Assinado em: {date}",
        "seal_caption": "SELO OFICIAL · AUTENTICADO",
    },
    "en": {
        "dept_title": "UNIFIED POLICE DEPARTMENT",
        "dept_sub": "OFFICE OF THE CHIEF OF POLICE · HEADQUARTERS",
        "dept_juris": "State of San Andreas · County of Los Santos",
        "ctrl_label": "CONTROL NO.:",
        "date_label": "DATE OF RECORD:",
        "series_label": "SERIES:",
        "status_label": "STATUS:",
        "series_doj": "JUDICIAL FILING · DOJ / SUPERIOR COURT",
        "series_internal": "INTERNAL DEPARTMENTAL RECORD",
        "status_approved": "APPROVED",
        "status_pending": "PENDING APPROVAL",
        "status_rejected": "REJECTED",
        "status_revoked": "REVOKED",
        "stamp_draft": "DRAFT — PENDING COMMAND APPROVAL",
        "stamp_invalid": "INVALID OR REVOKED RECORD",
        "footer_record": "OFFICIAL RECORD · CONTROL NO. {ctrl}",
        "footer_verify": "AUTHENTICITY VERIFICATION: Scan QR or verify control number at official UPD Registry:",
        "footer_sensitive": "LAW ENFORCEMENT SENSITIVE",
        "footer_dept": "Unified Police Department · County of Los Santos",
        "footer_page": "Page {cur} of {total}",
        "sig_issuer_role": "SUBMITTING / AFFIANT OFFICER",
        "sig_approver_role": "APPROVING COMMAND AUTHORITY",
        "sig_awaiting": "[ AWAITING COMMAND COUNTER-SIGNATURE ]",
        "sig_required": "REQUIRED RANK LEVEL: {req}",
        "sig_countersigned": "Counter-Signed: {date}",
        "seal_caption": "OFFICIAL SEAL · AUTHENTICATED",
    },
}

DOC_TEMPLATES: dict[str, dict[str, dict[str, Any]]] = {
    "SW": {
        "pt": {
            "name": "Mandado de Busca e Apreensão",
            "title": "DECLARAÇÃO JURAMENTADA E PEDIDO DE MANDADO DE BUSCA E APREENSÃO",
            "court_header": "NO TRIBUNAL SUPERIOR DO ESTADO DE SAN ANDREAS\nNO E PARA O CONDADO DE LOS SANTOS",
            "body": (
                "<b>PROCESSO / DOCKET Nº:</b> {case_no}\n"
                "<b>ALVO(S) DA INVESTIGAÇÃO:</b> {target_subject}\n"
                "<b>VIOLAÇÕES PENAIS:</b> {statutes_violated}\n"
                "<b>PARÂMETROS DE EXECUÇÃO:</b> {night_service}\n\n"
                "<b>I. DECLARAÇÃO JURAMENTADA DO OFICIAL DECLARANTE</b>\n"
                "Eu, <b>{issuer_name}</b>, Distintivo <b>#{issuer_badge}</b>, ocupante do posto de <b>{issuer_rank}</b> "
                "do Unified Police Department (UPD), prestando compromisso legal sob pena de perjúrio sob as leis do Estado "
                "de San Andreas, declaro ter fundada suspeita e causa provável para crer que evidências materiais de crime grave "
                "encontram-se ocultadas no local abaixo descrito.\n\n"
                "<b>II. DESCRIÇÃO PORMENORIZADA DO IMÓVEL / LOCAL</b>\n"
                "{target_premises}\n\n"
                "<b>III. BENS E EVIDÊNCIAS A SEREM APREENDIDOS (ANEXO A)</b>\n"
                "{items_to_seize}\n\n"
                "<b>IV. DEMONSTRAÇÃO DE CAUSA PROVÁVEL E CIRCUNSTÂNCIAS DOS FATOS</b>\n"
                "{probable_cause}\n\n"
                "<b>V. REQUERIMENTO FINAL</b>\n"
                "Diante do exposto, o Declarante requer a expedição do competente Mandado de Busca e Apreensão por este Tribunal Superior, "
                "autorizando qualquer Oficial de Paz do Unified Police Department a adentrar as dependências descritas e apreender os bens especificados."
            ),
            "fields": [
                {"key": "case_no", "label": "Nº do Processo / Docket", "type": "text", "required": True, "max_length": 60, "placeholder": "26-CR-00418"},
                {"key": "target_subject", "label": "Alvo(s) da Investigação / Ocupante(s)", "type": "text", "required": True, "max_length": 200, "placeholder": "Nome completo, data de nascimento e identificadores conhecidos"},
                {"key": "target_premises", "label": "Local da Busca (Endereço e Descrição Completa)", "type": "textarea", "required": True, "max_length": 800, "placeholder": "Endereço completo e características físicas do imóvel..."},
                {"key": "statutes_violated", "label": "Infrações Penais / Artigos do Código Penal", "type": "text", "required": True, "max_length": 300, "placeholder": "Artigos infringidos do Código Penal de San Andreas"},
                {"key": "items_to_seize", "label": "Bens e Evidências a Serem Apreendidos (Anexo A)", "type": "textarea", "required": True, "max_length": 1500, "placeholder": "1. Armas de fogo, munições e carregadores;\n2. Dispositivos de comunicação e mídias;\n3. Documentos e comprovantes."},
                {"key": "probable_cause", "label": "Declaração de Causa Provável (Fatos e Investigação)", "type": "textarea", "required": True, "max_length": 3500, "placeholder": "Narrativa detalhada dos atos investigatórios e demonstração dos indícios..."},
                {"key": "night_service", "label": "Horário de Cumprimento e Dispensa de Notificação", "type": "text", "required": True, "max_length": 200, "placeholder": "Cumprimento diurno padrão (07h às 22h)"},
            ],
        },
        "en": {
            "name": "Affidavit and Application for Search Warrant",
            "title": "AFFIDAVIT AND APPLICATION FOR A SEARCH WARRANT",
            "court_header": "IN THE SUPERIOR COURT OF THE STATE OF SAN ANDREAS\nIN AND FOR THE COUNTY OF LOS SANTOS",
            "body": (
                "<b>CASE DOCKET NO.:</b> {case_no}\n"
                "<b>TARGET SUBJECT(S):</b> {target_subject}\n"
                "<b>STATUTORY VIOLATIONS:</b> {statutes_violated}\n"
                "<b>EXECUTION PARAMETERS:</b> {night_service}\n\n"
                "<b>I. SWORN DECLARATION OF AFFIANT</b>\n"
                "I, <b>{issuer_name}</b>, Badge No. <b>#{issuer_badge}</b>, holding the rank of <b>{issuer_rank}</b> "
                "with the Unified Police Department (UPD), being first duly sworn, hereby depose and state under penalty "
                "of perjury under the laws of the State of San Andreas that I have probable cause to believe, and do believe, "
                "that evidence of a felony crime is presently concealed at the premises described below.\n\n"
                "<b>II. PARTICULAR DESCRIPTION OF PREMISES TO BE SEARCHED</b>\n"
                "{target_premises}\n\n"
                "<b>III. PARTICULAR DESCRIPTION OF PROPERTY & EVIDENCE TO BE SEIZED (SCHEDULE A)</b>\n"
                "{items_to_seize}\n\n"
                "<b>IV. STATEMENT OF PROBABLE CAUSE</b>\n"
                "{probable_cause}\n\n"
                "<b>V. PRAYER FOR ORDER</b>\n"
                "WHEREFORE, Affiant prays that a Search Warrant be issued by the Superior Court commanding any Peace Officer "
                "of the Unified Police Department to search the above-described premises and seize the enumerated property for disposition in accordance with law."
            ),
        },
    },
    "AW": {
        "pt": {
            "name": "Mandado de Prisão",
            "title": "DECLARAÇÃO DE CAUSA PROVÁVEL PARA MANDADO DE PRISÃO",
            "court_header": "NO TRIBUNAL SUPERIOR DO ESTADO DE SAN ANDREAS\nNO E PARA O CONDADO DE LOS SANTOS",
            "body": (
                "<b>PROCESSO / DOCKET Nº:</b> {case_no}\n"
                "<b>INDICIADO / RÉU:</b> {defendant_name}\n"
                "<b>ÚLTIMO ENDEREÇO CONHECIDO:</b> {last_known_address}\n"
                "<b>STATUS DE FIANÇA RECOMENDADO:</b> {bail_request}\n\n"
                "<b>I. REPRESENTAÇÃO FORMAL DE PRISÃO</b>\n"
                "Perante o Tribunal Superior do Estado de San Andreas, comparece o oficial <b>{issuer_name}</b> "
                "({issuer_rank}, Distintivo #{issuer_badge}), do Unified Police Department, o qual, prestando compromisso legal, "
                "declara sob pena da lei que no Condado de Los Santos o réu acima nominado praticou os crimes especificados nesta representação.\n\n"
                "<b>II. IMPUTAÇÕES E DISPOSITIVOS PENAIS</b>\n"
                "{charges}\n\n"
                "<b>III. DEMONSTRAÇÃO DE CAUSA PROVÁVEL E INDÍCIOS DE AUTORIA</b>\n"
                "{probable_cause}\n\n"
                "<b>IV. PEDIDO DE MANDADO DE PRISÃO</b>\n"
                "Diante do exposto, o Declarante requer a expedição de Mandado de Prisão autorizando qualquer Oficial de Paz a capturar e apresentar o réu perante o Magistrado competente."
            ),
            "fields": [
                {"key": "case_no", "label": "Nº do Processo / Docket", "type": "text", "required": True, "max_length": 60, "placeholder": "26-CR-00419"},
                {"key": "defendant_name", "label": "Nome Completo do Réu e Dados", "type": "text", "required": True, "max_length": 250, "placeholder": "Nome Completo · RG / ID · Data de Nascimento"},
                {"key": "last_known_address", "label": "Último Endereço / Local Conhecido", "type": "text", "required": True, "max_length": 250, "placeholder": "Último endereço conhecido em Los Santos, SA"},
                {"key": "charges", "label": "Imputações Penais (Artigos e Contagens)", "type": "textarea", "required": True, "max_length": 800, "placeholder": "Contagem 1: Artigo penal e tipificação"},
                {"key": "probable_cause", "label": "Demonstração de Causa Provável", "type": "textarea", "required": True, "max_length": 3500, "placeholder": "Fatos demonstrando a materialidade delitiva e os indícios suficientes de autoria..."},
                {"key": "bail_request", "label": "Recomendação de Fiança / Custódia", "type": "text", "required": True, "max_length": 150, "placeholder": "Prisão Preventiva / Sem Fiança — Risco à Ordem Pública"},
            ],
        },
        "en": {
            "name": "Affidavit and Application for Arrest Warrant",
            "title": "AFFIDAVIT OF PROBABLE CAUSE FOR ARREST WARRANT",
            "court_header": "IN THE SUPERIOR COURT OF THE STATE OF SAN ANDREAS\nIN AND FOR THE COUNTY OF LOS SANTOS",
            "body": (
                "<b>CASE DOCKET NO.:</b> {case_no}\n"
                "<b>DEFENDANT:</b> {defendant_name}\n"
                "<b>LAST KNOWN ADDRESS:</b> {last_known_address}\n"
                "<b>RECOMMENDED BAIL STATUS:</b> {bail_request}\n\n"
                "<b>I. SWORN COMPLAINT & AFFIDAVIT</b>\n"
                "Before the Superior Court of the State of San Andreas personally appeared <b>{issuer_name}</b> "
                "({issuer_rank}, Badge #{issuer_badge}), of the Unified Police Department, who, being first duly sworn, "
                "deposes and says that within the County of Los Santos the above-named Defendant committed the offenses set forth herein.\n\n"
                "<b>II. ENUMERATED CRIMINAL CHARGES</b>\n"
                "{charges}\n\n"
                "<b>III. STATEMENT OF PROBABLE CAUSE</b>\n"
                "{probable_cause}\n\n"
                "<b>IV. REQUEST FOR ISSUANCE OF WARRANT</b>\n"
                "WHEREFORE, Affiant requests that a Warrant of Arrest be issued authorizing any Peace Officer of the State "
                "of San Andreas to apprehend and bring the above-named Defendant before a Magistrate of the Superior Court."
            ),
        },
    },
    "CO": {
        "pt": {
            "name": "Quebra de Sigilo e Registros (18 U.S.C. § 2703(d))",
            "title": "REQUERIMENTO DE ORDEM JUDICIAL PARA QUEBRA DE SIGILO E REGISTROS\nNOS TERMOS DO 18 U.S.C. § 2703(d) E LEI DE PRIVACIDADE FINANCEIRA",
            "court_header": "NO TRIBUNAL SUPERIOR DO ESTADO DE SAN ANDREAS\nNO E PARA O CONDADO DE LOS SANTOS",
            "body": (
                "<b>INQUÉRITO / REGISTRO Nº:</b> {case_no}\n"
                "<b>IDENTIFICADOR / TITULAR DO ALVO:</b> {target_account}\n"
                "<b>CUSTODIANTE DOS REGISTROS:</b> {custodian_entity}\n"
                "<b>PRAZO DE SIGILO E NÃO DIVULGAÇÃO:</b> {nondisclosure_period}\n\n"
                "<b>I. REQUERIMENTO LEGAL</b>\n"
                "<b>{issuer_name}</b> ({issuer_rank}, Distintivo #{issuer_badge}), investigador juramentado do Unified Police Department, "
                "requer a este Tribunal Superior a expedição de Ordem Judicial nos termos do 18 U.S.C. § 2703(d) determinando "
                "que <b>{custodian_entity}</b> forneça os dados especificados a seguir.\n\n"
                "<b>II. REGISTROS E DADOS REQUISITADOS</b>\n"
                "{records_scope}\n\n"
                "<b>III. FATOS ARTICULADOS E RELEVÂNCIA PROBATÓRIA</b>\n"
                "{articulable_facts}"
            ),
            "fields": [
                {"key": "case_no", "label": "Nº do Inquérito / Investigação", "type": "text", "required": True, "max_length": 60, "placeholder": "26-INV-00109"},
                {"key": "target_account", "label": "Alvo e Conta / Telefone / Identificador", "type": "text", "required": True, "max_length": 250, "placeholder": "Número de conta / Linha telefônica e titular"},
                {"key": "custodian_entity", "label": "Provedor do Serviço / Instituição Financeira", "type": "text", "required": True, "max_length": 200, "placeholder": "Instituição bancária ou operadora de telecomunicações"},
                {"key": "records_scope", "label": "Escopo dos Dados e Período Requisitado", "type": "textarea", "required": True, "max_length": 1200, "placeholder": "Extratos, registros de chamadas, dados cadastrais e intervalo temporal..."},
                {"key": "articulable_facts", "label": "Fatos Concretos e Articulados (Relevância Legal)", "type": "textarea", "required": True, "max_length": 3500, "placeholder": "Demonstração de fatos concretos evidenciando a imprescindibilidade dos registros..."},
                {"key": "nondisclosure_period", "label": "Pedido de Sigilo e Não Divulgação", "type": "text", "required": True, "max_length": 150, "placeholder": "Sigilo Absoluto por 90 dias (18 U.S.C. § 2705(b))"},
            ],
        },
        "en": {
            "name": "Application for Court Order — Disclosure of Records (18 U.S.C. § 2703(d))",
            "title": "APPLICATION FOR COURT ORDER FOR DISCLOSURE OF RECORDS\nPURSUANT TO 18 U.S.C. § 2703(d) & S.A. FINANCIAL PRIVACY ACT",
            "court_header": "IN THE SUPERIOR COURT OF THE STATE OF SAN ANDREAS\nIN AND FOR THE COUNTY OF LOS SANTOS",
            "body": (
                "<b>INVESTIGATION NO.:</b> {case_no}\n"
                "<b>TARGET IDENTIFIER / SUBSCRIBER:</b> {target_account}\n"
                "<b>CUSTODIAN OF RECORDS:</b> {custodian_entity}\n"
                "<b>SEALING & NON-DISCLOSURE:</b> {nondisclosure_period}\n\n"
                "<b>I. STATUTORY APPLICATION</b>\n"
                "<b>{issuer_name}</b> ({issuer_rank}, Badge #{issuer_badge}), a sworn investigator of the Unified Police Department, "
                "hereby applies to the Superior Court for an Order pursuant to 18 U.S.C. § 2703(d) compelling "
                "<b>{custodian_entity}</b> to disclose the records specified below.\n\n"
                "<b>II. RECORDS & DATA TO BE PRODUCED</b>\n"
                "{records_scope}\n\n"
                "<b>III. SPECIFIC AND ARTICULABLE FACTS</b>\n"
                "{articulable_facts}"
            ),
        },
    },
    "SO": {
        "pt": {
            "name": "Operação de Pacificação Comunitária (SMEAC)",
            "title": "PEDIDO DE AUTORIZAÇÃO JUDICIAL E EXECUTIVA\nOPERAÇÃO ESPECIAL TÁTICA E PACIFICAÇÃO COMUNITÁRIA (SMEAC)",
            "court_header": "PERANTE O DEPARTAMENTO DE JUSTIÇA E TRIBUNAL SUPERIOR\nESTADO DE SAN ANDREAS · CONDADO DE LOS SANTOS",
            "body": (
                "<b>DESIGNAÇÃO DA OPERAÇÃO:</b> {operation_name}\n"
                "<b>JANELA OPERACIONAL:</b> {operational_window}\n"
                "<b>OFICIAL DE COMANDO RESPONSÁVEL:</b> {issuer_name} ({issuer_rank}, Distintivo #{issuer_badge})\n\n"
                "<b>I. SITUAÇÃO E INTELIGÊNCIA OPERACIONAL</b>\n"
                "{situation}\n\n"
                "<b>II. DECLARAÇÃO DE MISSÃO</b>\n"
                "{mission}\n\n"
                "<b>III. PLANO DE EXECUÇÃO E FASES TÁTICAS</b>\n"
                "{execution}\n\n"
                "<b>IV. REGRAS DE ENGAJAMENTO E SALVAGUARDAS CONSTITUCIONAIS</b>\n"
                "{roe_safeguards}"
            ),
            "fields": [
                {"key": "operation_name", "label": "Codinome da Operação e Zona Designada", "type": "text", "required": True, "max_length": 200, "placeholder": "Codinome da operação e setor geográfico"},
                {"key": "operational_window", "label": "Janela Operacional (Início e Fim / Horários)", "type": "text", "required": True, "max_length": 150, "placeholder": "Data e horário de início e encerramento previsto"},
                {"key": "situation", "label": "1. SITUAÇÃO (Inteligência e Ameaça Armada)", "type": "textarea", "required": True, "max_length": 1500, "placeholder": "Inteligência sobre facções, atuação armada e crimes violentos no setor..."},
                {"key": "mission", "label": "2. MISSÃO OPERACIONAL", "type": "textarea", "required": True, "max_length": 800, "placeholder": "Objetivos táticos e metas de estabilização comunitária..."},
                {"key": "execution", "label": "3. EXECUÇÃO E FASES TÁTICAS (Unidades e Perímetros)", "type": "textarea", "required": True, "max_length": 1500, "placeholder": "Fases da operação, unidades empenhadas e pontos de bloqueio..."},
                {"key": "roe_safeguards", "label": "4. REGRAS DE ENGAJAMENTO E SALVAGUARDAS", "type": "textarea", "required": True, "max_length": 1000, "placeholder": "Uso progressivo da força, câmeras operacionais e suporte médico..."},
            ],
        },
        "en": {
            "name": "Request for Authorization — Community Stabilization Operation (SMEAC)",
            "title": "REQUEST FOR JUDICIAL & EXECUTIVE AUTHORIZATION\nSPECIAL TACTICAL & COMMUNITY STABILIZATION OPERATION (SMEAC)",
            "court_header": "BEFORE THE DEPARTMENT OF JUSTICE & SUPERIOR COURT\nSTATE OF SAN ANDREAS · COUNTY OF LOS SANTOS",
            "body": (
                "<b>OPERATION DESIGNATION:</b> {operation_name}\n"
                "<b>OPERATIONAL WINDOW:</b> {operational_window}\n"
                "<b>FILING COMMAND OFFICER:</b> {issuer_name} ({issuer_rank}, Badge #{issuer_badge})\n\n"
                "<b>I. SITUATION & INTELLIGENCE ASSESSMENT</b>\n"
                "{situation}\n\n"
                "<b>II. MISSION</b>\n"
                "{mission}\n\n"
                "<b>III. EXECUTION PLAN (PHASES & DEPLOYED UNITS)</b>\n"
                "{execution}\n\n"
                "<b>IV. RULES OF ENGAGEMENT & SAFEGUARDS</b>\n"
                "{roe_safeguards}"
            ),
        },
    },
    "FQ": {
        "pt": {
            "name": "Certificado e Porte de Armas de Fogo UPD",
            "title": "CERTIFICADO DE QUALIFICAÇÃO EM ARMAS DE FOGO\nE AUTORIZAÇÃO DE CUSTÓDIA DE ARMAMENTO DEPARTAMENTAL",
            "court_header": "UNIFIED POLICE DEPARTMENT · DIVISÃO DE TIRO E TREINAMENTO COM ARMAS\nCERTIFICAÇÃO OFICIAL POST DO ESTADO DE SAN ANDREAS",
            "body": (
                "<b>INDIVÍDUO AUTORIZADO:</b> {holder_name} (Documento ID: {holder_id})\n"
                "<b>Nº DO PROCESSO / REGISTRO DOJ:</b> {doj_permit_ref}\n"
                "<b>INSTRUTOR RESPONSÁVEL:</b> {issuer_name} ({issuer_rank}, Distintivo #{issuer_badge})\n\n"
                "<b>I. ATESTADO DE APTIDÃO EM TIRO</b>\n"
                "Em conformidade com a autorização do Departamento de Justiça (<b>{doj_permit_ref}</b>), a Divisão de Tiro "
                "do Unified Police Department certifica que <b>{holder_name}</b> concluiu satisfatoriamente a instrução e avaliação prática de tiro:\n\n"
                "<b>Resultado da Qualificação:</b> {course_score}\n\n"
                "<b>II. TERMO DE CUSTÓDIA E POSSE DE ARMAMENTO DO UPD</b>\n"
                "O armamento abaixo identificado permanece, a todo momento, como patrimônio exclusivo do <b>Unified Police Department (UPD)</b>:\n\n"
                "<b>Armamento Designado:</b> {weapon_details}\n\n"
                "<b>Condições de Custódia e Uso:</b>\n"
                "{conditions}"
            ),
            "fields": [
                {"key": "holder_name", "label": "Nome Completo do Cidadão / Agente", "type": "text", "required": True, "max_length": 150, "placeholder": "Nome Completo"},
                {"key": "holder_id", "label": "Documento ID Estadual / RG / Passaporte", "type": "text", "required": True, "max_length": 60, "placeholder": "SA-ID #00000"},
                {"key": "doj_permit_ref", "label": "Porte DOJ / Nº do Protocolo", "type": "text", "required": True, "max_length": 100, "placeholder": "DOJ-CCW-2026-0001"},
                {"key": "course_score", "label": "Curso de Tiro e Aproveitamento", "type": "text", "required": True, "max_length": 150, "placeholder": "Curso de Combate e Tiro Defensivo — Nota: 98/100 (QUALIFICADO)"},
                {"key": "weapon_details", "label": "Armamento Designado (Marca, Modelo, Calibre e Nº Série)", "type": "text", "required": True, "max_length": 250, "placeholder": "Glock 17 Gen 5 · 9x19mm · Nº de Série UPD-ARM-0001"},
                {"key": "conditions", "label": "Termos de Custódia e Restrições de Uso", "type": "textarea", "required": True, "max_length": 800, "placeholder": "Armamento de propriedade exclusiva da UPD. Portador certificado em manuseio seguro, retenção e uso proporcional da força."},
            ],
        },
        "en": {
            "name": "Certificate of Firearms Qualification & UPD Weapon Authorization",
            "title": "CERTIFICATE OF FIREARMS QUALIFICATION\n& DEPARTMENTAL WEAPON CUSTODY AUTHORIZATION",
            "court_header": "UNIFIED POLICE DEPARTMENT · FIREARMS TRAINING & RANGE DIVISION\nSTATE OF SAN ANDREAS POST CERTIFICATION",
            "body": (
                "<b>CERTIFIED INDIVIDUAL:</b> {holder_name} (State ID: {holder_id})\n"
                "<b>DOJ PERMIT / REFERRAL NO.:</b> {doj_permit_ref}\n"
                "<b>ISSUING INSTRUCTOR:</b> {issuer_name} ({issuer_rank}, Badge #{issuer_badge})\n\n"
                "<b>I. ATTESTATION OF FIREARMS QUALIFICATION</b>\n"
                "Pursuant to the referral of the Department of Justice (<b>{doj_permit_ref}</b>), the Unified Police Department "
                "Firearms Training Division hereby certifies that <b>{holder_name}</b> has satisfactorily completed mandatory "
                "instruction and live-fire proficiency:\n\n"
                "<b>Qualification Result:</b> {course_score}\n\n"
                "<b>II. DECLARATION OF UPD WEAPON OWNERSHIP & AUTHORIZATION TO HANDLE</b>\n"
                "The firearm identified below is, and at all times remains, the official property of the <b>Unified Police Department (UPD)</b>:\n\n"
                "<b>Assigned Firearm:</b> {weapon_details}\n\n"
                "<b>Conditions of Custody:</b>\n"
                "{conditions}"
            ),
        },
    },
    "CM": {
        "pt": {
            "name": "Elogio e Condecoração Policial",
            "title": "CONDECORAÇÃO E ELOGIO DEPARTAMENTAL OFICIAL\nGABINETE DO CHEFE DE POLÍCIA",
            "court_header": "UNIFIED POLICE DEPARTMENT · CONSELHO DE HONRARIAS E CONDECORAÇÕES\nCONDADO DE LOS SANTOS, ESTADO DE SAN ANDREAS",
            "body": (
                "<b>PARA:</b> {recipient_name}\n"
                "<b>HONRARIA / CONDECORAÇÃO:</b> {award_class}\n"
                "<b>DATA E LOCAL DO ATO:</b> {incident_date}\n"
                "<b>SUPERVISOR PROPORENTE:</b> {issuer_name} ({issuer_rank}, Distintivo #{issuer_badge})\n\n"
                "<b>CITAÇÃO POR SERVIÇO RELEVANTE E CORAGEM</b>\n"
                "O Comando do Unified Police Department confere o presente Elogio Departamental Oficial a <b>{recipient_name}</b> "
                "em reconhecimento ao exemplar profissionalismo, distinção e bravura em cumprimento do dever policial:\n\n"
                "{citation_narrative}"
            ),
            "fields": [
                {"key": "recipient_name", "label": "Oficial Homenageado (Nome e Distintivo)", "type": "text", "required": True, "max_length": 150, "placeholder": "Oficial Nome e Distintivo #"},
                {"key": "award_class", "label": "Classe da Condecoração / Honraria", "type": "text", "required": True, "max_length": 120, "placeholder": "Medalha de Bravura / Citação de Honra ao Mérito"},
                {"key": "incident_date", "label": "Data e Local do Ato Meritório", "type": "text", "required": True, "max_length": 150, "placeholder": "Data e localização do ato"},
                {"key": "citation_narrative", "label": "Narrativa dos Fatos e Justificativa do Elogio", "type": "textarea", "required": True, "max_length": 2500, "placeholder": "Narrativa pormenorizada dos fatos e bravura..."},
            ],
        },
        "en": {
            "name": "Official Departmental Commendation",
            "title": "OFFICIAL DEPARTMENTAL COMMENDATION\nOFFICE OF THE CHIEF OF POLICE",
            "court_header": "UNIFIED POLICE DEPARTMENT · HONORS & AWARDS BOARD\nCOUNTY OF LOS SANTOS, STATE OF SAN ANDREAS",
            "body": (
                "<b>TO:</b> {recipient_name}\n"
                "<b>DECORATION CONFERRED:</b> {award_class}\n"
                "<b>DATE & LOCATION OF ACTION:</b> {incident_date}\n"
                "<b>NOMINATING SUPERVISOR:</b> {issuer_name} ({issuer_rank}, Badge #{issuer_badge})\n\n"
                "<b>CITATION FOR MERITORIOUS SERVICE</b>\n"
                "The Command Staff of the Unified Police Department presents this Official Commendation to "
                "<b>{recipient_name}</b> in recognition of exceptional professionalism and courage:\n\n"
                "{citation_narrative}"
            ),
        },
    },
}


def get_chrome(lang: str = "pt") -> dict[str, str]:
    return DOC_CHROME.get(lang.lower(), DOC_CHROME["pt"])


def resolve_template_text(code: str, fallback_snap: dict[str, Any], lang: str = "pt") -> dict[str, Any]:
    code = code.upper()
    lang = lang.lower() if lang in ("pt", "en") else "pt"
    tpl_info = DOC_TEMPLATES.get(code, {}).get(lang)
    if not tpl_info:
        return fallback_snap

    merged = dict(fallback_snap)
    merged["name"] = tpl_info.get("name", fallback_snap.get("name"))
    merged["title"] = tpl_info.get("title", fallback_snap.get("title"))
    merged["court_header"] = tpl_info.get("court_header", fallback_snap.get("court_header"))
    merged["body"] = tpl_info.get("body", fallback_snap.get("body"))
    if "fields" in tpl_info:
        merged["fields"] = tpl_info["fields"]
    return merged
