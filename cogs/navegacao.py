"""
navegacao.py
-------------
Navegação do Novo Mundo com Log Pose 3A (regras em navegacao_engine.py,
armazenamento em navegacao_db.py, animação em navegacao_visual.py).

Só dois comandos (cargos permitidos):
- /navegar  -> sincroniza o Log Pose; a mensagem sai com GIF animado e botões
               de Sucesso/Falha por agulha (persistentes, sem timeout).
- /navegacao -> painel (dashboard) dos staffs: bandos, ilhas visitadas, ajustes,
               sair de Totto Land, cadastro de ilhas.
"""

import asyncio
import datetime
import hashlib
import re
import traceback

import discord
from discord import app_commands
from discord.ext import commands

import navegacao_db as ndb
import navegacao_engine as eng
import navegacao_visual as visual
from navegacao_dados import INICIAIS
from cogs.permissoes import is_allowed_role, usuario_permitido

COR = 0x2F8FBF
COR_TOTTO = 0xE0609B
COR_ERRO = 0xB3261E
NOME_GIF = "logpose.gif"

_locks: dict = {}


def _lock(bando: str) -> asyncio.Lock:
    return _locks.setdefault(bando.strip().lower(), asyncio.Lock())


async def _bd(func, *args):
    return await asyncio.to_thread(func, *args)


def _hash_bando(nome: str) -> str:
    """ID curto e estável do bando, cabe no custom_id dos botões persistentes."""
    return hashlib.sha1(nome.strip().lower().encode("utf-8")).hexdigest()[:10]


def _msg_erro(texto: str) -> discord.Embed:
    return discord.Embed(description=f"❌ {texto}", color=COR_ERRO)


async def _responder_erro(interaction: discord.Interaction, texto: str):
    if interaction.response.is_done():
        await interaction.followup.send(embed=_msg_erro(texto), ephemeral=True)
    else:
        await interaction.response.send_message(embed=_msg_erro(texto), ephemeral=True)


async def bando_autocomplete(interaction: discord.Interaction, current: str):
    try:
        nomes = await _bd(ndb.listar_nomes_bandos)
    except Exception:
        return []
    current = (current or "").lower()
    return [app_commands.Choice(name=n, value=n) for n in nomes if current in n.lower()][:25]


# ===========================================================================
# Textos e embeds
# ===========================================================================

def _quando(e: dict) -> str:
    if not e.get("totto_ressinc_em"):
        return ""
    ts = int(datetime.datetime.fromisoformat(e["totto_ressinc_em"]).timestamp())
    return f"a partir de <t:{ts}:F> (<t:{ts}:R>)"


def _rodape(e: dict) -> str:
    limite = eng._limite_principal(e["area"])
    base = f"{e['bando']} · Área {e['area']} · {eng.formatar_prog(e['prog_area'])}/{limite or '—'} progressões"
    if e["no_totto"]:
        base += f" · Totto Land {eng.formatar_prog(e['prog_totto'])}/{eng.PROGRESSOES_SAIR_TOTTO}"
    return base


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
    marca = " ⭐ **(ilha principal)**" if ag["principal"] else ""
    return f"{info['emoji']} **Agulha {n} · {info['rotulo']}** → **{ag['ilha']}**{marca}\n   ↳ {extra}"


def _embed_agulhas(e: dict, com_gif: bool) -> discord.Embed:
    if e["totto_apontado"]:
        embed = discord.Embed(
            title="🍬 O Log Pose enlouqueceu: todas as agulhas apontam pra Totto Land!",
            description="\n".join(_linha_agulha(i + 1, a, False) for i, a in enumerate(e["agulhas"][:1])),
            color=COR_TOTTO,
        )
        embed.add_field(
            name="O que o bando faz?",
            value="• **Ir pra lá:** faça o Teste de Navegação e use os botões abaixo.\n"
                  f"• **Esperar** e tentar de novo: `/navegar` {_quando(e)}.",
            inline=False,
        )
    else:
        embed = discord.Embed(
            title="🧭 Log Pose 3A sincronizado",
            description=f"O bando está em **{e['local']}**.\n\n"
                        + "\n".join(_linha_agulha(i + 1, a, e["no_totto"]) for i, a in enumerate(e["agulhas"])),
            color=COR_TOTTO if e["no_totto"] else COR,
        )
        embed.add_field(
            name="Próximo passo",
            value="Façam o **Teste de Navegação** e o mestre aperta o botão da agulha seguida: ✅ sucesso ou ❌ falha.",
            inline=False,
        )
    if com_gif:
        embed.set_image(url=f"attachment://{NOME_GIF}")
    embed.set_footer(text=_rodape(e))
    return embed


