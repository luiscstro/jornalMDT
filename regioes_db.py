"""
regioes_db.py
--------------
Camada de dados para as "Regiões" do jornal (East Blue, South Blue, Paradise,
Novo Mundo, etc). Tudo o que antes era hardcoded em jornal.py (ilhas, climas
com peso, templates de rumor) agora vive aqui, num SQLite local
(regioes.db), e é 100% editável via a UI do bot (regioes_admin.py).

Nenhuma região nova exige alterar código: basta usar /regioes no Discord.
"""

import sqlite3
import os
import random
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regioes.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS regioes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    rotulo_local TEXT NOT NULL DEFAULT 'ilha',
    tem_clima INTEGER NOT NULL DEFAULT 1,
    tem_procurado INTEGER NOT NULL DEFAULT 1,
    locais_unicos_por_grupo INTEGER NOT NULL DEFAULT 0,
    mencoes_texto TEXT NOT NULL DEFAULT '',
    ordem INTEGER NOT NULL DEFAULT 0,
    ativa INTEGER NOT NULL DEFAULT 1,
    cabecalho_template TEXT NOT NULL DEFAULT '# {teste}RAINBOW NEWS - EXPRESS ({regiao})
-# Por Typist Mustang',
    introducao_template TEXT NOT NULL DEFAULT '## Fatos semanais sobre {regiao}!',
    clima_titulo_template TEXT NOT NULL DEFAULT '## Boletim do tempo - {regiao}',
    procurado_pirata_texto TEXT NOT NULL DEFAULT '**PROCURADO!** Está sendo contado pelos ventos que terror está sendo propagado em **{local}**, sob as ordens de **{nome_upper}**',
    procurado_marinheiro_texto TEXT NOT NULL DEFAULT 'Parece que tem atividade da Marinha em **{local}** sob o comando de **{nome}**!',
    procurado_vazio_texto TEXT NOT NULL DEFAULT 'Semana tranquila... Nenhum pirata notável foi reportado pelas autoridades.'
);

