"""
encontro.py
------------
/encontromaritimo: sorteia um acontecimento enquanto a tripulação navega, de
acordo com a região. Cada região tem a sua tabela de chances e o ND de cada
encontro (REGIOES). Resultados possíveis: caçada na ilha (um procurado anda
arrumando confusão), bando pirata, frota da Marinha, caçador de recompensa,
rei do mar e, no Calm Belt, "nada".

Totto Land não usa essa tabela: ao falhar na navegação rola-se um Desastre
(1d6, ataques das forças da Big Mom), e nas explorações vale o Desafio das
Ilhas (/desafiodasilhas, 1d12), que também considera o Nível de Confusão (NC).
"""

import random

import discord
from discord import app_commands
from discord.ext import commands

from cogs.permissoes import is_allowed_role

# Como cada resultado aparece. "nd" vem da tabela da região.
RESULTADOS = {
    "cacada": {
        "emoji": "📜", "rotulo": "Caçada na ilha", "cor": 0xC8A165,  # papel de cartaz de recompensa
        "descricao": "Parece que **um procurado anda arrumando confusão na região**.",
    },
    "pirata": {"emoji": "🏴‍☠️", "rotulo": "Bando pirata", "cor": 0xB3261E, "alvo": "Um Bando Pirata!"},
    "marinha": {"emoji": "⚓", "rotulo": "Marinha", "cor": 0x2F6FDE, "alvo": "Uma Frota da Marinha!"},
    "cacador": {"emoji": "🎯", "rotulo": "Caçador de recompensa", "cor": 0xE07B24, "alvo": "Um Caçador de Recompensa!"},
    "rei_do_mar": {"emoji": "🐉", "rotulo": "Rei do Mar", "cor": 0x7B3FBF, "alvo": "Um Rei do Mar!"},
    "nada": {
        "emoji": "🌫️", "rotulo": "Nada à vista", "cor": 0x6B7B8C,
        "descricao": "O mar está calmo e **nada aparece no horizonte**.",
    },
}

# (resultado, chance em %, ND). Cada tabela soma 100.
REGIOES = {
    "paradise": {
        "nome": "Paradise",
        "tabela": [
            ("cacada", 60, None),
            ("pirata", 14, 9),
            ("marinha", 14, 10),
            ("cacador", 6, 11),
            ("rei_do_mar", 6, 11),
        ],
    },
    "novo_mundo": {
        "nome": "Novo Mundo",
        "tabela": [
            ("cacada", 60, None),
            ("pirata", 14, 14),
            ("marinha", 14, 15),
            ("cacador", 6, 16),
            ("rei_do_mar", 6, 16),
        ],
    },
    "calm_belt": {
        "nome": "Calm Belt",
        "tabela": [
            ("pirata", 9, 16),
            ("marinha", 9, 16),
            ("cacador", 12, 16),
            ("rei_do_mar", 30, 16),
            ("nada", 40, None),
        ],
    },
    "totto_land": {"nome": "Totto Land", "desastre": True},
}

# --- TOTTO LAND: desastres na navegação (1d6) ---
COR_TOTTO = 0xE0609B  # rosa doce

# (rótulo, nº de d10 de dano, consequência extra)
DESASTRES_TOTTO = {
    1: ("Frota Tarte Pequena", 5, None),
    2: ("Frota Tarte Média", 10, None),
    3: ("Frota Tarte Grande", 15, None),
    4: ("Oficial Doce (Perseguição)", 20, "O navio **perde metade do deslocamento**."),
    5: ("Oficial Doce (Cerco)", 25, "O navio **perde todo o deslocamento**."),
}

DESASTRE_EMBATE = (
    "Os membros da tripulação poderão executar uma **Técnica Combinada**, utilizando quaisquer técnicas "
    "aprendidas que permitam realizar um ataque conjunto. O dano sofrido pelo navio será igual à diferença "
    "entre **500** e o dano total causado pelo ataque, sendo 0 o dano mínimo. Caso o dano não seja "
    "completamente anulado, o bando será considerado **capturado**.\n"
    "Para escapar, deverá obter sucesso em um Teste de Navegação **CD 25**. A tentativa poderá ser solicitada "
    "a partir da captura, respeitando o intervalo de uma semana entre novas tentativas até obter sucesso."
)