def _embed_resultado(e: dict, res: dict) -> discord.Embed:
    tipo = res["tipo"]
    ilha = res.get("ilha")
    prog = eng.formatar_prog(res["prog"]) if res["prog"] else None

    if tipo == "chegada":
        embed = discord.Embed(title=f"🏝️ Chegada em {ilha}",
                              description=f"Teste de Navegação bem-sucedido! **+{prog} progressão**.",
                              color=COR_TOTTO if e["no_totto"] else COR)
        if e["no_totto"] and e["prog_totto"] >= eng.PROGRESSOES_SAIR_TOTTO:
            embed.add_field(name="🍬 Totto Land", value="O bando já pode sair do arquipélago (painel `/navegacao`).", inline=False)
        else:
            limite = eng._limite_principal(e["area"])
            if limite and e["prog_area"] >= limite:
                embed.add_field(name="⭐ Ilha principal liberada", value="Ela já pode aparecer nas próximas sincronizações.", inline=False)
    elif tipo == "totto_entrada":
        embed = discord.Embed(
            title="🍬 O bando entrou em Totto Land",
            description=(f"Agora só ilhas do arquipélago são sincronizadas (CD normal, **+1 progressão** por ilha).\n"
                         f"Pra sair: **{eng.PROGRESSOES_SAIR_TOTTO} progressões** aqui dentro (painel `/navegacao`).\n"
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
        embed.add_field(name="Totto Land",
                        value=f"**{eng.formatar_prog(e['prog_totto'])}** / {eng.PROGRESSOES_SAIR_TOTTO} pra poder sair", inline=True)
    embed.add_field(
        name="Explorado",
        value=f"{len(e['visitadas'])} ilhas · {len(e['secretas'])} secretas · {len(e['calm'])} no Calm Belt",
        inline=False,
    )
    if e["agulhas"]:
        embed.add_field(name="Log Pose atual",
                        value="\n".join(_linha_agulha(i + 1, a, e["no_totto"]) for i, a in enumerate(e["agulhas"])), inline=False)
    else:
        embed.add_field(name="Log Pose atual", value="Não sincronizado. Use **🧭 Navegar** ou `/navegar`.", inline=False)
    if e["fim"]:
        embed.add_field(name="🏴‍☠️", value="O bando chegou em **Laugh Tale**!", inline=False)
    return embed


def _pedacos(nomes: list, limite: int = 1000) -> list:
    """Junta nomes em blocos de texto que cabem num field de embed."""
    blocos, atual = [], ""
    for n in nomes:
        item = ("" if not atual else " • ") + n
        if len(atual) + len(item) > limite:
            blocos.append(atual)
            atual = n
        else:
            atual += item
    if atual:
        blocos.append(atual)
    return blocos or ["—"]


def _embed_visitadas(e: dict, ilhas: list) -> discord.Embed:
    embed = discord.Embed(title=f"🏝️ Ilhas visitadas — {e['bando']}",
                          description="Na ordem da viagem. O número é visitadas/total cadastradas.", color=COR)
    for rotulo, nomes, total in eng.resumo_visitadas(e, ilhas):
        for n, bloco in enumerate(_pedacos(nomes)):
            titulo = f"{rotulo} · {len(nomes)}/{total}" if n == 0 else f"{rotulo} (cont.)"
            embed.add_field(name=titulo, value=bloco, inline=False)
    embed.set_footer(text=_rodape(e))
    return embed


def _embed_ilhas(ilhas: list) -> discord.Embed:
    embed = discord.Embed(
        title="🏝️ Ilhas cadastradas",
        description=f"Banco: **{ndb.nome_backend()}** · {len(ilhas)} ilhas",
        color=COR,
    )
    linhas = []
    for area in (1, 2, 3, 4, "calm"):
        do_grupo = [i for i in ilhas if i["area"] == area]
        if not do_grupo:
            continue
        cont = {}
        for i in do_grupo:
            cont[i["tipo"]] = cont.get(i["tipo"], 0) + 1
        rotulo = "Calm Belt" if area == "calm" else f"Área {area}"
        linhas.append(f"**{rotulo}:** " + ", ".join(f"{q} {t}" for t, q in cont.items()))
    embed.add_field(name="Resumo", value="\n".join(linhas) or "Nenhuma ilha cadastrada.", inline=False)
    if not any(i["tipo"] == "totto_ilha" for i in ilhas):
        embed.add_field(name="⚠️ Totto Land sem ilhas",
                        value="Cadastre as ilhas internas com **➕ Adicionar** (área `2`, tipo `totto_ilha`).", inline=False)
    return embed


# ===========================================================================
# Sincronizar + botões persistentes
# ===========================================================================

class BotaoViagem(discord.ui.DynamicItem[discord.ui.Button],
                  template=r"nm:(?P<ag>[1-3]):(?P<res>[sf]):(?P<h>[0-9a-f]{10}):(?P<sync>\d+)"):
    """Botão Sucesso/Falha de uma agulha. Persistente: o estado vive no custom_id
    (agulha, resultado, bando e nº da sincronização) e o banco, então sobrevive a
    reinícios do bot e nunca expira."""

    def __init__(self, agulha: int, sucesso: bool, h: str, sync: int, row: int = 0, totto: bool = False):
        if totto:
            label = "Sucesso (ir pra Totto)" if sucesso else "Falha"
        else:
            label = f"Agulha {agulha} · {'Sucesso' if sucesso else 'Falha'}"
        super().__init__(discord.ui.Button(
            label=label,
            style=discord.ButtonStyle.success if sucesso else discord.ButtonStyle.danger,
            emoji="✅" if sucesso else "❌",
            custom_id=f"nm:{agulha}:{'s' if sucesso else 'f'}:{h}:{sync}",
            row=row,
        ))
        self.agulha, self.sucesso, self.h, self.sync = agulha, sucesso, h, sync

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match, /):
        return cls(int(match["ag"]), match["res"] == "s", match["h"], int(match["sync"]))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not usuario_permitido(interaction):
            await interaction.response.send_message("❌ Só a staff pode usar esses botões.", ephemeral=True)
            return False
        return True

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            nomes = await _bd(ndb.listar_nomes_bandos)
            nome = next((n for n in nomes if _hash_bando(n) == self.h), None)
            if not nome:
                await _responder_erro(interaction, "Não achei esse bando (foi apagado?).")
                return
            async with _lock(nome):
                estado = await _bd(ndb.obter_bando, nome)
                if not estado:
                    await _responder_erro(interaction, "Não achei esse bando (foi apagado?).")
                    return
                if estado.get("sync_id", 0) != self.sync or not estado["agulhas"]:
                    await _responder_erro(interaction, "Essa sincronização já foi resolvida ou foi substituída por outra. Use `/navegar`.")
                    await self._desativar(interaction, "⚠️ Sincronização encerrada.")
                    return
                ilhas = await _bd(ndb.listar_ilhas)
                novo, res = eng.viajar(estado, ilhas, self.agulha, self.sucesso)
                await _bd(ndb.salvar_bando, novo)
                await _bd(ndb.registrar_log, novo["bando"], f"viajou:{res['tipo']}", res.get("ilha") or "")
        except eng.ErroRegra as e:
            await _responder_erro(interaction, str(e))
            return
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))
            return

        resultado = "Sucesso" if self.sucesso else "Falha"
        await self._desativar(interaction, f"{'✅' if self.sucesso else '❌'} Agulha {self.agulha} · {resultado} — por {interaction.user.display_name}")
        await interaction.followup.send(embed=_embed_resultado(novo, res))

    async def _desativar(self, interaction: discord.Interaction, rodape: str):
        """Tira os botões da mensagem (já foi resolvida) e registra o que aconteceu."""
        try:
            embeds = interaction.message.embeds
            if embeds:
                embed = embeds[0]
                embed.set_footer(text=rodape)
                await interaction.message.edit(embed=embed, view=None)
            else:
                await interaction.message.edit(view=None)
        except discord.HTTPException as e:
            print(f"⚠️ Não consegui atualizar a mensagem da sincronização: {e}")


