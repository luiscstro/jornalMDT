"""
cacadas_db.py
--------------
Persistência do sistema de caça a procurados (/procurado):

- "cacadas": cada vez que um procurado é sorteado numa caça, fica travado
  por 2 semanas (ninguém pode caçá-lo de novo até o prazo passar).
- "jornal_atual": nomes que apareceram na última edição OFICIAL do jornal
  (semanal ou /rerrolar_jornal) — enquanto essa edição estiver valendo,
  esses nomes não podem ser sorteados pelo /procurado. É substituída
  inteira sempre que uma nova edição oficial é postada.
"""

import sqlite3
import json
import os
import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cacadas.db")

DIAS_TRAVA = 14

SCHEMA = """
CREATE TABLE IF NOT EXISTS cacadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    procurado_nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    mar TEXT NOT NULL,
    local TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    user_nome TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    expira_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jornal_atual (
    procurado_nome TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS edicao_atual (
    regiao_nome TEXT PRIMARY KEY,
    ordem INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    estado TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def _agora() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Caçadas (travas de 2 semanas)
# ---------------------------------------------------------------------------

def limpar_expiradas():
    with get_conn() as conn:
        conn.execute("DELETE FROM cacadas WHERE expira_em <= ?", (_iso(_agora()),))


def procurado_esta_travado(nome: str) -> bool:
    limpar_expiradas()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM cacadas WHERE LOWER(procurado_nome) = LOWER(?) LIMIT 1",
            (nome,),
        ).fetchone()
        return row is not None


def registrar_cacada(procurado_nome: str, tipo: str, mar: str, local: str,
                      user_id: int, user_nome: str) -> dict:
    criado_em = _agora()
    expira_em = criado_em + datetime.timedelta(days=DIAS_TRAVA)
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO cacadas (procurado_nome, tipo, mar, local, user_id, user_nome, criado_em, expira_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (procurado_nome, tipo, mar, local, user_id, user_nome, _iso(criado_em), _iso(expira_em)),
        )
        cacada_id = cur.lastrowid
    return {
        "id": cacada_id,
        "procurado_nome": procurado_nome,
        "tipo": tipo,
        "mar": mar,
        "local": local,
        "user_id": user_id,
        "user_nome": user_nome,
        "criado_em": criado_em,
        "expira_em": expira_em,
    }


def listar_cacadas_ativas() -> list:
    limpar_expiradas()
    with get_conn() as conn:
        linhas = conn.execute(
            "SELECT * FROM cacadas ORDER BY expira_em ASC"
        ).fetchall()
    resultado = []
    for r in linhas:
        d = dict(r)
        d["criado_em"] = datetime.datetime.fromisoformat(d["criado_em"])
        d["expira_em"] = datetime.datetime.fromisoformat(d["expira_em"])
        resultado.append(d)
    return resultado


def buscar_cacadas_ativas_por_nome(filtro_nome: str) -> list:
    ativas = listar_cacadas_ativas()
    filtro_nome = (filtro_nome or "").lower()
    return [c for c in ativas if filtro_nome in c["procurado_nome"].lower()]


def liberar_cacada(cacada_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM cacadas WHERE id = ?", (cacada_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Nomes bloqueados por estarem na edição atual do jornal
# ---------------------------------------------------------------------------

def definir_jornal_atual(nomes: list):
    with get_conn() as conn:
        conn.execute("DELETE FROM jornal_atual")
        conn.executemany(
            "INSERT OR IGNORE INTO jornal_atual (procurado_nome) VALUES (?)",
            [(n,) for n in nomes],
        )


def obter_jornal_atual() -> list:
    with get_conn() as conn:
        linhas = conn.execute("SELECT procurado_nome FROM jornal_atual").fetchall()
        return [r["procurado_nome"] for r in linhas]


def trocar_no_jornal_atual(nome_antigo, nome_novo):
    """Troca um nome da edição atual por outro (usado ao rerrolar o procurado)."""
    with get_conn() as conn:
        if nome_antigo:
            conn.execute("DELETE FROM jornal_atual WHERE procurado_nome = ?", (nome_antigo,))
        if nome_novo:
            conn.execute("INSERT OR IGNORE INTO jornal_atual (procurado_nome) VALUES (?)", (nome_novo,))


# ---------------------------------------------------------------------------
# Estado da edição oficial atual (pra rerrolar variáveis e editar a mensagem)
# ---------------------------------------------------------------------------

def salvar_edicao_atual(registros: list):
    """`registros`: [(regiao_nome, channel_id, message_id, estado_dict)] na ordem
    de postagem. Substitui a edição anterior inteira."""
    with get_conn() as conn:
        conn.execute("DELETE FROM edicao_atual")
        conn.executemany(
            "INSERT INTO edicao_atual (regiao_nome, ordem, channel_id, message_id, estado) VALUES (?, ?, ?, ?, ?)",
            [(nome, ordem, canal_id, msg_id, json.dumps(estado))
             for ordem, (nome, canal_id, msg_id, estado) in enumerate(registros)],
        )


def _linha_para_dict(r) -> dict:
    d = dict(r)
    d["estado"] = json.loads(d["estado"])
    return d


def listar_edicao_atual() -> list:
    with get_conn() as conn:
        linhas = conn.execute("SELECT * FROM edicao_atual ORDER BY ordem").fetchall()
    return [_linha_para_dict(r) for r in linhas]


def obter_edicao_regiao(regiao_nome: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM edicao_atual WHERE regiao_nome = ?", (regiao_nome,)).fetchone()
    return _linha_para_dict(row) if row else None


def salvar_edicao_regiao(regiao_nome: str, channel_id: int, message_id: int, estado: dict):
    """Insere/atualiza o registro de UMA região (mantém a posição se já existia)."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO edicao_atual (regiao_nome, ordem, channel_id, message_id, estado)
               VALUES (?, (SELECT COALESCE(MAX(ordem), -1) + 1 FROM edicao_atual), ?, ?, ?)
               ON CONFLICT(regiao_nome) DO UPDATE SET
                   channel_id = excluded.channel_id,
                   message_id = excluded.message_id,
                   estado = excluded.estado""",
            (regiao_nome, channel_id, message_id, json.dumps(estado)),
        )


def nome_no_jornal_atual(nome: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM jornal_atual WHERE LOWER(procurado_nome) = LOWER(?) LIMIT 1",
            (nome,),
        ).fetchone()
        return row is not None
