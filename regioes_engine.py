"""
regioes_engine.py
------------------
Motor de geração dos boletins a partir dos dados dinâmicos em regioes_db.
Substitui a lógica que antes estava hardcoded em jornal.py
(ILHAS_MARITIMAS, CLIMA_OPCOES, RUMOR_TEMPLATES, PARADISE_*).

Qualquer região cadastrada via /regioes (com locais, grupos de template e,
opcionalmente, clima) é suportada automaticamente — sem precisar tocar em
código para adicionar um "Novo Mundo", "Calm Belt" etc.

Cada boletim é gerado como um "estado" (dict serializável em JSON) com um
item por variável sorteada (rumor, mestre, procurado, categorias de clima...).
O texto final é montado a partir desse estado (renderizar_estado), o que
permite rerrolar UMA variável depois sem refazer o resto (rerrolar_variavel).
"""

import copy
import random
import re
import database as db  # planilha do Google com os procurados/marinheiros
import regioes_db as rdb

CHAVE_CLIMA = "clima"  # rerrola todas as categorias de clima de uma vez
CHAVE_PROCURADO = "procurado"


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


# ---------------------------------------------------------------------------
# Sorteio de cada tipo de variável
# ---------------------------------------------------------------------------

def _rolar_grupo(grupo: dict, regiao: dict, locais: list, ja_usados: set):
    variacoes = rdb.listar_variacoes(grupo["id"])
    if not variacoes:
        return None
    texto = rdb.sortear_com_peso(variacoes, chave_texto="texto")
    local = None
    if grupo["usa_local"] and "{local}" in texto:
        local = _sortear_local(locais, ja_usados, bool(regiao["locais_unicos_por_grupo"]))
        texto = texto.format(local=local or "???")
    return {"chave": f"grupo:{grupo['id']}", "rotulo": grupo["nome"], "texto": f"- {texto}", "local": local}


def _rolar_procurado(regiao: dict, locais: list, ja_usados: set, pool_procurados: list):
    """Consome (pop) o primeiro nome do pool, igual ao comportamento original."""
    nome_usado = None
    local = None
    if pool_procurados:
        nome_p, tipo_p = pool_procurados.pop(0)
        nome_usado = nome_p
        local = _sortear_local(locais, ja_usados, False) or "???"
        if tipo_p == "Marinheiro":
            texto = regiao["procurado_marinheiro_texto"].format(local=local, nome=nome_p)
        else:
            texto = regiao["procurado_pirata_texto"].format(local=local, nome=nome_p, nome_upper=nome_p.upper())
    else:
        texto = regiao["procurado_vazio_texto"]
    return {"chave": CHAVE_PROCURADO, "rotulo": "Procurado", "texto": f"- {texto}", "local": local, "nome": nome_usado}


def _rolar_categoria_clima(categoria: dict):
    opcoes = rdb.listar_opcoes_clima(categoria["id"])
    if not opcoes:
        return None
    opcao_sorteada = rdb.sortear_com_peso(opcoes, chave_texto="opcao")
    frase = categoria["frase"].format(categoria=categoria["nome"], opcao=opcao_sorteada.upper())
    return {"chave": f"clima:{categoria['id']}", "rotulo": categoria["nome"], "texto": frase}


# ---------------------------------------------------------------------------
# Geração / renderização do boletim de uma região
# ---------------------------------------------------------------------------