def _view_sync(e: dict) -> discord.ui.View:
    h, sync = _hash_bando(e["bando"]), e.get("sync_id", 0)
    view = discord.ui.View(timeout=None)
    if e["totto_apontado"]:
        view.add_item(BotaoViagem(1, True, h, sync, row=0, totto=True))
        view.add_item(BotaoViagem(1, False, h, sync, row=0, totto=True))
        return view
    for n in range(1, len(e["agulhas"]) + 1):
        view.add_item(BotaoViagem(n, True, h, sync, row=0))
    for n in range(1, len(e["agulhas"]) + 1):
        view.add_item(BotaoViagem(n, False, h, sync, row=1))
    return view


async def _montar_msg_sync(e: dict) -> dict:
    """kwargs prontos pro send: embed + GIF animado (se der) + botões persistentes."""
    gif = await asyncio.to_thread(visual.gerar_gif_logpose, [a["tipo"] for a in e["agulhas"]], e["totto_apontado"], e.get("sync_id"))
    kwargs = {"embed": _embed_agulhas(e, gif is not None), "view": _view_sync(e)}
    if gif is not None:
        kwargs["file"] = discord.File(gif, filename=NOME_GIF)
    return kwargs


async def _sincronizar(bando: str, forcar: bool):
    """Sincroniza e salva. Retorna o novo estado (levanta ErroRegra/ErroBanco)."""
    async with _lock(bando):
        estado = await _bd(ndb.obter_bando, bando)
        if not estado:
            raise eng.ErroRegra(f"O bando **{bando}** não existe. Crie pelo painel `/navegacao`.")
        ilhas = await _bd(ndb.listar_ilhas)
        novo = eng.sincronizar(estado, ilhas, forcar=forcar)
        await _bd(ndb.salvar_bando, novo)
        resumo = " | ".join(f"{a['tipo']}:{a['ilha']}" for a in novo["agulhas"])
        await _bd(ndb.registrar_log, novo["bando"], "sincronizou", resumo)
        return novo


