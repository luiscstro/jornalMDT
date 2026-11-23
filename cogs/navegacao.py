"""
navegacao.py
-------------
Navegação do Novo Mundo com Log Pose 3A (regras em navegacao_engine.py,
armazenamento no Google Sheets em navegacao_db.py).

Comandos (todos só pra cargos permitidos): /navegacao_iniciar, /navegar,
/viajar, /totto_sair, /navegacao_status, /navegacao_ajustar.
"""

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

import navegacao_db as ndb
import navegacao_engine as eng
from navegacao_dados import INICIAIS, NOME_TOTTO
from cogs.permissoes import is_allowed_role

COR = 0x2F8FBF
COR_TOTTO = 0xE0609B
COR_ERRO = 0xB3261E

_locks: dict = {}


def _lock(bando: str) -> asyncio.Lock:
    return _locks.setdefault(bando.strip().lower(), asyncio.Lock())


async def bando_autocomplete(interaction: discord.Interaction, current: str):
    try:
        nomes = await asyncio.to_thread(ndb.listar_nomes_bandos)
    except Exception:
        return []
    current = (current or "").lower()
    return [app_commands.Choice(name=n, value=n) for n in nomes if current in n.lower()][:25]


def _linha_agulha(n: int, ag: dict, no_totto: bool) -> str:
    info = eng.AGULHAS[ag["tipo"]]
    if ag["totto"]:
        extra = "🍬 aponta pra Totto Land"
    elif no_totto:
        extra = "CD normal · +1 progressão"
    else:
        cd = "CD normal" if not info["cd"] else f"CD **+{info['cd']}**"
        falha = " · falha leva ao **Calm Belt**" if ag["tipo"] == "I" else ""
        extra = f"{cd} · +{eng.formatar_prog(info['prog'])} progressão{falha}"
    marca = ""
    if ag["principal"]:
        marca = " ⭐ **(ilha principal)**"
    return f"{info['emoji']} **Agulha {n} · {info['rotulo']}** → **{ag['ilha']}**{marca}\n   ↳ {extra}"


def _embed_agulhas(e: dict) -> discord.Embed:
    if e["totto_apontado"]:
        embed = discord.Embed(
            title="🍬 O Log Pose enlouqueceu: todas as agulhas apontam pra Totto Land!",
            description="\n".join(_linha_agulha(i + 1, a, False) for i, a in enumerate(e["agulhas"])),
            color=COR_TOTTO,
        )
        embed.add_field(
            name="O que o bando faz?",
            value="• **Ir pra lá:** `/viajar` (qualquer agulha).\n"
                  f"• **Esperar** e tentar ressincronizar: `/navegar` {_quando(e)}.",
            inline=False,
        )
    else:
        local_txt = f"em **{e['local']}**"
        embed = discord.Embed(
            title="🧭 Log Pose 3A sincronizado",
            description=f"O bando está {local_txt}.\n\n"
                        + "\n".join(_linha_agulha(i + 1, a, e["no_totto"]) for i, a in enumerate(e["agulhas"])),
            color=COR_TOTTO if e["no_totto"] else COR,
        )
        embed.add_field(name="Próximo passo", value="Faça o **Teste de Navegação** e use `/viajar` com o resultado.", inline=False)
    embed.set_footer(text=_rodape(e))
    return embed


def _quando(e: dict) -> str:
    import datetime
    if not e.get("totto_ressinc_em"):
        return ""
    ts = int(datetime.datetime.fromisoformat(e["totto_ressinc_em"]).timestamp())
    return f"a partir de <t:{ts}:F> (<t:{ts}:R>)"


def _rodape(e: dict) -> str:
    base = f"{e['bando']} · Área {e['area']} · {eng.formatar_prog(e['prog_area'])}/{eng._limite_principal(e['area']) or '—'} progressões"
    if e["no_totto"]:
        base += f" · Totto Land {eng.formatar_prog(e['prog_totto'])}/{eng.PROGRESSOES_SAIR_TOTTO}"
    return base


