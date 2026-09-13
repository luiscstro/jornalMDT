"""
procurado.py
-------------
Sistema de caça a procurados: em /procurado quem executa escolhe QUAL
procurado (pirata ou marinheiro) vai caçar e EM QUAL mar; só a ilha dentro
daquele mar é sorteada (mesma chance entre todas). Uma vez escolhido, o
procurado fica travado por 2 semanas (cacadas_db.DIAS_TRAVA) e não pode ser
escolhido de novo até o prazo passar. Procurados que estão na edição atual
do jornal também ficam de fora, pra não repetir o mesmo alvo em dois lugares
ao mesmo tempo.
"""

import random

import discord
from discord import app_commands
from discord.ext import commands

import database as db
import regioes_db as rdb
import cacadas_db as cdb
from cogs.permissoes import is_allowed_role


async def mar_autocomplete(interaction: discord.Interaction, current: str) -> list:
    regioes = rdb.listar_regioes(apenas_ativas=True)
    opcoes = [r["nome"] for r in regioes if r["tem_procurado"]]
    current = (current or "").lower()
    filtradas = [nome for nome in opcoes if current in nome.lower()]
    return [app_commands.Choice(name=nome, value=nome) for nome in filtradas[:25]]


async def procurado_disponivel_autocomplete(interaction: discord.Interaction, current: str) -> list:
    current = (current or "").lower()
    disponiveis = [
        (nome, tipo) for (nome, tipo) in db.listar_procurados()
        if not cdb.procurado_esta_travado(nome) and not cdb.nome_no_jornal_atual(nome)
    ]
    filtrados = [(nome, tipo) for (nome, tipo) in disponiveis if current in nome.lower()]
    return [app_commands.Choice(name=f"{nome} ({tipo})", value=nome) for (nome, tipo) in filtrados[:25]]


async def cacada_ativa_autocomplete(interaction: discord.Interaction, current: str) -> list:
    ativas = cdb.buscar_cacadas_ativas_por_nome(current)
    return [
        app_commands.Choice(name=f"{c['procurado_nome']} (caçado por {c['user_nome']})", value=c["procurado_nome"])
        for c in ativas[:25]
    ]


class ProcuradoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cdb.init_db()

    @app_commands.command(name="procurado", description="Registra a caça a um procurado escolhido e sorteia a ilha dele num mar.")
    @is_allowed_role()
    @app_commands.describe(procurado="Qual procurado caçar.", mar="Em qual mar procurar.")
    @app_commands.autocomplete(procurado=procurado_disponivel_autocomplete, mar=mar_autocomplete)
    async def procurado_slash(self, interaction: discord.Interaction, procurado: str, mar: str):
        await interaction.response.defer()

        regiao = rdb.obter_regiao_por_nome(mar)
        if not regiao or not regiao["tem_procurado"]:
            await interaction.followup.send(f"❌ **{mar}** não é um mar válido para caça a procurados.", ephemeral=True)
            return

        locais = rdb.listar_locais(regiao["id"])
        if not locais:
            await interaction.followup.send(f"❌ **{mar}** não tem nenhuma ilha/local cadastrado.", ephemeral=True)
            return

        todos_procurados = db.listar_procurados()
        if not todos_procurados:
            erro = db.obter_ultimo_erro_conexao()
            if erro:
                await interaction.followup.send(f"❌ Não consegui conectar à planilha do Google: `{erro}`", ephemeral=True)
            else:
                await interaction.followup.send("❌ Não há nenhum procurado cadastrado na planilha.", ephemeral=True)
            return

        mapa_procurados = {nome.lower(): (nome, tipo) for nome, tipo in todos_procurados}
        entrada = mapa_procurados.get(procurado.lower())
        if not entrada:
            await interaction.followup.send(f"❌ **{procurado}** não consta na planilha.", ephemeral=True)
            return

        nome_p, tipo_p = entrada

        if cdb.procurado_esta_travado(nome_p):
            await interaction.followup.send(f"❌ **{nome_p}** já está sendo caçado por alguém — a trava ainda não acabou.", ephemeral=True)
            return

        if cdb.nome_no_jornal_atual(nome_p):
            await interaction.followup.send(f"❌ **{nome_p}** está na edição atual do jornal e não pode ser caçado agora.", ephemeral=True)
            return

        local_p = random.choice(locais)["nome"]

        cacada = cdb.registrar_cacada(
            procurado_nome=nome_p,
            tipo=tipo_p,
            mar=mar,
            local=local_p,
            user_id=interaction.user.id,
            user_nome=interaction.user.display_name,
        )

        expira_ts = int(cacada["expira_em"].timestamp())
        emoji = "🏴‍☠️" if tipo_p == "Pirata" else "⚓"

        embed = discord.Embed(
            title=f"{emoji} Caça iniciada!",
            description=f"**{nome_p}** ({tipo_p}) foi localizado em **{local_p}** ({mar}).",
            color=discord.Color.dark_gold(),
        )
        embed.add_field(name="Caçador", value=interaction.user.mention, inline=True)
        embed.add_field(name="Trava libera em", value=f"<t:{expira_ts}:F> (<t:{expira_ts}:R>)", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="procurados_ativos", description="Lista as caçadas em andamento e quando cada trava libera.")
    @is_allowed_role()
    async def procurados_ativos_slash(self, interaction: discord.Interaction):
        ativas = cdb.listar_cacadas_ativas()

        if not ativas:
            await interaction.response.send_message("ℹ️ Nenhuma caçada ativa no momento.", ephemeral=True)
            return

        embed = discord.Embed(title="Caçadas em andamento", color=discord.Color.orange())
        for c in ativas:
            expira_ts = int(c["expira_em"].timestamp())
            embed.add_field(
                name=f"{c['procurado_nome']} ({c['tipo']})",
                value=(
                    f"Mar: **{c['mar']}** • Local: **{c['local']}**\n"
                    f"Caçador: **{c['user_nome']}** • Libera em <t:{expira_ts}:R>"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="procurado_liberar", description="Libera manualmente a trava de um procurado antes do prazo.")
    @is_allowed_role()
    @app_commands.describe(nome="O procurado com caçada ativa a liberar.")
    @app_commands.autocomplete(nome=cacada_ativa_autocomplete)
    async def procurado_liberar_slash(self, interaction: discord.Interaction, nome: str):
        ativas = cdb.buscar_cacadas_ativas_por_nome(nome)
        correspondente = next((c for c in ativas if c["procurado_nome"].lower() == nome.lower()), None)

        if not correspondente:
            await interaction.response.send_message(f"❌ Não há caçada ativa para **{nome}**.", ephemeral=True)
            return

        cdb.liberar_cacada(correspondente["id"])
        await interaction.response.send_message(f"🔓 Trava de **{nome}** liberada. Já pode ser caçado de novo.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ProcuradoCog(bot))