# ===========================================================================
# Painel (dashboard)
# ===========================================================================

class PainelBase(discord.ui.View):
    def __init__(self, timeout: float = 900):
        super().__init__(timeout=timeout)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not usuario_permitido(interaction):
            await interaction.response.send_message("❌ Você não tem permissão para usar este painel.", ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)
        try:
            await _responder_erro(interaction, "Algo deu errado nesse botão. Tente `🔄 Atualizar`.")
        except discord.HTTPException:
            pass


async def _mostrar_menu(interaction: discord.Interaction):
    """Mostra o menu (a interação já foi respondida com defer)."""
    nomes = await _bd(ndb.listar_nomes_bandos)
    embed = discord.Embed(
        title="🧭 Painel da Navegação — Novo Mundo",
        description="Escolha um bando pra ver o progresso, as ilhas visitadas e fazer ajustes.\n"
                    "Pra sincronizar o Log Pose, use **🧭 Navegar** dentro do bando ou `/navegar`.",
        color=COR,
    )
    embed.add_field(name=f"Bandos ({len(nomes)})", value=", ".join(nomes[:25]) or "Nenhum ainda. Clique em ➕ **Novo bando**.", inline=False)
    embed.set_footer(text=f"Banco: {ndb.nome_backend()}")
    await interaction.edit_original_response(embed=embed, content=None, attachments=[], view=MenuView(nomes))


async def _mostrar_bando(interaction: discord.Interaction, nome: str):
    estado = await _bd(ndb.obter_bando, nome)
    if not estado:
        await _mostrar_menu(interaction)
        await interaction.followup.send(embed=_msg_erro(f"O bando **{nome}** não existe mais."), ephemeral=True)
        return
    await interaction.edit_original_response(embed=_embed_status(estado), view=BandoView(estado))


async def _mostrar_ilhas(interaction: discord.Interaction):
    ilhas = await _bd(ndb.listar_ilhas, True)
    await interaction.edit_original_response(embed=_embed_ilhas(ilhas), view=IlhasView())


class SelectBando(discord.ui.Select):
    def __init__(self, nomes: list):
        opcoes = [discord.SelectOption(label=n[:100], value=n[:100]) for n in nomes[:25]]
        super().__init__(
            placeholder="📂 Escolher bando..." if opcoes else "Nenhum bando ainda",
            options=opcoes or [discord.SelectOption(label="Nenhum bando", value="none")],
            disabled=not opcoes, row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            await _mostrar_bando(interaction, self.values[0])
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))