def _embed_status(e: dict) -> discord.Embed:
    embed = discord.Embed(title=f"🗺️ {e['bando']} — Novo Mundo", color=COR_TOTTO if e["no_totto"] else COR)
    embed.add_field(name="Localização", value=f"**{e['local']}**" + (" 🍬 (dentro de Totto Land)" if e["no_totto"] else ""), inline=False)
    limite = eng._limite_principal(e["area"])
    embed.add_field(
        name=f"Área {e['area']}",
        value=f"Progressão: **{eng.formatar_prog(e['prog_area'])}**" + (f" / {limite}" if limite else ""),
        inline=True,
    )
    if e["no_totto"]:
        embed.add_field(
            name="Totto Land",
            value=f"**{eng.formatar_prog(e['prog_totto'])}** / {eng.PROGRESSOES_SAIR_TOTTO} pra poder sair",
            inline=True,
        )
    embed.add_field(
        name="Explorado",
        value=f"{len(e['visitadas'])} ilhas · {len(e['secretas'])} secretas · {len(e['calm'])} no Calm Belt",
        inline=False,
    )
    if e["agulhas"]:
        embed.add_field(
            name="Log Pose atual",
            value="\n".join(_linha_agulha(i + 1, a, e["no_totto"]) for i, a in enumerate(e["agulhas"])),
            inline=False,
        )
    else:
        embed.add_field(name="Log Pose atual", value="Não sincronizado. Use `/navegar`.", inline=False)
    if e["fim"]:
        embed.add_field(name="🏴‍☠️", value="O bando chegou em **Laugh Tale**!", inline=False)
    return embed


def _msg_erro(texto: str) -> discord.Embed:
    return discord.Embed(description=f"❌ {texto}", color=COR_ERRO)


class NavegacaoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _carregar(self, interaction, bando: str):
        """Busca o bando; responde com erro e devolve None se não existir."""
        estado = await asyncio.to_thread(ndb.obter_bando, bando)
        if not estado:
            await interaction.followup.send(
                embed=_msg_erro(f"O bando **{bando}** não existe. Use `/navegacao_iniciar`."), ephemeral=True)
        return estado

    # ------------------------------------------------------------------
    @app_commands.command(name="navegacao_iniciar", description="Cria um bando no Novo Mundo, partindo de uma das 3 ilhas iniciais.")
    @is_allowed_role()
    @app_commands.describe(bando="Nome do bando.", ilha="Ilha de partida.")
    @app_commands.choices(ilha=[app_commands.Choice(name=n, value=n) for n in INICIAIS])
    async def navegacao_iniciar(self, interaction: discord.Interaction, bando: str, ilha: app_commands.Choice[str]):
        await interaction.response.defer()
        bando = bando.strip()
        async with _lock(bando):
            try:
                if await asyncio.to_thread(ndb.obter_bando, bando):
                    await interaction.followup.send(embed=_msg_erro(f"Já existe um bando chamado **{bando}**."), ephemeral=True)
                    return
                estado = eng.novo_estado(bando, ilha.value)
                await asyncio.to_thread(ndb.salvar_bando, estado)
                await asyncio.to_thread(ndb.registrar_log, bando, "inicio", ilha.value)
            except ndb.ErroBanco as e:
                await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
                return
        embed = discord.Embed(
            title="⛵ Bando pronto pra zarpar",
            description=f"**{bando}** parte de **{ilha.value}**.\nDepois de explorar a ilha, use `/navegar` pra sincronizar o Log Pose 3A.",
            color=COR,
        )
        await interaction.followup.send(embed=embed)

    # ------------------------------------------------------------------
    @app_commands.command(name="navegar", description="Sincroniza o Log Pose 3A (sorteia as 3 ilhas e o tipo de cada agulha).")
    @is_allowed_role()
    @app_commands.describe(bando="Nome do bando.", forcar="Ignora a espera de 1 semana de Totto Land (uso do mestre).")
    @app_commands.autocomplete(bando=bando_autocomplete)
    async def navegar(self, interaction: discord.Interaction, bando: str, forcar: bool = False):
        await interaction.response.defer()
        async with _lock(bando):
            try:
                estado = await self._carregar(interaction, bando)
                if not estado:
                    return
                ilhas = await asyncio.to_thread(ndb.listar_ilhas)
                novo = eng.sincronizar(estado, ilhas, forcar=forcar)
                await asyncio.to_thread(ndb.salvar_bando, novo)
                resumo = " | ".join(f"{a['tipo']}:{a['ilha']}" for a in novo["agulhas"])
                await asyncio.to_thread(ndb.registrar_log, novo["bando"], "sincronizou", resumo)
            except eng.ErroRegra as e:
                await interaction.followup.send(embed=_msg_erro(str(e)))
                return
            except ndb.ErroBanco as e:
                await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
                return
        await interaction.followup.send(embed=_embed_agulhas(novo))

    # ------------------------------------------------------------------
    @app_commands.command(name="viajar", description="Aplica o resultado do Teste de Navegação para uma agulha do Log Pose.")
    @is_allowed_role()
    @app_commands.describe(bando="Nome do bando.", agulha="Qual agulha o bando seguiu (1 a 3).", resultado="Resultado do Teste de Navegação.")
    @app_commands.choices(resultado=[
        app_commands.Choice(name="Sucesso", value="sucesso"),
        app_commands.Choice(name="Falha", value="falha"),
    ])
    @app_commands.autocomplete(bando=bando_autocomplete)
    async def viajar(self, interaction: discord.Interaction, bando: str, agulha: app_commands.Range[int, 1, 3],
                     resultado: app_commands.Choice[str]):
        await interaction.response.defer()
        async with _lock(bando):
            try:
                estado = await self._carregar(interaction, bando)
                if not estado:
                    return
                ilhas = await asyncio.to_thread(ndb.listar_ilhas)
                novo, res = eng.viajar(estado, ilhas, agulha, resultado.value == "sucesso")
                await asyncio.to_thread(ndb.salvar_bando, novo)
                await asyncio.to_thread(ndb.registrar_log, novo["bando"], f"viajou:{res['tipo']}", res.get("ilha") or "")
            except eng.ErroRegra as e:
                await interaction.followup.send(embed=_msg_erro(str(e)))
                return
            except ndb.ErroBanco as e:
                await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
                return

        embed = self._embed_resultado(novo, res)
        await interaction.followup.send(embed=embed)

    def _embed_resultado(self, e: dict, res: dict) -> discord.Embed:
        tipo = res["tipo"]
        ilha = res.get("ilha")
        prog = eng.formatar_prog(res["prog"]) if res["prog"] else None

        if tipo == "chegada":
            embed = discord.Embed(title=f"🏝️ Chegada em {ilha}",
                                  description=f"Teste de Navegação bem-sucedido! **+{prog} progressão**.", color=COR_TOTTO if e["no_totto"] else COR)
            if e["no_totto"] and e["prog_totto"] >= eng.PROGRESSOES_SAIR_TOTTO:
                embed.add_field(name="🍬 Totto Land", value="O bando já pode sair do arquipélago com `/totto_sair`.", inline=False)
            else:
                limite = eng._limite_principal(e["area"])
                if limite and e["prog_area"] >= limite:
                    embed.add_field(name="⭐ Ilha principal liberada", value="Ela já pode aparecer nas próximas sincronizações.", inline=False)
        elif tipo == "totto_entrada":
            embed = discord.Embed(
                title="🍬 O bando entrou em Totto Land",
                description=(f"Agora só ilhas do arquipélago são sincronizadas (CD normal, **+1 progressão** por ilha).\n"
                             f"Pra sair: **{eng.PROGRESSOES_SAIR_TOTTO} progressões** aqui dentro (`/totto_sair`).\n"
                             "Falhas na navegação aqui rolam um **Desastre** (`/encontromaritimo` → Totto Land)."),
                color=COR_TOTTO)
        elif tipo == "principal":
            embed = discord.Embed(title=f"⭐ {ilha} explorada!",
                                  description=f"A progressão resetou e a **Área {res['area']}** foi liberada pra sincronização.", color=0xE0A93B)
        elif tipo == "laugh_tale":
            embed = discord.Embed(title="🏴‍☠️ LAUGH TALE!",
                                  description="O bando chegou ao fim da Grand Line. O One Piece é de vocês!", color=0xE0A93B)
        elif tipo == "calm":
            embed = discord.Embed(
                title=f"🌀 Calm Belt — {ilha}",
                description=("A agulha **Instável** falhou e o bando foi parar no **Calm Belt**!"
                             + (f" (nível {res['nivel']})" if res.get("nivel") else "")), color=COR_ERRO)
        elif tipo == "secreta":
            embed = discord.Embed(
                title=f"🗝️ Ilha Secreta — {ilha}",
                description="Falha na navegação: o bando se perdeu e descobriu uma **Ilha Secreta**! (sem progressão)", color=0x7B3FBF)
        elif tipo == "falha_totto":
            embed = discord.Embed(
                title="🌪️ Falha em Totto Land",
                description="Dentro de Totto Land não existem Ilhas Secretas. Rolem um **Desastre** com `/encontromaritimo` (Totto Land).",
                color=COR_ERRO)
        elif tipo == "calm_vazio":
            embed = discord.Embed(description="A falha levaria ao Calm Belt, mas **não restam ilhas** novas lá. O bando segue onde está; use `/navegar`.", color=COR_ERRO)
        else:  # secreta_vazia
            embed = discord.Embed(description="Falha na navegação, mas **não restam Ilhas Secretas** nesta área. O bando segue onde está; use `/navegar`.", color=COR_ERRO)
        embed.set_footer(text=_rodape(e))
        return embed

    # ------------------------------------------------------------------
    @app_commands.command(name="totto_sair", description="Tira o bando de Totto Land (exige 5 progressões lá dentro).")
    @is_allowed_role()
    @app_commands.describe(bando="Nome do bando.")
    @app_commands.autocomplete(bando=bando_autocomplete)
    async def totto_sair(self, interaction: discord.Interaction, bando: str):
        await interaction.response.defer()
        async with _lock(bando):
            try:
                estado = await self._carregar(interaction, bando)
                if not estado:
                    return
                novo = eng.sair_totto(estado)
                await asyncio.to_thread(ndb.salvar_bando, novo)
                await asyncio.to_thread(ndb.registrar_log, novo["bando"], "saiu_totto", "")
            except eng.ErroRegra as e:
                await interaction.followup.send(embed=_msg_erro(str(e)))
                return
            except ndb.ErroBanco as e:
                await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
                return
        embed = discord.Embed(
            title="⛵ O bando deixou Totto Land",
            description=(f"As progressões feitas lá contam pro total da Área {novo['area']}.\n"
                         f"Totto Land ainda pode ser sincronizada, mas agora como uma ilha qualquer.\nUse `/navegar`."),
            color=COR)
        embed.set_footer(text=_rodape(novo))
        await interaction.followup.send(embed=embed)

    # ------------------------------------------------------------------
    @app_commands.command(name="navegacao_status", description="Mostra onde o bando está e o progresso dele.")
    @is_allowed_role()
    @app_commands.describe(bando="Nome do bando.")
    @app_commands.autocomplete(bando=bando_autocomplete)
    async def navegacao_status(self, interaction: discord.Interaction, bando: str):
        await interaction.response.defer(ephemeral=True)
        try:
            estado = await self._carregar(interaction, bando)
        except ndb.ErroBanco as e:
            await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
            return
        if estado:
            await interaction.followup.send(embed=_embed_status(estado), ephemeral=True)

    # ------------------------------------------------------------------
    @app_commands.command(name="navegacao_ajustar", description="Mestre: corrige área, progressão ou local de um bando.")
    @is_allowed_role()
    @app_commands.describe(
        bando="Nome do bando.", area="Nova área (1 a 4).", progressao="Nova progressão da área.",
        progressao_totto="Nova progressão dentro de Totto Land.", local="Nova localização (texto livre).",
        no_totto="Define se o bando está dentro de Totto Land.",
    )
    @app_commands.autocomplete(bando=bando_autocomplete)
    async def navegacao_ajustar(self, interaction: discord.Interaction, bando: str,
                                area: app_commands.Range[int, 1, 4] = None,
                                progressao: app_commands.Range[float, 0, 999] = None,
                                progressao_totto: app_commands.Range[float, 0, 999] = None,
                                local: str = None, no_totto: bool = None):
        await interaction.response.defer(ephemeral=True)
        if all(v is None for v in (area, progressao, progressao_totto, local, no_totto)):
            await interaction.followup.send(embed=_msg_erro("Informe pelo menos um valor pra ajustar."), ephemeral=True)
            return
        async with _lock(bando):
            try:
                estado = await self._carregar(interaction, bando)
                if not estado:
                    return
                mudancas = []
                if area is not None:
                    estado["area"] = area; mudancas.append(f"área={area}")
                if progressao is not None:
                    estado["prog_area"] = float(progressao); mudancas.append(f"progressão={progressao}")
                if progressao_totto is not None:
                    estado["prog_totto"] = float(progressao_totto); mudancas.append(f"prog. Totto={progressao_totto}")
                if local is not None:
                    estado["local"] = local; mudancas.append(f"local={local}")
                if no_totto is not None:
                    estado["no_totto"] = no_totto; mudancas.append(f"no_totto={no_totto}")
                estado["agulhas"] = []  # qualquer ajuste invalida o Log Pose atual
                estado["totto_apontado"] = False
                estado["totto_ressinc_em"] = None
                await asyncio.to_thread(ndb.salvar_bando, estado)
                await asyncio.to_thread(ndb.registrar_log, estado["bando"], "ajuste", ", ".join(mudancas))
            except ndb.ErroBanco as e:
                await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
                return
        await interaction.followup.send(content="✅ Ajustado (o Log Pose foi dessincronizado):", embed=_embed_status(estado), ephemeral=True)


    # ------------------------------------------------------------------
    @app_commands.command(name="navegacao_ilha_adicionar", description="Mestre: cadastra uma ilha no banco da navegação (ex: ilhas de Totto Land).")
    @is_allowed_role()
    @app_commands.describe(nome="Nome da ilha.", tipo="Tipo da ilha.", area="Área da ilha (Totto Land = 2).", nota="Observação (no Calm Belt: nível 1 ou 2).")
    @app_commands.choices(
        tipo=[app_commands.Choice(name=n, value=n) for n in ndb.TIPOS_ILHA],
        area=[app_commands.Choice(name=n, value=n) for n in ("1", "2", "3", "4", "calm")],
    )
    async def navegacao_ilha_adicionar(self, interaction: discord.Interaction, nome: str,
                                       tipo: app_commands.Choice[str], area: app_commands.Choice[str], nota: str = ""):
        await interaction.response.defer(ephemeral=True)
        try:
            ok = await asyncio.to_thread(ndb.adicionar_ilha, area.value, nome, tipo.value, nota)
        except ndb.ErroBanco as e:
            await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
            return
        if ok:
            await interaction.followup.send(f"✅ **{nome.strip()}** cadastrada (área {area.value}, tipo `{tipo.value}`).", ephemeral=True)
        else:
            await interaction.followup.send(embed=_msg_erro(f"Já existe uma ilha chamada **{nome.strip()}**."), ephemeral=True)

    @app_commands.command(name="navegacao_ilha_remover", description="Mestre: remove uma ilha do banco da navegação.")
    @is_allowed_role()
    @app_commands.describe(nome="Nome exato da ilha.")
    async def navegacao_ilha_remover(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer(ephemeral=True)
        try:
            ok = await asyncio.to_thread(ndb.remover_ilha, nome)
        except ndb.ErroBanco as e:
            await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
            return
        if ok:
            await interaction.followup.send(f"🗑️ **{nome.strip()}** removida.", ephemeral=True)
        else:
            await interaction.followup.send(embed=_msg_erro(f"Não achei a ilha **{nome.strip()}**."), ephemeral=True)

    @app_commands.command(name="navegacao_banco", description="Mestre: mostra qual banco a navegação está usando e se está conectado.")
    @is_allowed_role()
    async def navegacao_banco(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            ilhas = await asyncio.to_thread(ndb.listar_ilhas, True)
            bandos = await asyncio.to_thread(ndb.listar_nomes_bandos)
        except ndb.ErroBanco as e:
            await interaction.followup.send(embed=_msg_erro(f"[{ndb.nome_backend()}] {e}"), ephemeral=True)
            return
        await interaction.followup.send(
            f"✅ Banco: **{ndb.nome_backend()}**\n• {len(ilhas)} ilhas cadastradas\n• {len(bandos)} bandos",
            ephemeral=True)


async def setup(bot):
    await bot.add_cog(NavegacaoCog(bot))
