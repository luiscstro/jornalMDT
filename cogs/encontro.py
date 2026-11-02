"""
encontro.py
------------
/encontromaritimo: sorteia um acontecimento enquanto a tripulação navega, de
acordo com a região. Cada região tem a sua tabela de chances e o ND de cada
encontro (REGIOES). Resultados possíveis: caçada na ilha (um procurado anda
arrumando confusão), bando pirata, frota da Marinha, caçador de recompensa,
rei do mar e, no Calm Belt, "nada".
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
}


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


async def setup(bot):
    await bot.add_cog(EncontroCog(bot))
