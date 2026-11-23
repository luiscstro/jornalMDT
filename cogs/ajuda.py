"""
ajuda.py
---------
/ajuda: sem argumento mostra o resumo de todos os comandos; com `comando`
mostra a explicação detalhada daquele comando. Os textos ficam em ajuda_dados.py.
"""

import difflib

import discord
from discord import app_commands
from discord.ext import commands

from ajuda_dados import CATEGORIAS, COMANDOS

COR = 0x2F8FBF
COR_ERRO = 0xB3261E


def _normalizar(texto: str) -> str:
    return (texto or "").strip().lstrip("/").lower()


def _cortar(texto: str, limite: int = 1024) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def _embed_geral() -> discord.Embed:
    embed = discord.Embed(
        title="📖 Ajuda do bot",
        description=(
            "Resumo dos comandos. Pra ver os detalhes de um deles, use "
            "`/ajuda comando:<nome>`.\n🔒 = só quem tem os cargos de staff."
        ),
        color=COR,
    )
    for titulo, nomes in CATEGORIAS:
        linhas = []
        for nome in nomes:
            c = COMANDOS[nome]
            cadeado = " 🔒" if c["staff"] else ""
            linhas.append(f"`/{nome}`{cadeado} — {c['resumo']}")
        embed.add_field(name=titulo, value=_cortar("\n".join(linhas)), inline=False)
    embed.set_footer(text="O jornal sai sozinho todo domingo às 15:00 (UTC).")
    return embed


def _embed_comando(nome: str) -> discord.Embed:
    c = COMANDOS[nome]
    categoria = next((t for t, nomes in CATEGORIAS if nome in nomes), "")
    embed = discord.Embed(title=f"/{nome}", description=c["detalhes"], color=COR)
    embed.add_field(name="Como usar", value=f"```{c['uso']}```", inline=False)
    if c["params"]:
        embed.add_field(
            name="Parâmetros",
            value=_cortar("\n".join(f"• **{p}**: {d}" for p, d in c["params"])),
            inline=False,
        )
    embed.add_field(
        name="Quem pode usar",
        value="🔒 Só staff (cargos permitidos)" if c["staff"] else "Todos",
        inline=True,
    )
    if c["ver"]:
        embed.add_field(name="Veja também", value=" ".join(f"`/{v}`" for v in c["ver"]), inline=True)
    if categoria:
        embed.set_footer(text=categoria)
    return embed


async def comando_autocomplete(interaction: discord.Interaction, current: str):
    busca = _normalizar(current)
    opcoes = []
    for nome, c in COMANDOS.items():
        if busca in nome or busca in c["resumo"].lower():
            rotulo = f"/{nome} — {c['resumo']}"
            opcoes.append(app_commands.Choice(name=rotulo[:100], value=nome))
    return opcoes[:25]


class AjudaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ajuda", description="Explica os comandos do bot. Use 'comando' pra ver os detalhes de um.")
    @app_commands.describe(comando="O comando que você quer entender melhor (deixe vazio pra ver todos).")
    @app_commands.autocomplete(comando=comando_autocomplete)
    async def ajuda(self, interaction: discord.Interaction, comando: str = None):
        if not comando or not comando.strip():
            await interaction.response.send_message(embed=_embed_geral(), ephemeral=True)
            return

        nome = _normalizar(comando)
        if nome not in COMANDOS:
            parecidos = difflib.get_close_matches(nome, list(COMANDOS), n=3, cutoff=0.5)
            texto = f"❌ Não conheço o comando **{comando.strip()}**."
            if parecidos:
                texto += " Você quis dizer " + ", ".join(f"`/{p}`" for p in parecidos) + "?"
            texto += "\nUse `/ajuda` sem nada pra ver a lista."
            await interaction.response.send_message(embed=discord.Embed(description=texto, color=COR_ERRO), ephemeral=True)
            return

        await interaction.response.send_message(embed=_embed_comando(nome), ephemeral=True)


async def setup(bot):
    await bot.add_cog(AjudaCog(bot))
