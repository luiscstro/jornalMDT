"""
regioes_engine.py
------------------
Motor de geração dos boletins a partir dos dados dinâmicos em regioes_db.
Substitui a lógica que antes estava hardcoded em jornal.py
(ILHAS_MARITIMAS, CLIMA_OPCOES, RUMOR_TEMPLATES, PARADISE_*).

Qualquer região cadastrada via /regioes (com locais, grupos de template e,
opcionalmente, clima) é suportada automaticamente — sem precisar tocar em
código para adicionar um "Novo Mundo", "Calm Belt" etc.
"""

import random
import database as db  # planilha do Google com os procurados/marinheiros
import regioes_db as rdb


def _sortear_local(locais: list, ja_usados: set, forcar_unico: bool):
    """Sorteia um local (nome) da lista, opcionalmente evitando repetir os
    já usados nesta mensagem (usado por regiões com locais_unicos_por_grupo)."""
    if not locais:
        return None
    if forcar_unico:
        disponiveis = [l for l in locais if l["nome"] not in ja_usados]
        if not disponiveis:
            disponiveis = locais  # acabaram opções únicas, permite repetir
        escolhido = random.choice(disponiveis)
    else:
        escolhido = random.choice(locais)
    ja_usados.add(escolhido["nome"])
    return escolhido["nome"]


def gerar_boletim_regiao(regiao: dict, pool_procurados: list, teste: bool = False) -> tuple:
    """Gera o texto de UMA região a partir da configuração salva no banco.
    `pool_procurados` é consumido (pop) para não repetir entre regiões,
    igual ao comportamento original.

    Retorna (texto, nome_procurado_usado_ou_None)."""

    regiao_id = regiao["id"]
    nome_regiao = regiao["nome"]
    locais = rdb.listar_locais(regiao_id)
    ja_usados = set()

    titulo_teste = "[TESTE] " if teste else ""
    cabecalho = regiao["cabecalho_template"].format(teste=titulo_teste, regiao=nome_regiao.upper())
    introducao = regiao["introducao_template"].format(regiao=nome_regiao)

    linhas = []
    nome_usado = None

    # --- grupos de template (rumores, mestre, nakama, tesouro, etc) ---
    for grupo in rdb.listar_grupos_template(regiao_id):
        variacoes = rdb.listar_variacoes(grupo["id"])
        if not variacoes:
            continue
        texto = rdb.sortear_com_peso(variacoes, chave_texto="texto")
        if grupo["usa_local"] and "{local}" in texto:
            local_sorteado = _sortear_local(locais, ja_usados, bool(regiao["locais_unicos_por_grupo"]))
            texto = texto.format(local=local_sorteado or "???")
        linhas.append(f"- {texto}")

    # --- procurado / marinheiro (pool compartilhado entre regiões) ---
    if regiao["tem_procurado"]:
        if pool_procurados:
            nome_p, tipo_p = pool_procurados.pop(0)
            nome_usado = nome_p
            local_p = _sortear_local(locais, ja_usados, False) or "???"
            if tipo_p == "Marinheiro":
                texto_p = regiao["procurado_marinheiro_texto"].format(local=local_p, nome=nome_p)
            else:
                texto_p = regiao["procurado_pirata_texto"].format(local=local_p, nome=nome_p, nome_upper=nome_p.upper())
        else:
            texto_p = regiao["procurado_vazio_texto"]
        linhas.append(f"- {texto_p}")

    corpo = "\n".join(linhas)

    partes = [cabecalho, "", introducao, corpo]

    # --- clima (opcional) ---
    if regiao["tem_clima"]:
        titulo_clima = regiao["clima_titulo_template"].format(regiao=nome_regiao)
        linhas_clima = []
        for categoria in rdb.listar_categorias_clima(regiao_id):
            opcoes = rdb.listar_opcoes_clima(categoria["id"])
            if not opcoes:
                continue
            opcao_sorteada = rdb.sortear_com_peso(opcoes, chave_texto="opcao")
            frase = categoria["frase"].format(categoria=categoria["nome"], opcao=opcao_sorteada.upper())
            linhas_clima.append(frase)
        if linhas_clima:
            partes += ["", titulo_clima, "\n".join(linhas_clima)]

    if regiao["mencoes_texto"]:
        partes += ["", regiao["mencoes_texto"]]

    return "\n".join(p for p in partes if p is not None) + "\n", nome_usado


def gerar_todos_boletins(teste: bool = False) -> tuple:
    """Gera o texto de todas as regiões ativas, na ordem configurada.
    Retorna ({nome_regiao: texto}, [nomes_de_procurados_usados_nesta_edição])."""
    regioes = rdb.listar_regioes(apenas_ativas=True)

    pool_procurados = db.listar_procurados()
    random.shuffle(pool_procurados)

    boletins = {}
    procurados_usados = []
    for regiao in regioes:
        texto, nome_usado = gerar_boletim_regiao(regiao, pool_procurados, teste=teste)
        boletins[regiao["nome"]] = texto
        if nome_usado:
            procurados_usados.append(nome_usado)
    return boletins, procurados_usados
