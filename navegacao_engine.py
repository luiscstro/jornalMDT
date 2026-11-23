"""
navegacao_engine.py
--------------------
Regras da navegação do Novo Mundo com Log Pose 3A. Lógica pura (sem Discord
e sem planilha): recebe o estado do bando + a lista de ilhas e devolve o
novo estado. Fica fácil de testar e de ajustar as constantes abaixo.

Resumo das regras (ver docs/REGRAS_NAVEGACAO.md):
- Bando parte de Raijin, Risky Red ou Mystoria. Depois de explorar, o Log
  Pose sincroniza 3 ilhas, cada agulha com um tipo (Estável/Moderada/Instável).
- Áreas 1 -> 2 -> 3 -> Laugh Tale, liberadas por Dressrosa, Wano e Elbaph
  (só sincronizam depois de 20 progressões na área).
- Totto Land (Área 2): se uma agulha sorteia, as 3 apontam pra lá.
"""

import copy
import datetime
import random

from navegacao_dados import NOME_TOTTO, NOME_LAUGH_TALE

# --- Constantes de balanceamento (ajuste aqui) ---------------------------------
PROGRESSOES_PRINCIPAL = 20      # progressões na área pra ilha principal poder sincronizar
PROGRESSOES_SAIR_TOTTO = 5      # progressões dentro de Totto Land pra poder sair
DIAS_RESSINCRONIZAR_TOTTO = 7   # espera pra ressincronizar quando Totto é apontada
PESO_AREA_ANTERIOR = 0.1        # chance relativa de ilhas de áreas já exploradas (área atual = 1)
PESO_PRINCIPAL = 5              # chance relativa da ilha principal quando liberada
PESOS_TIPO_AGULHA = {"E": 1, "M": 1, "I": 1}  # sorteio do tipo de cada agulha

AGULHAS = {
    "E": {"rotulo": "Estável", "emoji": "🟢", "cd": 0, "prog": 1.0},
    "M": {"rotulo": "Moderada", "emoji": "🟡", "cd": 2, "prog": 1.5},
    "I": {"rotulo": "Instável", "emoji": "🔴", "cd": 5, "prog": 3.0},
}


class ErroRegra(Exception):
    """Violação de regra, com mensagem pronta pra mostrar ao usuário."""


def _agora():
    return datetime.datetime.now(datetime.timezone.utc)


def _chave(nome: str) -> str:
    return (nome or "").strip().lower()


def _nomes(lista) -> set:
    return {_chave(n) for n in lista}


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------

def novo_estado(bando: str, ilha_inicial: str) -> dict:
    return {
        "bando": bando,
        "area": 1,
        "local": ilha_inicial,
        "prog_area": 0.0,
        "no_totto": False,
        "prog_totto": 0.0,
        "totto_apontado": False,
        "totto_ressinc_em": None,
        "totto_saiu": False,
        "agulhas": [],
        "visitadas": [ilha_inicial],
        "secretas": [],
        "calm": [],
        "fim": False,
    }


def _principal_da_area(ilhas: list, area: int):
    return next((i for i in ilhas if i["area"] == area and i["tipo"] == "principal"), None)


def _limite_principal(area: int) -> int:
    return 0 if area >= 4 else PROGRESSOES_PRINCIPAL


# ---------------------------------------------------------------------------
# Sincronização do Log Pose
# ---------------------------------------------------------------------------

def _sortear_sem_repeticao(candidatos: list, qtd: int, rng) -> list:
    """candidatos: [(ilha, peso)]. Sorteio ponderado sem reposição."""
    restantes = list(candidatos)
    escolhidos = []
    while restantes and len(escolhidos) < qtd:
        item = rng.choices(restantes, weights=[p for _, p in restantes], k=1)[0]
        escolhidos.append(item[0])
        restantes.remove(item)
    return escolhidos


def _pool_normal(estado: dict, ilhas: list) -> list:
    """[(ilha, peso)] de tudo que o Log Pose pode apontar fora de Totto Land."""
    visitadas = _nomes(estado["visitadas"])
    area = estado["area"]
    pool = []
    for i in ilhas:
        if i["tipo"] == "sincronizavel" and isinstance(i["area"], int) and i["area"] <= area:
            if _chave(i["nome"]) in visitadas:
                continue
            pool.append((i, 1 if i["area"] == area else PESO_AREA_ANTERIOR))
        elif i["tipo"] == "totto" and area >= 2:
            # Totto nunca sai do pool: dá pra voltar lá quantas vezes quiser.
            pool.append((i, 1 if area == 2 else PESO_AREA_ANTERIOR))

    principal = _principal_da_area(ilhas, area)
    if (principal and _chave(principal["nome"]) not in visitadas
            and estado["prog_area"] >= _limite_principal(area)):
        pool.append((principal, PESO_PRINCIPAL))
    return pool