class MenuView(PainelBase):
    def __init__(self, nomes: list):
        super().__init__()
        self.add_item(SelectBando(nomes))

    @discord.ui.button(label="Novo bando", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def novo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NovoBandoModal())

    @discord.ui.button(label="Ilhas", style=discord.ButtonStyle.primary, emoji="🏝️", row=1)
    async def ilhas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await _mostrar_ilhas(interaction)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))

    @discord.ui.button(label="Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def atualizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await _mostrar_menu(interaction)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))


class BandoView(PainelBase):
    def __init__(self, estado: dict):
        super().__init__()
        self.nome = estado["bando"]
        self.sair_totto.disabled = not estado["no_totto"]
        self.navegar.disabled = bool(estado["fim"])

    @discord.ui.button(label="Navegar", style=discord.ButtonStyle.primary, emoji="🧭", row=0)
    async def navegar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            novo = await _sincronizar(self.nome, forcar=False)
            kwargs = await _montar_msg_sync(novo)
            await interaction.channel.send(**kwargs)  # mensagem pública, com GIF e botões
            await interaction.edit_original_response(embed=_embed_status(novo), view=BandoView(novo))
            await interaction.followup.send("🧭 Log Pose sincronizado e postado no canal.", ephemeral=True)
        except (eng.ErroRegra, ndb.ErroBanco) as e:
            await _responder_erro(interaction, str(e))
        except discord.HTTPException as e:
            await _responder_erro(interaction, f"Não consegui postar no canal: {e}")

    @discord.ui.button(label="Ilhas visitadas", style=discord.ButtonStyle.secondary, emoji="🏝️", row=0)
    async def visitadas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            estado = await _bd(ndb.obter_bando, self.nome)
            ilhas = await _bd(ndb.listar_ilhas)
            if not estado:
                await _mostrar_menu(interaction)
                return
            await interaction.edit_original_response(embed=_embed_visitadas(estado, ilhas), view=VoltarBandoView(self.nome))
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))

    @discord.ui.button(label="Sair de Totto", style=discord.ButtonStyle.secondary, emoji="🍬", row=0)
    async def sair_totto(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            async with _lock(self.nome):
                estado = await _bd(ndb.obter_bando, self.nome)
                novo = eng.sair_totto(estado)
                await _bd(ndb.salvar_bando, novo)
                await _bd(ndb.registrar_log, novo["bando"], "saiu_totto", "")
            await _mostrar_bando(interaction, self.nome)
            await interaction.followup.send(f"⛵ **{self.nome}** deixou Totto Land. Totto agora é uma ilha comum; use **🧭 Navegar**.", ephemeral=True)
        except (eng.ErroRegra, ndb.ErroBanco) as e:
            await _responder_erro(interaction, str(e))

    @discord.ui.button(label="Ajustar", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def ajustar(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            estado = await _bd(ndb.obter_bando, self.nome)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))
            return
        if not estado:
            await _responder_erro(interaction, "Esse bando não existe mais.")
            return
        await interaction.response.send_modal(AjustarModal(estado))

    @discord.ui.button(label="Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def atualizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await _mostrar_bando(interaction, self.nome)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await _mostrar_menu(interaction)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))


class VoltarBandoView(PainelBase):
    def __init__(self, nome: str):
        super().__init__()
        self.nome = nome

    @discord.ui.button(label="Voltar ao bando", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await _mostrar_bando(interaction, self.nome)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))


class IlhasView(PainelBase):
    @discord.ui.button(label="Adicionar", style=discord.ButtonStyle.success, emoji="➕")
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(IlhaAdicionarModal())

    @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="➖")
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(IlhaRemoverModal())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await _mostrar_menu(interaction)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))


# ---------------------------------------------------------------------------
# Modais
# ---------------------------------------------------------------------------