def gerar_estado_regiao(regiao: dict, pool_procurados: list, teste: bool = False) -> dict:
    """Sorteia todas as variáveis de UMA região a partir da configuração
    salva no banco. `pool_procurados` é consumido (pop) para não repetir
    entre regiões, igual ao comportamento original."""

    regiao_id = regiao["id"]
    nome_regiao = regiao["nome"]
    locais = rdb.listar_locais(regiao_id)
    ja_usados = set()

    titulo_teste = "[TESTE] " if teste else ""
    estado = {
        "regiao_id": regiao_id,
        "cabecalho": regiao["cabecalho_template"].format(teste=titulo_teste, regiao=nome_regiao.upper()),
        "introducao": regiao["introducao_template"].format(regiao=nome_regiao),
        "itens": [],
        "clima_titulo": None,
        "clima": [],
        "mencoes": regiao["mencoes_texto"] or "",
    }

    # --- grupos de template (rumores, mestre, nakama, tesouro, etc) ---
    for grupo in rdb.listar_grupos_template(regiao_id):
        item = _rolar_grupo(grupo, regiao, locais, ja_usados)
        if item:
            estado["itens"].append(item)

    # --- procurado / marinheiro (pool compartilhado entre regiões) ---
    if regiao["tem_procurado"]:
        estado["itens"].append(_rolar_procurado(regiao, locais, ja_usados, pool_procurados))

    # --- clima (opcional) ---
    if regiao["tem_clima"]:
        for categoria in rdb.listar_categorias_clima(regiao_id):
            item = _rolar_categoria_clima(categoria)
            if item:
                estado["clima"].append(item)
        if estado["clima"]:
            estado["clima_titulo"] = regiao["clima_titulo_template"].format(regiao=nome_regiao)

    return estado


def renderizar_estado(estado: dict) -> str:
    """Monta o texto final da mensagem a partir do estado."""
    partes = [estado["cabecalho"], "", estado["introducao"], "\n".join(i["texto"] for i in estado["itens"])]

    if estado["clima"]:
        partes += ["", estado["clima_titulo"], "\n".join(c["texto"] for c in estado["clima"])]

    if estado["mencoes"]:
        partes += ["", estado["mencoes"]]

    return "\n".join(partes) + "\n"


def nome_procurado(estado: dict):
    """Nome do procurado/marinheiro sorteado nesse estado, ou None."""
    for item in estado["itens"]:
        if item["chave"] == CHAVE_PROCURADO:
            return item.get("nome")
    return None


def gerar_boletim_regiao(regiao: dict, pool_procurados: list, teste: bool = False) -> tuple:
    """Retorna (texto, nome_procurado_usado_ou_None)."""
    estado = gerar_estado_regiao(regiao, pool_procurados, teste=teste)
    return renderizar_estado(estado), nome_procurado(estado)


def gerar_todos_boletins(teste: bool = False) -> tuple:
    """Gera o texto de todas as regiões ativas, na ordem configurada.
    Retorna ({nome_regiao: texto}, [procurados_usados_nesta_edição], {nome_regiao: estado})."""
    regioes = rdb.listar_regioes(apenas_ativas=True)

    pool_procurados = db.listar_procurados()
    random.shuffle(pool_procurados)

    boletins = {}
    estados = {}
    procurados_usados = []
    for regiao in regioes:
        estado = gerar_estado_regiao(regiao, pool_procurados, teste=teste)
        boletins[regiao["nome"]] = renderizar_estado(estado)
        estados[regiao["nome"]] = estado
        nome_usado = nome_procurado(estado)
        if nome_usado:
            procurados_usados.append(nome_usado)
    return boletins, procurados_usados, estados


# ---------------------------------------------------------------------------
# Rerrolar uma variável específica de um boletim já gerado
# ---------------------------------------------------------------------------

def listar_variaveis_regiao(regiao_id: int) -> list:
    """[(rótulo, chave)] das variáveis que a região sorteia (pela configuração atual)."""
    regiao = rdb.obter_regiao(regiao_id)
    variaveis = [(g["nome"], f"grupo:{g['id']}") for g in rdb.listar_grupos_template(regiao_id)
                 if rdb.listar_variacoes(g["id"])]
    if regiao["tem_procurado"]:
        variaveis.append(("Procurado", CHAVE_PROCURADO))
    if regiao["tem_clima"]:
        categorias = [c for c in rdb.listar_categorias_clima(regiao_id) if rdb.listar_opcoes_clima(c["id"])]
        if categorias:
            variaveis.append(("Clima (completo)", CHAVE_CLIMA))
            variaveis += [(f"Clima: {c['nome']}", f"clima:{c['id']}") for c in categorias]
    return variaveis