# --- TOTTO LAND: Desafio das Ilhas (1d12 ao iniciar uma exploração) ---
# (resultado máximo do d12, chave)
FAIXAS_DESAFIO = [(4, "nada"), (9, "patrulha"), (11, "combatente"), (12, "oficial")]

ENCONTROS_TOTTO = {
    "nada": {
        "emoji": "🍃", "rotulo": "Passa despercebido", "nd": None, "cor": 0x6B7B8C,
        "descricao": "Por sorte ou destino, o bando passa despercebido.",
    },
    "patrulha": {
        "emoji": "🍬", "rotulo": "Patrulha Doce", "nd": None, "cor": 0xE0609B,
        "descricao": "Formada majoritariamente por Soldados Xadrez, Homies que compõem a base do exército da Big Mom.",
    },
    "combatente": {
        "emoji": "🧁", "rotulo": "Combatente Doce", "nd": 14, "cor": 0xD6409F,
        "descricao": "Pirata subordinado à Big Mom, responsável por combater ameaças em seu território.",
    },
    "oficial": {
        "emoji": "🎂", "rotulo": "Oficial Doce", "nd": 15, "cor": 0xB3261E,
        "descricao": "Um dos filhos da Big Mom, também conhecido como Ministro.",
    },
    "furia": {
        "emoji": "⚔️", "rotulo": "Exército da Fúria", "nd": 16, "cor": 0x8E1B1B,
        "descricao": "Uma enorme tropa enviada para esmagar aqueles que desafiam a Imperatriz ou ameaçam seus filhos.",
    },
    "general": {
        "emoji": "👑", "rotulo": "General Doce", "nd": 17, "cor": 0x5A0F0F,
        "descricao": "Integrante da elite militar dos Piratas da Big Mom, com autoridade abaixo apenas da própria Imperatriz.",
    },
}


def estado_de_cacada(nc: int) -> str:
    """Estado de caçada correspondente ao Nível de Confusão (0-10)."""
    if nc <= 1:
        return "Desconhecidos — nenhuma consequência adicional."
    if nc <= 7:
        return "Monitorados — a CD dos Testes de Navegação aumenta em **+1**."
    if nc <= 9:
        return "Inimigos Públicos — o **Exército da Fúria** aparece na próxima exploração."
    return "Alvos Marcados — um **General Doce** é o encontro da próxima exploração."


def sortear_resultado(tabela: list) -> tuple:
    """Sorteia uma linha da tabela. Retorna (chave, nd, roll, total)."""
    total = sum(chance for _, chance, _ in tabela)
    roll = round(random.uniform(0, total), 1)
    acumulado = 0
    for chave, chance, nd in tabela:
        acumulado += chance
        if roll < acumulado:
            return chave, nd, roll, total
    chave, _, nd = tabela[-1]
    return chave, nd, roll, total


class EncontroCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="encontromaritimo", description="Sorteia o que acontece enquanto a tripulação navega.")
    @is_allowed_role()
    @app_commands.describe(regiao="Onde a tripulação está navegando.", debug="Mostra os números sorteados.")
    @app_commands.choices(regiao=[app_commands.Choice(name=r["nome"], value=chave) for chave, r in REGIOES.items()])
    async def encontromaritimo(self, interaction: discord.Interaction, regiao: app_commands.Choice[str], debug: bool = False):
        config = REGIOES[regiao.value]
        if config.get("desastre"):
            await self._enviar_desastre(interaction, config, debug)
            return

        chave, nd, roll, total = sortear_resultado(config["tabela"])
        resultado = RESULTADOS[chave]

        if "alvo" in resultado:
            descricao = (
                "Parece que **há um encontro ao seu aguardo no mar**.\n"
                f"Você está diante de\n### {resultado['emoji']} {resultado['alvo']}\n**ND {nd}**"
            )
        else:
            descricao = resultado["descricao"]

        if debug:
            chance = next(c for k, c, _ in config["tabela"] if k == chave)
            descricao += f"\n\n`[debug: {config['nome']} · sorteou {roll} de {total}% → {resultado['rotulo']} ({chance}%)]`"

        embed = discord.Embed(description=descricao, color=resultado["cor"], timestamp=discord.utils.utcnow())
        embed.set_author(name=f"🌊 Encontro Marítimo · {config['nome']} · {resultado['rotulo']}")
        embed.set_footer(
            text=f"Navegando com {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.response.send_message(embed=embed)

    async def _enviar_desastre(self, interaction: discord.Interaction, config: dict, debug: bool):
        """Totto Land: no lugar do encontro marítimo normal, rola 1d6 de desastre."""
        roll = random.randint(1, 6)
        debug_txt = f"d6 → {roll}"

        if roll in DESASTRES_TOTTO:
            rotulo, qtd, extra = DESASTRES_TOTTO[roll]
            dados = [random.randint(1, 10) for _ in range(qtd)]
            descricao = f"### 🧨 {rotulo}\nO navio sofre **{qtd}d10** de dano → 🎲 **{sum(dados)}**"
            if extra:
                descricao += f"\n{extra}"
            debug_txt += f" · {qtd}d10: {dados}"
        else:
            rotulo = "Oficial Doce (Embate)"
            descricao = f"### 🧨 {rotulo}\n{DESASTRE_EMBATE}"

        descricao += "\n\n⚠️ Dentro de Totto Land, não existem Ilhas Secretas."
        if debug:
            descricao += f"\n`[debug: {debug_txt}]`"

        embed = discord.Embed(description=descricao, color=COR_TOTTO, timestamp=discord.utils.utcnow())
        embed.set_author(name=f"🌊 Encontro Marítimo · {config['nome']} · Desastre ({roll})")
        embed.set_footer(
            text=f"Navegando com {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="desafiodasilhas", description="Totto Land: sorteia o encontro ao iniciar uma exploração.")
    @is_allowed_role()
    @app_commands.describe(
        nc="Nível de Confusão atual do bando (0 a 10). NC alto força um encontro específico.",
        debug="Mostra os números sorteados.",
    )
    async def desafiodasilhas(self, interaction: discord.Interaction, nc: app_commands.Range[int, 0, 10] = None, debug: bool = False):
        forcado = None
        if nc is not None and nc >= 10:
            forcado = "general"
        elif nc is not None and nc >= 8:
            forcado = "furia"

        if forcado:
            chave = forcado
            debug_txt = f"NC {nc} força o encontro (prioridade sobre o 1d12)"
        else:
            roll = random.randint(1, 12)
            chave = next(c for ate, c in FAIXAS_DESAFIO if roll <= ate)
            debug_txt = f"d12 → {roll}"

        encontro = ENCONTROS_TOTTO[chave]
        titulo = f"{encontro['emoji']} {encontro['rotulo']}" + (f" — ND {encontro['nd']}" if encontro["nd"] else "")
        descricao = f"### {titulo}\n{encontro['descricao']}"

        if nc is not None:
            descricao += f"\n\n🚨 **NC {nc}** · {estado_de_cacada(nc)}"
        if forcado:
            descricao += "\nEsse encontro tem prioridade sobre o resultado do Desafio das Ilhas."
        if chave != "nada":
            descricao += "\n\n-# Um encontro não significa necessariamente combate: depende das circunstâncias e do Nível de Confusão do bando."
        if debug:
            descricao += f"\n`[debug: {debug_txt}]`"

        embed = discord.Embed(description=descricao, color=encontro["cor"], timestamp=discord.utils.utcnow())
        embed.set_author(name="⚔️ Desafio das Ilhas · Totto Land")
        embed.set_footer(
            text=f"Explorando com {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(EncontroCog(bot))