CREATE TABLE IF NOT EXISTS locais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regiao_id INTEGER NOT NULL REFERENCES regioes(id) ON DELETE CASCADE,
    nome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS grupos_template (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regiao_id INTEGER NOT NULL REFERENCES regioes(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    ordem INTEGER NOT NULL DEFAULT 0,
    usa_local INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS variacoes_template (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grupo_id INTEGER NOT NULL REFERENCES grupos_template(id) ON DELETE CASCADE,
    texto TEXT NOT NULL,
    peso INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS clima_categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regiao_id INTEGER NOT NULL REFERENCES regioes(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    ordem INTEGER NOT NULL DEFAULT 0,
    frase TEXT NOT NULL DEFAULT '- {categoria} hoje: **{opcao}**.'
);

CREATE TABLE IF NOT EXISTS clima_opcoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id INTEGER NOT NULL REFERENCES clima_categorias(id) ON DELETE CASCADE,
    opcao TEXT NOT NULL,
    peso INTEGER NOT NULL DEFAULT 1
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(seed_defaults: bool = True):
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    if seed_defaults:
        _seed_defaults_if_empty()


# ---------------------------------------------------------------------------
# SEED: recria a configuração atual (East/South/North/West Blue + Paradise)
# como registros editáveis, para que nada quebre na migração.
# ---------------------------------------------------------------------------

def _seed_defaults_if_empty():
    with get_conn() as conn:
        existentes = conn.execute("SELECT COUNT(*) c FROM regioes").fetchone()["c"]
        if existentes > 0:
            return

    ilhas_por_mar = {
        "East Blue": [
            "Oykot Kingdom", "Polestar Island", "Cozia Island", "Mirrorball",
            "Conomi Island", "Grand Serenity", "Baratie", "Gecko Island",
            "Island of Rare Animals", "Organ Islands", "Crescent Isle",
            "Tequila Wolf", "Goat Island", "Shimotsuki", "Sixis Island", "Down Island"
        ],
        "South Blue": [
            "Baterilla", "Behemoth Island", "Black Drum Kingdom", "Briar Island",
            "Briss Kingdom", "Centaurea", "Clockwork Island", "Deadman's Key",
            "Fort Justice", "Karate Island", "Kyuka Island", "Mokora",
            "Reino Torino", "Ryujin Island", "Sorbet Kingdom", "South Pole"
        ],
        "North Blue": [
            "Blackpine Kingdom", "Deul Kingdom", "Downs Island", "Flevance Kingdom",
            "Frostharbor Island", "Germa Kingdom", "Kuen Island", "Lvneel Kingdom",
            "Minion Island", "North Pole", "Notice Island", "Rakesh", 
            "Rubeck Island", "Spider Miles", "Swallow Island", "Whiteland Kingdom"
        ],
        "West Blue": [
            "80th Branch", "Arlen Island", "Ballywood Kingdom", "Blackreef Island",
            "Ferrônia", "Fogreach", "Ilisia Kingdom", "Isla Fortuna",
            "Kano Kuni", "Las Camp", "Ohara",
            "Saint Aurelia", "Soja Island", "Stormhaven",
            "Toroa Island", "Vespera Island"    
        ],
    }

    ranks_opcoes = ["Amador:Infame", "Amador: Desconhecido", "Amador: Famoso"]

    ids_role = ["1221255954708959324", "1283492761039011851", "1220345032079572995"]
    mencoes_blues = f"||{' '.join(f'<@&{i}>' for i in ids_role)}||"

    for ordem, (mar, ilhas) in enumerate(ilhas_por_mar.items()):
        regiao_id = criar_regiao(
            nome=mar,
            rotulo_local="ilha",
            tem_clima=True,
            tem_procurado=True,
            locais_unicos_por_grupo=False,
            mencoes_texto="",
            ordem=ordem,
        )
        adicionar_locais(regiao_id, ilhas)

        g_rumor = criar_grupo_template(regiao_id, "Rumor de Tesouro", ordem=0, usa_local=True)
        for t in [
            "Boatos sobre ruínas inexploradas em **{local}**.",
            "Dizem que um tesouro antigo está enterrado em **{local}**.",
            "Um mapa misterioso aponta para um tesouro escondido em **{local}**.",
        ]:
            adicionar_variacao(g_rumor, t, peso=1)

        g_mestre = criar_grupo_template(regiao_id, "Mestre", ordem=1, usa_local=True)
        adicionar_variacao(
            g_mestre,
            "Procurando um mestre? Em **{local}**, temos um **professor** querendo ensinar piratas dispostos a aprender.",
            peso=1,
        )

        g_nakama = criar_grupo_template(regiao_id, "Nakama", ordem=2, usa_local=True)
        for rank in ranks_opcoes:
            adicionar_variacao(
                g_nakama,
                "Não quer um mestre? Que tal um nakama provisório pro seu barco? Temos um **" + rank + "** em **{local}**!",
                peso=1,
            )

        cat_temp = criar_categoria_clima(regiao_id, "temperatura", ordem=0,
                                          frase="- Oh yes! A temperatura hoje está... **{opcao}**.")
        for op in ["Amena", "Frio", "Calor"]:
            adicionar_opcao_clima(cat_temp, op, peso=1)

        cat_vento = criar_categoria_clima(regiao_id, "vento", ordem=1,
                                           frase="- Icem as velas, ou não pois hoje temos Vento... **{opcao}**.")
        for op in ["Nenhum", "Fraco", "Forte"]:
            adicionar_opcao_clima(cat_vento, op, peso=1)

        cat_precip = criar_categoria_clima(regiao_id, "precipitacao", ordem=2,
                                            frase="- E por último mas não menos importante, para as donas de casa que deixaram roupas no varal a previsão é de... **{opcao}**.")
        for op in ["Nenhuma", "Chuva ou Nevasca Fraca", "Chuva ou Nevasca intensa"]:
            adicionar_opcao_clima(cat_precip, op, peso=1)

        editar_regiao(regiao_id, mencoes_texto=mencoes_blues if mar == "West Blue" else "")

    paradise_id = criar_regiao(
        nome="Paradise",
        rotulo_local="rota",
        tem_clima=False,
        tem_procurado=False,
        locais_unicos_por_grupo=True,
        mencoes_texto=mencoes_blues,
        ordem=len(ilhas_por_mar),
    )
    adicionar_locais(paradise_id, ["Vermelha", "Laranja", "Azul", "Verde", "Amarela", "Rosa", "Branca"])
    g_tesouro = criar_grupo_template(paradise_id, "Tesouro", ordem=0, usa_local=True)
    adicionar_variacao(
        g_tesouro,
        "Ouvimos muitos boatos de piratas sortudos encontrando tesouros recheados na **rota {local}**! (Caçador de Tesouros)",
        peso=1,
    )
    g_procurado_paradise = criar_grupo_template(paradise_id, "Procurado", ordem=1, usa_local=True)
    adicionar_variacao(
        g_procurado_paradise,
        "Há rumores de um possível encontro de figurões piratas na **rota {local}**! (procurado garantido)",
        peso=1,
    )


# ---------------------------------------------------------------------------
# CRUD: Regiões
# ---------------------------------------------------------------------------

def listar_regioes(apenas_ativas: bool = False):
    with get_conn() as conn:
        q = "SELECT * FROM regioes"
        if apenas_ativas:
            q += " WHERE ativa = 1"
        q += " ORDER BY ordem, id"
        return [dict(r) for r in conn.execute(q).fetchall()]


def obter_regiao(regiao_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM regioes WHERE id = ?", (regiao_id,)).fetchone()
        return dict(row) if row else None


def obter_regiao_por_nome(nome: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM regioes WHERE nome = ?", (nome,)).fetchone()
        return dict(row) if row else None


def criar_regiao(nome, rotulo_local="ilha", tem_clima=True, tem_procurado=True,
                  locais_unicos_por_grupo=False, mencoes_texto="", ordem=0, **campos_extra):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO regioes (nome, rotulo_local, tem_clima, tem_procurado,
               locais_unicos_por_grupo, mencoes_texto, ordem)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (nome, rotulo_local, int(tem_clima), int(tem_procurado),
             int(locais_unicos_por_grupo), mencoes_texto, ordem),
        )
        regiao_id = cur.lastrowid
    if campos_extra:
        editar_regiao(regiao_id, **campos_extra)
    return regiao_id


CAMPOS_EDITAVEIS_REGIAO = {
    "nome", "rotulo_local", "tem_clima", "tem_procurado", "locais_unicos_por_grupo",
    "mencoes_texto", "ordem", "ativa", "cabecalho_template", "introducao_template",
    "clima_titulo_template", "procurado_pirata_texto", "procurado_marinheiro_texto",
    "procurado_vazio_texto",
}


def editar_regiao(regiao_id: int, **campos):
    campos = {k: v for k, v in campos.items() if k in CAMPOS_EDITAVEIS_REGIAO and v is not None}
    if not campos:
        return
    sets = ", ".join(f"{k} = ?" for k in campos)
    valores = list(campos.values()) + [regiao_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE regioes SET {sets} WHERE id = ?", valores)


def excluir_regiao(regiao_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM regioes WHERE id = ?", (regiao_id,))


def nome_regiao_existe(nome: str, ignorar_id: int = None) -> bool:
    with get_conn() as conn:
        if ignorar_id:
            row = conn.execute("SELECT id FROM regioes WHERE nome = ? AND id != ?", (nome, ignorar_id)).fetchone()
        else:
            row = conn.execute("SELECT id FROM regioes WHERE nome = ?", (nome,)).fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# CRUD: Locais (ilhas / rotas / o que for)
# ---------------------------------------------------------------------------

def listar_locais(regiao_id: int):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM locais WHERE regiao_id = ? ORDER BY nome", (regiao_id,)
        ).fetchall()]


def adicionar_local(regiao_id: int, nome: str):
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO locais (regiao_id, nome) VALUES (?, ?)", (regiao_id, nome))
        return cur.lastrowid


def adicionar_locais(regiao_id: int, nomes: list):
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO locais (regiao_id, nome) VALUES (?, ?)",
            [(regiao_id, n) for n in nomes],
        )


def remover_local(local_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM locais WHERE id = ?", (local_id,))


# ---------------------------------------------------------------------------
# CRUD: Grupos de template + variações (com peso)
# ---------------------------------------------------------------------------

def listar_grupos_template(regiao_id: int):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM grupos_template WHERE regiao_id = ? ORDER BY ordem, id", (regiao_id,)
        ).fetchall()]


def criar_grupo_template(regiao_id: int, nome: str, ordem: int = 0, usa_local: bool = True):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO grupos_template (regiao_id, nome, ordem, usa_local) VALUES (?, ?, ?, ?)",
            (regiao_id, nome, ordem, int(usa_local)),
        )
        return cur.lastrowid


def editar_grupo_template(grupo_id: int, **campos):
    campos_validos = {"nome", "ordem", "usa_local"}
    campos = {k: v for k, v in campos.items() if k in campos_validos and v is not None}
    if not campos:
        return
    sets = ", ".join(f"{k} = ?" for k in campos)
    valores = list(campos.values()) + [grupo_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE grupos_template SET {sets} WHERE id = ?", valores)


def excluir_grupo_template(grupo_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM grupos_template WHERE id = ?", (grupo_id,))


def listar_variacoes(grupo_id: int):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM variacoes_template WHERE grupo_id = ? ORDER BY id", (grupo_id,)
        ).fetchall()]


def adicionar_variacao(grupo_id: int, texto: str, peso: int = 1):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO variacoes_template (grupo_id, texto, peso) VALUES (?, ?, ?)",
            (grupo_id, texto, peso),
        )
        return cur.lastrowid


