"""
navegacao_db.py
----------------
Armazenamento da navegação do Novo Mundo. Dois backends com a MESMA interface,
escolhidos pela variável de ambiente DATABASE_URL:

- PostgreSQL da Discloud (com DATABASE_URL): tabelas nm_ilhas, nm_bandos e
  nm_log, criadas sozinhas. Só é acessível de dentro da rede privada (VLAN).
- Google Sheets (sem DATABASE_URL, ex: testes locais): abas NM_Ilhas, NM_Bandos
  e NM_Log na planilha "Procurados Blues", também criadas sozinhas.

Todas as funções são BLOQUEANTES. No cog, chame via asyncio.to_thread.
"""

import datetime
import json
import os
import time

import database as db
from navegacao_dados import ilhas_seed

TIPOS_ILHA = ("inicial", "sincronizavel", "secreta", "principal", "totto", "totto_ilha", "calm")

TTL_CACHE_SEGUNDOS = 60
_cache_ilhas = {"ts": 0.0, "dados": None}


class ErroBanco(Exception):
    """Falha ao falar com o banco (mensagem pronta pra mostrar)."""


def usa_postgres() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def nome_backend() -> str:
    return "PostgreSQL (Discloud)" if usa_postgres() else "Google Sheets"


def _invalidar_cache():
    _cache_ilhas.update(ts=0.0, dados=None)


def _agora_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _converter_area(valor):
    valor = str(valor or "").strip().lower()
    return int(valor) if valor.isdigit() else valor


def _montar_ilha(area, nome, tipo, nota) -> dict:
    return {"area": _converter_area(area), "nome": str(nome).strip(),
            "tipo": str(tipo).strip().lower(), "nota": str(nota or "").strip()}