class NovoBandoModal(discord.ui.Modal, title="Novo bando"):
    nome = discord.ui.TextInput(label="Nome do bando", max_length=50)
    ilha = discord.ui.TextInput(label="Ilha de partida", placeholder="Raijin, Risky Red ou Mystoria", max_length=30)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        nome = self.nome.value.strip()
        ilha = next((i for i in INICIAIS if i.lower() == self.ilha.value.strip().lower()), None)
        if not ilha:
            await _responder_erro(interaction, f"Ilha inicial inválida. Use: {', '.join(INICIAIS)}.")
            return
        try:
            async with _lock(nome):
                if await _bd(ndb.obter_bando, nome):
                    await _responder_erro(interaction, f"Já existe um bando chamado **{nome}**.")
                    return
                await _bd(ndb.salvar_bando, eng.novo_estado(nome, ilha))
                await _bd(ndb.registrar_log, nome, "inicio", ilha)
            await _mostrar_bando(interaction, nome)
            await interaction.followup.send(f"⛵ **{nome}** pronto pra zarpar de **{ilha}**. Explorem a ilha e use **🧭 Navegar**.", ephemeral=True)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))


class AjustarModal(discord.ui.Modal, title="Ajustar bando"):
    def __init__(self, estado: dict):
        super().__init__()
        self.nome = estado["bando"]
        self.area = discord.ui.TextInput(label="Área (1 a 4)", default=str(estado["area"]), max_length=1, required=False)
        self.prog = discord.ui.TextInput(label="Progressão da área", default=eng.formatar_prog(estado["prog_area"]), max_length=6, required=False)
        self.prog_totto = discord.ui.TextInput(label="Progressão em Totto Land", default=eng.formatar_prog(estado["prog_totto"]), max_length=6, required=False)
        self.local = discord.ui.TextInput(label="Local atual", default=estado["local"][:100], max_length=100, required=False)
        self.no_totto = discord.ui.TextInput(label="Está em Totto Land? (sim/não)", default="sim" if estado["no_totto"] else "não", max_length=3, required=False)
        for campo in (self.area, self.prog, self.prog_totto, self.local, self.no_totto):
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            area = int(self.area.value) if self.area.value.strip() else None
            prog = float((self.prog.value or "").replace(",", ".")) if self.prog.value.strip() else None
            prog_t = float((self.prog_totto.value or "").replace(",", ".")) if self.prog_totto.value.strip() else None
        except ValueError:
            await _responder_erro(interaction, "Área e progressões precisam ser números.")
            return
        if area is not None and not 1 <= area <= 4:
            await _responder_erro(interaction, "A área vai de 1 a 4.")
            return
        resp = self.no_totto.value.strip().lower()
        if resp and resp not in ("sim", "não", "nao", "s", "n"):
            await _responder_erro(interaction, "Em Totto Land: responda sim ou não.")
            return
        try:
            async with _lock(self.nome):
                estado = await _bd(ndb.obter_bando, self.nome)
                if not estado:
                    await _mostrar_menu(interaction)
                    return
                mudancas = []
                if area is not None and area != estado["area"]:
                    estado["area"] = area; mudancas.append(f"área={area}")
                if prog is not None and prog != estado["prog_area"]:
                    estado["prog_area"] = prog; mudancas.append(f"progressão={prog}")
                if prog_t is not None and prog_t != estado["prog_totto"]:
                    estado["prog_totto"] = prog_t; mudancas.append(f"prog. Totto={prog_t}")
                if self.local.value.strip() and self.local.value.strip() != estado["local"]:
                    estado["local"] = self.local.value.strip(); mudancas.append(f"local={estado['local']}")
                if resp:
                    novo_totto = resp in ("sim", "s")
                    if novo_totto != estado["no_totto"]:
                        estado["no_totto"] = novo_totto; mudancas.append(f"no_totto={novo_totto}")
                if mudancas:
                    estado["agulhas"] = []  # qualquer ajuste invalida o Log Pose atual
                    estado["totto_apontado"] = False
                    estado["totto_ressinc_em"] = None
                    estado["sync_id"] = estado.get("sync_id", 0) + 1
                    await _bd(ndb.salvar_bando, estado)
                    await _bd(ndb.registrar_log, estado["bando"], "ajuste", ", ".join(mudancas))
            await _mostrar_bando(interaction, self.nome)
            await interaction.followup.send(
                ("✅ Ajustado (o Log Pose foi dessincronizado): " + ", ".join(mudancas)) if mudancas else "Nada mudou.", ephemeral=True)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))