# ---------------------------------------------------------------------------
# Reconstruir o estado a partir do texto de uma mensagem JÁ postada
# (edições que não foram salvas, ex: a que já estava no ar antes do /rerrolar_variavel)
# ---------------------------------------------------------------------------

def _regex_de_template(template: str, campos: list, fixos: dict = None):
    """Regex (já escapada) que reconhece o texto gerado por template.format(...),
    com um grupo nomeado por campo em `campos` (repetições viram backreference).
    `fixos` são campos preenchidos com valor literal. None se o template for inválido."""
    fichas = {c: f"XQ{c}QX" for c in campos}
    try:
        texto = template.format(**fichas, **(fixos or {}))
    except (KeyError, IndexError, ValueError):
        return None
    vistos = set()

    def trocar(m):
        nome = m.group(1)
        if nome in vistos:
            return f"(?P={nome})"
        vistos.add(nome)
        return f"(?P<{nome}>.+?)"

    return re.sub(r"XQ(\w+?)QX", trocar, re.escape(texto))


def _reconhecer_item(regiao: dict, linha: str, grupos: list, usados: set, nomes_conhecidos: list):
    """Descobre qual variável (grupo de template ou procurado) gerou essa linha."""
    prefixo = re.escape("- ")

    for grupo, variacoes in grupos:
        chave = f"grupo:{grupo['id']}"
        if chave in usados:
            continue
        for v in variacoes:
            t = v["texto"]
            rx = _regex_de_template(t, ["local"]) if grupo["usa_local"] and "{local}" in t else re.escape(t)
            m = rx and re.fullmatch(prefixo + rx, linha)
            if m:
                usados.add(chave)
                return {"chave": chave, "rotulo": grupo["nome"], "texto": linha, "local": m.groupdict().get("local")}

    if regiao["tem_procurado"] and CHAVE_PROCURADO not in usados:
        opcoes = [
            (_regex_de_template(regiao["procurado_pirata_texto"], ["local", "nome", "nome_upper"]), True),
            (_regex_de_template(regiao["procurado_marinheiro_texto"], ["local", "nome", "nome_upper"]), False),
            (re.escape(regiao["procurado_vazio_texto"]), False),
        ]
        for rx, maiusculo in opcoes:
            m = rx and re.fullmatch(prefixo + rx, linha)
            if not m:
                continue
            g = m.groupdict()
            nome = g.get("nome")
            if nome is None and g.get("nome_upper"):
                nome = next((n for n in nomes_conhecidos if n.upper() == g["nome_upper"]), None)
            usados.add(CHAVE_PROCURADO)
            return {"chave": CHAVE_PROCURADO, "rotulo": "Procurado", "texto": linha,
                    "local": g.get("local"), "nome": nome}
    return None


def reconstruir_estado(regiao: dict, texto: str, nomes_conhecidos: list = ()) -> dict:
    """Reconstrói o estado de uma região a partir do texto de uma mensagem já
    postada, comparando cada linha com os templates ATUAIS da região.
    `nomes_conhecidos` (planilha + edição atual) servem pra recuperar o nome do
    procurado com a capitalização certa. Linhas que não forem reconhecidas são
    mantidas como estão (só não podem ser rerroladas).
    Levanta ValueError se a mensagem não parecer ser dessa região."""
    intro = regiao["introducao_template"].format(regiao=regiao["nome"])
    pos = texto.find(intro)
    if pos == -1:
        raise ValueError(f"Essa mensagem não parece ser do jornal de **{regiao['nome']}**.")

    estado = {
        "regiao_id": regiao["id"],
        "cabecalho": texto[:pos].rstrip("\n"),
        "introducao": intro,
        "itens": [],
        "clima_titulo": None,
        "clima": [],
        "mencoes": "",
    }
    resto = texto[pos + len(intro):].rstrip("\n")

    mencoes = regiao["mencoes_texto"]
    if mencoes and resto.endswith(mencoes):
        estado["mencoes"] = mencoes
        resto = resto[:-len(mencoes)]

    grupos = [(g, rdb.listar_variacoes(g["id"])) for g in rdb.listar_grupos_template(regiao["id"])]
    categorias = rdb.listar_categorias_clima(regiao["id"])
    titulo_clima = regiao["clima_titulo_template"].format(regiao=regiao["nome"])
    usados = set()
    no_clima = False

    for n, linha in enumerate(l for l in resto.split("\n") if l.strip()):
        if not no_clima and linha == titulo_clima:
            no_clima = True
            estado["clima_titulo"] = linha
            continue

        if no_clima:
            item = None
            for categoria in categorias:
                chave = f"clima:{categoria['id']}"
                rx = _regex_de_template(categoria["frase"], ["opcao"], {"categoria": categoria["nome"]})
                if chave not in usados and rx and re.fullmatch(rx, linha):
                    usados.add(chave)
                    item = {"chave": chave, "rotulo": categoria["nome"], "texto": linha}
                    break
            estado["clima"].append(item or {"chave": f"linha:{n}", "rotulo": "(linha não reconhecida)", "texto": linha})
        else:
            item = _reconhecer_item(regiao, linha, grupos, usados, list(nomes_conhecidos))
            estado["itens"].append(item or {"chave": f"linha:{n}", "rotulo": "(linha não reconhecida)",
                                            "texto": linha, "local": None})

    if estado["clima"] and not estado["clima_titulo"]:
        estado["clima_titulo"] = titulo_clima
    return estado