def editar_variacao(variacao_id: int, texto: str = None, peso: int = None):
    campos = {}
    if texto is not None:
        campos["texto"] = texto
    if peso is not None:
        campos["peso"] = peso
    if not campos:
        return
    sets = ", ".join(f"{k} = ?" for k in campos)
    valores = list(campos.values()) + [variacao_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE variacoes_template SET {sets} WHERE id = ?", valores)


def remover_variacao(variacao_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM variacoes_template WHERE id = ?", (variacao_id,))


# ---------------------------------------------------------------------------
# CRUD: Categorias de clima + opções (com peso / porcentagem)
# ---------------------------------------------------------------------------

def listar_categorias_clima(regiao_id: int):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM clima_categorias WHERE regiao_id = ? ORDER BY ordem, id", (regiao_id,)
        ).fetchall()]


def criar_categoria_clima(regiao_id: int, nome: str, ordem: int = 0, frase: str = None):
    with get_conn() as conn:
        if frase is None:
            cur = conn.execute(
                "INSERT INTO clima_categorias (regiao_id, nome, ordem) VALUES (?, ?, ?)",
                (regiao_id, nome, ordem),
            )
        else:
            cur = conn.execute(
                "INSERT INTO clima_categorias (regiao_id, nome, ordem, frase) VALUES (?, ?, ?, ?)",
                (regiao_id, nome, ordem, frase),
            )
        return cur.lastrowid