def _sortear_tipo(rng) -> str:
    tipos = list(PESOS_TIPO_AGULHA)
    return rng.choices(tipos, weights=[PESOS_TIPO_AGULHA[t] for t in tipos], k=1)[0]


def _agulha(ilha: dict, tipo: str) -> dict:
    return {
        "ilha": ilha["nome"], "tipo": tipo, "area": ilha["area"],
        "principal": ilha["tipo"] == "principal", "totto": ilha["tipo"] == "totto",
    }


def sincronizar(estado: dict, ilhas: list, rng=random, agora=None, forcar: bool = False) -> dict:
    """Sincroniza o Log Pose. Devolve o NOVO estado (o original não é alterado).
    Levanta ErroRegra se não for possível."""
    agora = agora or _agora()
    e = copy.deepcopy(estado)

    if e["fim"]:
        raise ErroRegra("Esse bando já chegou em **Laugh Tale**. A jornada acabou! 🏴‍☠️")

    if e["totto_apontado"] and e["totto_ressinc_em"] and not forcar:
        liberado = datetime.datetime.fromisoformat(e["totto_ressinc_em"])
        if agora < liberado:
            raise ErroRegra(
                f"As agulhas estão apontando pra **Totto Land**. O bando pode ir pra lá (`/viajar`) "
                f"ou esperar pra ressincronizar: <t:{int(liberado.timestamp())}:R>."
            )

    e["totto_apontado"] = False
    e["totto_ressinc_em"] = None

    # --- Dentro de Totto Land: só ilhas do arquipélago, tudo Estável ---
    if e["no_totto"]:
        visitadas = _nomes(e["visitadas"])
        candidatos = [(i, 1) for i in ilhas if i["tipo"] == "totto_ilha" and _chave(i["nome"]) not in visitadas]
        if not candidatos:
            raise ErroRegra(
                "Não há ilhas de Totto Land disponíveis pra sincronizar (cadastre na aba **NM_Ilhas** "
                "com tipo `totto_ilha`, ou todas já foram visitadas). Se tiver "
                f"{PROGRESSOES_SAIR_TOTTO} progressões, use `/totto_sair`."
            )
        escolhidas = _sortear_sem_repeticao(candidatos, 3, rng)
        e["agulhas"] = [_agulha(i, "E") for i in escolhidas]
        return e

    pool = _pool_normal(e, ilhas)
    if not pool:
        raise ErroRegra("Não há nenhuma ilha disponível pra sincronizar. Confira a aba **NM_Ilhas**.")

    # Em Laugh Tale: a ilha final sempre aparece numa das agulhas.
    if e["area"] >= 4:
        final = next((par for par in pool if par[0]["nome"] == NOME_LAUGH_TALE), None)
        if final:
            resto = [p for p in pool if p is not final]
            escolhidas = [final[0]] + _sortear_sem_repeticao(resto, 2, rng)
            rng.shuffle(escolhidas)
        else:
            escolhidas = _sortear_sem_repeticao(pool, 3, rng)
    else:
        escolhidas = _sortear_sem_repeticao(pool, 3, rng)

    # Totto Land sorteada (e o bando ainda nunca saiu de lá): todas as agulhas apontam pra ela.
    totto = next((i for i in escolhidas if i["tipo"] == "totto"), None)
    if totto and not e["totto_saiu"]:
        e["agulhas"] = [_agulha(totto, "E") for _ in range(3)]
        e["totto_apontado"] = True
        e["totto_ressinc_em"] = (agora + datetime.timedelta(days=DIAS_RESSINCRONIZAR_TOTTO)).isoformat()
        return e

    e["agulhas"] = [_agulha(i, _sortear_tipo(rng)) for i in escolhidas]
    return e


# ---------------------------------------------------------------------------
# Viajar (resultado do Teste de Navegação)
# ---------------------------------------------------------------------------