def rerrolar_variavel(estado: dict, chave: str, pool_procurados: list = None) -> tuple:
    """Rerrola só a variável `chave` e devolve (novo_estado, [novas_linhas]).
    Usa a configuração ATUAL da região (locais, variações, pesos).
    Levanta ValueError com mensagem pronta pra mostrar ao usuário."""
    regiao = rdb.obter_regiao(estado["regiao_id"])
    if not regiao:
        raise ValueError("Essa região não existe mais.")

    novo = copy.deepcopy(estado)

    # --- clima ---
    if chave == CHAVE_CLIMA or chave.startswith("clima:"):
        categorias = rdb.listar_categorias_clima(regiao["id"])
        if chave == CHAVE_CLIMA:
            novas = [i for i in map(_rolar_categoria_clima, categorias) if i]
            if not novas:
                raise ValueError("Essa região não tem clima configurado.")
            novo["clima"] = novas
            if not novo["clima_titulo"]:
                novo["clima_titulo"] = regiao["clima_titulo_template"].format(regiao=regiao["nome"])
            return novo, [i["texto"] for i in novas]

        idx = next((n for n, i in enumerate(novo["clima"]) if i["chave"] == chave), None)
        categoria = next((c for c in categorias if f"clima:{c['id']}" == chave), None)
        if idx is None or categoria is None:
            raise ValueError("Essa variável de clima não existe mais.")
        item = _rolar_categoria_clima(categoria)
        if not item:
            raise ValueError("Essa categoria de clima não tem opções cadastradas.")
        novo["clima"][idx] = item
        return novo, [item["texto"]]

    # --- itens (grupos de template / procurado) ---
    idx = next((n for n, i in enumerate(novo["itens"]) if i["chave"] == chave), None)
    if idx is None:
        raise ValueError("Essa variável não existe nessa edição.")

    locais = rdb.listar_locais(regiao["id"])
    # locais já ocupados pelas OUTRAS variáveis (só importa em regiões com locais únicos)
    ja_usados = {i["local"] for n, i in enumerate(novo["itens"]) if n != idx and i.get("local")}

    if chave == CHAVE_PROCURADO:
        if not pool_procurados:
            raise ValueError("Não há outro procurado disponível pra sortear.")
        pool = list(pool_procurados)
        random.shuffle(pool)
        item = _rolar_procurado(regiao, locais, ja_usados, pool)
    else:
        grupo = next((g for g in rdb.listar_grupos_template(regiao["id"]) if f"grupo:{g['id']}" == chave), None)
        if grupo is None:
            raise ValueError("Esse grupo de template não existe mais.")
        item = _rolar_grupo(grupo, regiao, locais, ja_usados)
        if not item:
            raise ValueError("Esse grupo não tem variações cadastradas.")

    novo["itens"][idx] = item
    return novo, [item["texto"]]
