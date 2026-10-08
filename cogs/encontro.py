"""
encontro.py
------------
/encontromaritimo: sorteia um acontecimento enquanto a tripulação navega.
Primeiro decide entre procurado (60%) e encontro marítimo (40%) — nunca os
dois. Se der encontro, sorteia qual: pirata e marinha (35% cada), caçador de
recompensa e rei do mar (15% cada).
"""

import random

import discord
from discord import app_commands
from discord.ext import commands

from cogs.permissoes import is_allowed_role

CHANCE_PROCURADO = 60

PROCURADO = {
    "emoji": "📜",
    "rotulo": "Procurado à vista",
    "cor": 0xC8A165,  # papel de cartaz de recompensa
    "descricao": "Parece que **um procurado anda arrumando confusão na região**.",
}

ENCONTROS = [
    {"peso": 35, "emoji": "🏴‍☠️", "rotulo": "Bando pirata", "cor": 0xB3261E, "alvo": "Um Bando Pirata!"},
    {"peso": 35, "emoji": "⚓", "rotulo": "Marinha", "cor": 0x2F6FDE, "alvo": "Uma Frota da Marinha!"},
    {"peso": 15, "emoji": "🎯", "rotulo": "Caçador de recompensa", "cor": 0xE07B24, "alvo": "Um Caçador de Recompensa!"},
    {"peso": 15, "emoji": "🐉", "rotulo": "Rei do Mar", "cor": 0x7B3FBF, "alvo": "Um Rei do Mar!"},
]


class EncontroCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="encontromaritimo", description="Sorteia o que acontece enquanto a tripulação navega.")
    @is_allowed_role()
    @app_commands.describe(debug="Mostra os números sorteados.")
    async def encontromaritimo(self, interaction: discord.Interaction, debug: bool = False):
        roll = round(random.uniform(0, 100), 1)

        if roll < CHANCE_PROCURADO:
            resultado = PROCURADO
            descricao = PROCURADO["descricao"]
            debug_txt = f"sorteou {roll} de {CHANCE_PROCURADO}% → procurado"
        else:
            resultado = random.choices(ENCONTROS, weights=[e["peso"] for e in ENCONTROS], k=1)[0]
            descricao = (
                "Parece que **há um encontro ao seu aguardo no mar**.\n"
                f"Você está diante de\n### {resultado['emoji']} {resultado['alvo']}"
            )
            debug_txt = f"sorteou {roll} de {CHANCE_PROCURADO}% → encontro ({resultado['rotulo']}, {resultado['peso']}%)"

        if debug:
            descricao += f"\n\n`[debug: {debug_txt}]`"

        embed = discord.Embed(description=descricao, color=resultado["cor"], timestamp=discord.utils.utcnow())
        embed.set_author(name=f"🌊 Encontro Marítimo · {resultado['rotulo']}")
        embed.set_footer(
            text=f"Navegando com {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(EncontroCog(bot))