def viajar(estado: dict, ilhas: list, agulha: int, sucesso: bool, rng=random) -> tuple:
    """Aplica o resultado do Teste de Navegação pra agulha escolhida (1 a 3).
    Retorna (novo_estado, resultado) com resultado = {"tipo": ..., "ilha": ..., "prog": ...}."""
    e = copy.deepcopy(estado)
    if e["fim"]:
        raise ErroRegra("Esse bando já chegou em **Laugh Tale**.")
    if not e["agulhas"]:
        raise ErroRegra("O Log Pose não está sincronizado. Use `/navegar` primeiro.")
    if not 1 <= agulha <= len(e["agulhas"]):
        raise ErroRegra(f"Escolha uma agulha de 1 a {len(e['agulhas'])}.")

    ag = e["agulhas"][agulha - 1]
    e["agulhas"] = []
    e["totto_apontado"] = False
    e["totto_ressinc_em"] = None

    # ---------------- sucesso ----------------
    if sucesso:
        if ag["totto"]:
            e["no_totto"] = True
            e["prog_totto"] = 0.0
            e["local"] = ag["ilha"]
            return e, {"tipo": "totto_entrada", "ilha": ag["ilha"], "prog": 0.0}

        if ag["principal"]:
            e["visitadas"].append(ag["ilha"])
            e["local"] = ag["ilha"]
            e["prog_area"] = 0.0
            if ag["ilha"] == NOME_LAUGH_TALE:
                e["fim"] = True
                return e, {"tipo": "laugh_tale", "ilha": ag["ilha"], "prog": 0.0}
            e["area"] += 1
            return e, {"tipo": "principal", "ilha": ag["ilha"], "prog": 0.0, "area": e["area"]}

        prog = 1.0 if e["no_totto"] else AGULHAS[ag["tipo"]]["prog"]
        e["prog_area"] += prog
        if e["no_totto"]:
            e["prog_totto"] += prog
        e["visitadas"].append(ag["ilha"])
        e["local"] = ag["ilha"]
        return e, {"tipo": "chegada", "ilha": ag["ilha"], "prog": prog}

    # ---------------- falha ----------------
    if e["no_totto"]:
        # Dentro de Totto Land não existem Ilhas Secretas: rola-se um Desastre (/encontromaritimo).
        return e, {"tipo": "falha_totto", "ilha": None, "prog": 0.0}

    if ag["tipo"] == "I":
        achadas = _nomes(e["calm"])
        candidatas = [i for i in ilhas if i["tipo"] == "calm" and _chave(i["nome"]) not in achadas]
        if not candidatas:
            return e, {"tipo": "calm_vazio", "ilha": None, "prog": 0.0}
        ilha = rng.choice(candidatas)
        e["calm"].append(ilha["nome"])
        e["local"] = ilha["nome"]
        return e, {"tipo": "calm", "ilha": ilha["nome"], "prog": 0.0, "nivel": ilha.get("nota", "")}

    achadas = _nomes(e["secretas"])
    candidatas = [i for i in ilhas if i["tipo"] == "secreta" and i["area"] == e["area"]
                  and _chave(i["nome"]) not in achadas]
    if not candidatas:
        return e, {"tipo": "secreta_vazia", "ilha": None, "prog": 0.0}
    ilha = rng.choice(candidatas)
    e["secretas"].append(ilha["nome"])
    e["local"] = ilha["nome"]
    return e, {"tipo": "secreta", "ilha": ilha["nome"], "prog": 0.0}


# ---------------------------------------------------------------------------
# Sair de Totto Land
# ---------------------------------------------------------------------------

def sair_totto(estado: dict) -> dict:
    e = copy.deepcopy(estado)
    if not e["no_totto"]:
        raise ErroRegra("Esse bando não está em Totto Land.")
    if e["prog_totto"] < PROGRESSOES_SAIR_TOTTO:
        raise ErroRegra(
            f"Só dá pra sair de Totto Land com **{PROGRESSOES_SAIR_TOTTO} progressões** dentro do arquipélago "
            f"(o bando tem **{formatar_prog(e['prog_totto'])}**)."
        )
    e["no_totto"] = False
    e["totto_saiu"] = True
    e["agulhas"] = []
    return e


def formatar_prog(valor: float) -> str:
    return str(int(valor)) if float(valor).is_integer() else f"{valor:.1f}"