# ===========================================================================
# PostgreSQL
# ===========================================================================

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS nm_ilhas (
    id SERIAL PRIMARY KEY,
    area TEXT NOT NULL,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    nota TEXT NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS nm_ilhas_nome_uq ON nm_ilhas (LOWER(nome));
CREATE TABLE IF NOT EXISTS nm_bandos (
    chave TEXT PRIMARY KEY,
    bando TEXT NOT NULL,
    estado JSONB NOT NULL,
    atualizado TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS nm_log (
    id SERIAL PRIMARY KEY,
    data TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bando TEXT NOT NULL,
    evento TEXT NOT NULL,
    detalhe TEXT NOT NULL DEFAULT ''
);
"""

_schema_ok = False


class _ConexaoPg:
    """Context manager: abre conexão, faz commit/rollback e fecha."""

    def __enter__(self):
        global _schema_ok
        try:
            import psycopg2
            self.conn = psycopg2.connect(os.getenv("DATABASE_URL"), connect_timeout=10)
        except Exception as e:
            raise ErroBanco(f"Não consegui conectar ao PostgreSQL da Discloud: {e}")
        try:
            if not _schema_ok:
                with self.conn.cursor() as cur:
                    cur.execute(_SCHEMA_PG)
                    cur.execute("SELECT COUNT(*) FROM nm_ilhas")
                    if cur.fetchone()[0] == 0:
                        cur.executemany(
                            "INSERT INTO nm_ilhas (area, nome, tipo, nota) VALUES (%s, %s, %s, %s) "
                            "ON CONFLICT DO NOTHING",
                            [(str(a), n, t, nt) for a, n, t, nt in ilhas_seed()],
                        )
                self.conn.commit()
                _schema_ok = True
        except Exception as e:
            self.conn.close()
            raise ErroBanco(f"Erro ao preparar as tabelas da navegação: {e}")
        return self.conn

    def __exit__(self, tipo, valor, tb):
        try:
            if tipo is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()
        if tipo is not None and not issubclass(tipo, ErroBanco):
            raise ErroBanco(f"Erro no PostgreSQL: {valor}") from valor
        return False


def _pg_listar_ilhas() -> list:
    with _ConexaoPg() as conn, conn.cursor() as cur:
        cur.execute("SELECT area, nome, tipo, nota FROM nm_ilhas ORDER BY id")
        return [_montar_ilha(*linha) for linha in cur.fetchall()]


def _pg_adicionar_ilha(area, nome, tipo, nota) -> bool:
    with _ConexaoPg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO nm_ilhas (area, nome, tipo, nota) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (str(area), nome.strip(), tipo, nota or ""),
        )
        return cur.rowcount > 0


def _pg_remover_ilha(nome) -> bool:
    with _ConexaoPg() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM nm_ilhas WHERE LOWER(nome) = LOWER(%s)", (nome.strip(),))
        return cur.rowcount > 0


def _pg_listar_nomes_bandos() -> list:
    with _ConexaoPg() as conn, conn.cursor() as cur:
        cur.execute("SELECT bando FROM nm_bandos ORDER BY bando")
        return [l[0] for l in cur.fetchall()]


def _pg_obter_bando(nome):
    with _ConexaoPg() as conn, conn.cursor() as cur:
        cur.execute("SELECT estado FROM nm_bandos WHERE chave = %s", (nome.strip().lower(),))
        linha = cur.fetchone()
        if not linha:
            return None
        return linha[0] if isinstance(linha[0], dict) else json.loads(linha[0])


def _pg_salvar_bando(estado):
    with _ConexaoPg() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO nm_bandos (chave, bando, estado, atualizado)
               VALUES (%s, %s, %s::jsonb, NOW())
               ON CONFLICT (chave) DO UPDATE SET estado = EXCLUDED.estado, atualizado = NOW()""",
            (estado["bando"].strip().lower(), estado["bando"], json.dumps(estado, ensure_ascii=False)),
        )


def _pg_registrar_log(bando, evento, detalhe):
    with _ConexaoPg() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO nm_log (bando, evento, detalhe) VALUES (%s, %s, %s)", (bando, evento, detalhe))


# ===========================================================================
# Google Sheets (fallback)
# ===========================================================================

ABA_ILHAS = "NM_Ilhas"
ABA_BANDOS = "NM_Bandos"
ABA_LOG = "NM_Log"
CAB_ILHAS = ["area", "nome", "tipo", "nota"]
CAB_BANDOS = ["bando", "estado", "atualizado"]
CAB_LOG = ["data", "bando", "evento", "detalhe"]


def _planilha():
    planilha = db.obter_planilha()
    if planilha is None:
        erro = db.obter_ultimo_erro_conexao() or "erro desconhecido"
        raise ErroBanco(f"Não consegui conectar à planilha do Google: {erro}")
    return planilha


def _aba(nome: str, cabecalho: list, linhas_iniciais: list = None):
    """Abre a aba; se não existir, cria com o cabeçalho (e linhas iniciais)."""
    import gspread
    planilha = _planilha()
    try:
        return planilha.worksheet(nome)
    except gspread.WorksheetNotFound:
        pass
    try:
        ws = planilha.add_worksheet(title=nome, rows=max(200, len(linhas_iniciais or []) + 20), cols=len(cabecalho))
        ws.append_row(cabecalho)
        if linhas_iniciais:
            ws.append_rows([[str(c) for c in linha] for linha in linhas_iniciais])
        return ws
    except Exception as e:
        raise ErroBanco(f"Não consegui criar a aba {nome}: {e}")


def _sh(func):
    """Converte qualquer erro do gspread em ErroBanco."""
    try:
        return func()
    except ErroBanco:
        raise
    except Exception as e:
        raise ErroBanco(f"Erro no Google Sheets: {e}")


def _sh_listar_ilhas() -> list:
    linhas = _sh(lambda: _aba(ABA_ILHAS, CAB_ILHAS, ilhas_seed()).get_all_values()[1:])
    ilhas = []
    for linha in linhas:
        linha = linha + [""] * (4 - len(linha))
        if linha[1].strip():
            ilhas.append(_montar_ilha(*linha[:4]))
    return ilhas


def _sh_adicionar_ilha(area, nome, tipo, nota) -> bool:
    if any(i["nome"].lower() == nome.strip().lower() for i in _sh_listar_ilhas()):
        return False
    _sh(lambda: _aba(ABA_ILHAS, CAB_ILHAS, ilhas_seed()).append_row([str(area), nome.strip(), tipo, nota or ""]))
    return True


def _sh_remover_ilha(nome) -> bool:
    ws = _sh(lambda: _aba(ABA_ILHAS, CAB_ILHAS, ilhas_seed()))
    for idx, linha in enumerate(_sh(ws.get_all_values)):
        if idx and len(linha) > 1 and linha[1].strip().lower() == nome.strip().lower():
            _sh(lambda: ws.delete_rows(idx + 1))
            return True
    return False


def _sh_listar_nomes_bandos() -> list:
    return [l[0] for l in _sh(lambda: _aba(ABA_BANDOS, CAB_BANDOS).get_all_values()[1:]) if l and l[0]]


def _sh_obter_bando(nome):
    for linha in _sh(lambda: _aba(ABA_BANDOS, CAB_BANDOS).get_all_values()[1:]):
        if len(linha) >= 2 and linha[0].strip().lower() == nome.strip().lower():
            return json.loads(linha[1])
    return None


def _sh_salvar_bando(estado):
    def _salvar():
        ws = _aba(ABA_BANDOS, CAB_BANDOS)
        texto = json.dumps(estado, ensure_ascii=False)
        for idx, linha in enumerate(ws.get_all_values()):
            if idx and linha and linha[0].strip().lower() == estado["bando"].strip().lower():
                ws.update_cell(idx + 1, 2, texto)
                ws.update_cell(idx + 1, 3, _agora_iso())
                return
        ws.append_row([estado["bando"], texto, _agora_iso()])
    _sh(_salvar)


def _sh_registrar_log(bando, evento, detalhe):
    _sh(lambda: _aba(ABA_LOG, CAB_LOG).append_row([_agora_iso(), bando, evento, detalhe]))


# ===========================================================================
# Interface pública (usada pelo cog)
# ===========================================================================

def listar_ilhas(forcar: bool = False) -> list:
    """[{area, nome, tipo, nota}] (cache de 60s)."""
    if not forcar and _cache_ilhas["dados"] is not None and time.time() - _cache_ilhas["ts"] < TTL_CACHE_SEGUNDOS:
        return _cache_ilhas["dados"]
    ilhas = _pg_listar_ilhas() if usa_postgres() else _sh_listar_ilhas()
    _cache_ilhas.update(ts=time.time(), dados=ilhas)
    return ilhas


def adicionar_ilha(area, nome: str, tipo: str, nota: str = "") -> bool:
    """False se já existe uma ilha com esse nome."""
    ok = _pg_adicionar_ilha(area, nome, tipo, nota) if usa_postgres() else _sh_adicionar_ilha(area, nome, tipo, nota)
    _invalidar_cache()
    return ok


def remover_ilha(nome: str) -> bool:
    ok = _pg_remover_ilha(nome) if usa_postgres() else _sh_remover_ilha(nome)
    _invalidar_cache()
    return ok


def listar_nomes_bandos() -> list:
    return _pg_listar_nomes_bandos() if usa_postgres() else _sh_listar_nomes_bandos()


def obter_bando(nome: str):
    """Estado (dict) do bando, ou None se não existir."""
    return _pg_obter_bando(nome) if usa_postgres() else _sh_obter_bando(nome)


def salvar_bando(estado: dict):
    (_pg_salvar_bando if usa_postgres() else _sh_salvar_bando)(estado)


def registrar_log(bando: str, evento: str, detalhe: str = ""):
    """Histórico (só anexa). Falha no log nunca derruba o comando."""
    try:
        (_pg_registrar_log if usa_postgres() else _sh_registrar_log)(bando, evento, detalhe)
    except Exception as e:
        print(f"⚠️ Não consegui gravar o log da navegação: {e}")