def editar_categoria_clima(categoria_id: int, **campos):
    campos_validos = {"nome", "ordem", "frase"}
    campos = {k: v for k, v in campos.items() if k in campos_validos and v is not None}
    if not campos:
        return
    sets = ", ".join(f"{k} = ?" for k in campos)
    valores = list(campos.values()) + [categoria_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE clima_categorias SET {sets} WHERE id = ?", valores)


def excluir_categoria_clima(categoria_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM clima_categorias WHERE id = ?", (categoria_id,))


def listar_opcoes_clima(categoria_id: int):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM clima_opcoes WHERE categoria_id = ? ORDER BY id", (categoria_id,)
        ).fetchall()]


def adicionar_opcao_clima(categoria_id: int, opcao: str, peso: int = 1):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clima_opcoes (categoria_id, opcao, peso) VALUES (?, ?, ?)",
            (categoria_id, opcao, peso),
        )
        return cur.lastrowid


def editar_opcao_clima(opcao_id: int, opcao: str = None, peso: int = None):
    campos = {}
    if opcao is not None:
        campos["opcao"] = opcao
    if peso is not None:
        campos["peso"] = peso
    if not campos:
        return
    sets = ", ".join(f"{k} = ?" for k in campos)
    valores = list(campos.values()) + [opcao_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE clima_opcoes SET {sets} WHERE id = ?", valores)


def remover_opcao_clima(opcao_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM clima_opcoes WHERE id = ?", (opcao_id,))


# ---------------------------------------------------------------------------
# Utilitário de porcentagem: dado uma lista de pesos, retorna % de cada um
# ---------------------------------------------------------------------------

def calcular_porcentagens(itens_com_peso: list, chave_peso: str = "peso"):
    """Recebe uma lista de dicts com um campo de peso e devolve a mesma lista
    com um campo extra 'porcentagem' (peso relativo, 0-100, arredondado a 1 casa)."""
    total = sum(item[chave_peso] for item in itens_com_peso) or 1
    for item in itens_com_peso:
        item["porcentagem"] = round(item[chave_peso] / total * 100, 1)
    return itens_com_peso


def sortear_com_peso(itens: list, chave_texto: str, chave_peso: str = "peso"):
    if not itens:
        return None
    textos = [i[chave_texto] for i in itens]
    pesos = [i[chave_peso] for i in itens]
    return random.choices(textos, weights=pesos, k=1)[0]