class IlhaAdicionarModal(discord.ui.Modal, title="Adicionar ilha"):
    nome = discord.ui.TextInput(label="Nome da ilha", max_length=80)
    tipo = discord.ui.TextInput(label="Tipo", placeholder=", ".join(ndb.TIPOS_ILHA)[:100], max_length=20)
    area = discord.ui.TextInput(label="Área", placeholder="1, 2, 3, 4 ou calm (Totto Land = 2)", max_length=4)
    nota = discord.ui.TextInput(label="Nota (opcional)", required=False, max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        tipo = self.tipo.value.strip().lower()
        area = self.area.value.strip().lower()
        if tipo not in ndb.TIPOS_ILHA:
            await _responder_erro(interaction, f"Tipo inválido. Use: {', '.join(ndb.TIPOS_ILHA)}.")
            return
        if area not in ("1", "2", "3", "4", "calm"):
            await _responder_erro(interaction, "Área inválida. Use 1, 2, 3, 4 ou calm.")
            return
        try:
            ok = await _bd(ndb.adicionar_ilha, area, self.nome.value, tipo, self.nota.value)
            await _mostrar_ilhas(interaction)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))
            return
        await interaction.followup.send(
            f"✅ **{self.nome.value.strip()}** cadastrada (área {area}, tipo `{tipo}`)." if ok
            else f"❌ Já existe uma ilha chamada **{self.nome.value.strip()}**.", ephemeral=True)


class IlhaRemoverModal(discord.ui.Modal, title="Remover ilha"):
    nome = discord.ui.TextInput(label="Nome exato da ilha", max_length=80)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            ok = await _bd(ndb.remover_ilha, self.nome.value)
            await _mostrar_ilhas(interaction)
        except ndb.ErroBanco as e:
            await _responder_erro(interaction, str(e))
            return
        await interaction.followup.send(
            f"🗑️ **{self.nome.value.strip()}** removida." if ok else f"❌ Não achei a ilha **{self.nome.value.strip()}**.", ephemeral=True)


# ===========================================================================
# Cog
# ===========================================================================

class NavegacaoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Botões de sincronizações já postadas voltam a funcionar após reiniciar o bot.
        bot.add_dynamic_items(BotaoViagem)

    def cog_unload(self):
        self.bot.remove_dynamic_items(BotaoViagem)

    @app_commands.command(name="navegar", description="Sincroniza o Log Pose 3A do bando (com animação e botões de sucesso/falha).")
    @is_allowed_role()
    @app_commands.describe(bando="Nome do bando.", forcar="Ignora a espera de 1 semana de Totto Land (uso do mestre).")
    @app_commands.autocomplete(bando=bando_autocomplete)
    async def navegar(self, interaction: discord.Interaction, bando: str, forcar: bool = False):
        await interaction.response.defer()
        try:
            novo = await _sincronizar(bando, forcar)
            kwargs = await _montar_msg_sync(novo)
        except eng.ErroRegra as e:
            await interaction.followup.send(embed=_msg_erro(str(e)))
            return
        except ndb.ErroBanco as e:
            await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
            return
        await interaction.followup.send(**kwargs)

    @app_commands.command(name="navegacao", description="Painel da navegação do Novo Mundo (bandos, ilhas visitadas, ajustes, ilhas).")
    @is_allowed_role()
    async def navegacao(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            nomes = await _bd(ndb.listar_nomes_bandos)
        except ndb.ErroBanco as e:
            await interaction.followup.send(embed=_msg_erro(str(e)), ephemeral=True)
            return
        embed = discord.Embed(
            title="🧭 Painel da Navegação — Novo Mundo",
            description="Escolha um bando pra ver o progresso, as ilhas visitadas e fazer ajustes.\n"
                        "Pra sincronizar o Log Pose, use **🧭 Navegar** dentro do bando ou `/navegar`.",
            color=COR,
        )
        embed.add_field(name=f"Bandos ({len(nomes)})", value=", ".join(nomes[:25]) or "Nenhum ainda. Clique em ➕ **Novo bando**.", inline=False)
        embed.set_footer(text=f"Banco: {ndb.nome_backend()}")
        await interaction.followup.send(embed=embed, view=MenuView(nomes), ephemeral=True)


async def setup(bot):
    await bot.add_cog(NavegacaoCog(bot))
