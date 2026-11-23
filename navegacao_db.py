"""
navegacao_db.py
----------------
Armazenamento da navegação do Novo Mundo no Google Sheets (grátis e persistente:
sobrevive a reinícios e redeploys do bot, ao contrário de arquivos locais).
Usa a mesma planilha "Procurados Blues" e as mesmas credenciais do bot, com
abas próprias (criadas automaticamente na primeira vez):

- NM_Ilhas  : area | nome | tipo | nota   (semeada com navegacao_dados.py; pode editar à mão)
- NM_Bandos : bando | estado (JSON) | atualizado
- NM_Log    : data | bando | evento | detalhe

Todas as funções são BLOQUEANTES (gspread). No cog, chame via asyncio.to_thread.
"""

import datetime
import json
import time

import gspread

import database as db
from navegacao_dados import ilhas_seed

ABA_ILHAS = "NM_Ilhas"
ABA_BANDOS = "NM_Bandos"
ABA_LOG = "NM_Log"

CAB_ILHAS = ["area", "nome", "tipo", "nota"]
CAB_BANDOS = ["bando", "estado", "atualizado"]
CAB_LOG = ["data", "bando", "evento", "detalhe"]

TTL_CACHE_SEGUNDOS = 60

_cache_ilhas = {"ts": 0.0, "dados": None}


class ErroBanco(Exception):
    """Falha ao falar com a planilha (mensagem pronta pra mostrar)."""


def _agora_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _planilha():
    planilha = db.obter_planilha()
    if planilha is None:
        erro = db.obter_ultimo_erro_conexao() or "erro desconhecido"
        raise ErroBanco(f"Não consegui conectar à planilha do Google: {erro}")
    return planilha


def _aba(nome: str, cabecalho: list, linhas_iniciais: list = None):
    """Abre a aba; se não existir, cria com o cabeçalho (e linhas iniciais)."""
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


# ---------------------------------------------------------------------------
# Ilhas
# ---------------------------------------------------------------------------

def _converter_area(valor: str):
    valor = (valor or "").strip().lower()
    return int(valor) if valor.isdigit() else valor


def listar_ilhas(forcar: bool = False) -> list:
    """[{area, nome, tipo, nota}] da aba NM_Ilhas (cache de 60s)."""
    if not forcar and _cache_ilhas["dados"] is not None and time.time() - _cache_ilhas["ts"] < TTL_CACHE_SEGUNDOS:
        return _cache_ilhas["dados"]
    try:
        ws = _aba(ABA_ILHAS, CAB_ILHAS, ilhas_seed())
        linhas = ws.get_all_values()[1:]
    except ErroBanco:
        raise
    except Exception as e:
        raise ErroBanco(f"Erro ao ler a aba {ABA_ILHAS}: {e}")
    ilhas = []
    for linha in linhas:
        linha = linha + [""] * (4 - len(linha))
        if not linha[1].strip():
            continue
        ilhas.append({
            "area": _converter_area(linha[0]),
            "nome": linha[1].strip(),
            "tipo": linha[2].strip().lower(),
            "nota": linha[3].strip(),
        })
    _cache_ilhas.update(ts=time.time(), dados=ilhas)
    return ilhas


# ---------------------------------------------------------------------------
# Bandos
# ---------------------------------------------------------------------------

def _ws_bandos():
    return _aba(ABA_BANDOS, CAB_BANDOS)


def listar_nomes_bandos() -> list:
    try:
        return [l[0] for l in _ws_bandos().get_all_values()[1:] if l and l[0]]
    except ErroBanco:
        raise
    except Exception as e:
        raise ErroBanco(f"Erro ao ler a aba {ABA_BANDOS}: {e}")


def obter_bando(nome: str):
    """Estado (dict) do bando, ou None se não existir."""
    try:
        for linha in _ws_bandos().get_all_values()[1:]:
            if len(linha) >= 2 and linha[0].strip().lower() == nome.strip().lower():
                return json.loads(linha[1])
    except ErroBanco:
        raise
    except Exception as e:
        raise ErroBanco(f"Erro ao ler o bando '{nome}': {e}")
    return None


def salvar_bando(estado: dict):
    """Cria ou atualiza a linha do bando."""
    try:
        ws = _ws_bandos()
        valores = ws.get_all_values()
        texto = json.dumps(estado, ensure_ascii=False)
        for idx, linha in enumerate(valores):
            if idx == 0:
                continue
            if linha and linha[0].strip().lower() == estado["bando"].strip().lower():
                ws.update_cell(idx + 1, 2, texto)
                ws.update_cell(idx + 1, 3, _agora_iso())
                return
        ws.append_row([estado["bando"], texto, _agora_iso()])
    except ErroBanco:
        raise
    except Exception as e:
        raise ErroBanco(f"Erro ao salvar o bando '{estado['bando']}': {e}")


def registrar_log(bando: str, evento: str, detalhe: str = ""):
    """Histórico (só anexa). Falha no log nunca derruba o comando."""
    try:
        _aba(ABA_LOG, CAB_LOG).append_row([_agora_iso(), bando, evento, detalhe])
    except Exception as e:
        print(f"⚠️ Não consegui gravar o log da navegação: {e}")
