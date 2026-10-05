"""
regioes_admin.py
------------------
UI 100% dentro do Discord (botões, selects e modais) para criar, editar e
remover Regiões do jornal e tudo que elas contêm: locais, categorias de
clima com peso/porcentagem e grupos de template com variações com peso.

Comando: /regioes

Nada aqui exige editar código para adicionar uma região nova (ex: "Novo
Mundo") — é tudo feito pela própria UI.
"""

import discord
from discord import app_commands
from discord.ext import commands

import regioes_db as rdb
import regioes_engine as rengine
from cogs.permissoes import is_allowed_role, usuario_permitido

EMOJI_ON = "✅"
EMOJI_OFF = "⬛"


# ---------------------------------------------------------------------------
# Base: view que só aceita interação de quem tem cargo permitido
# ---------------------------------------------------------------------------

class PainelBaseView(discord.ui.View):
    def __init__(self, timeout=600):
        super().__init__(timeout=timeout)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not usuario_permitido(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este painel.", ephemeral=True
            )
            return False
        return True


def _pct_txt(itens, chave_peso="peso"):
    itens = rdb.calcular_porcentagens(list(itens), chave_peso)
    return itens


# ---------------------------------------------------------------------------
# MENU PRINCIPAL
# ---------------------------------------------------------------------------

class MenuPrincipalView(PainelBaseView):
    def __init__(self):
        super().__init__()
        self.add_item(SelectRegiao())

    @discord.ui.button(label="Nova Região", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def nova_regiao(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NovaRegiaoModal())

    @discord.ui.button(label="Atualizar Lista", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def atualizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_embed_menu_principal(), view=MenuPrincipalView())


def build_embed_menu_principal() -> discord.Embed:
    regioes = rdb.listar_regioes()
    embed = discord.Embed(
        title="🗺️ Gerenciador de Regiões do Jornal",
        description="Escolha uma região abaixo para editar, ou crie uma nova.\n"
                    "Toda região criada aqui é gerada automaticamente nas próximas edições do jornal.",
        color=discord.Color.blurple(),
    )
    if not regioes:
        embed.add_field(name="Nenhuma região cadastrada", value="Clique em ➕ Nova Região para começar.", inline=False)
    else:
        linhas = []
        for r in regioes:
            status = "🟢" if r["ativa"] else "🔴"
            linhas.append(f"{status} **{r['nome']}** — {len(rdb.listar_locais(r['id']))} locais")
        embed.add_field(name=f"Regiões ({len(regioes)})", value="\n".join(linhas), inline=False)
    return embed


class SelectRegiao(discord.ui.Select):
    def __init__(self):
        regioes = rdb.listar_regioes()
        options = [
            discord.SelectOption(
                label=r["nome"][:100],
                value=str(r["id"]),
                description=f"{'Ativa' if r['ativa'] else 'Inativa'} · {r['rotulo_local']}",
            )
            for r in regioes[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="Nenhuma região ainda", value="none")]
        super().__init__(placeholder="📂 Selecionar região para editar...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Crie uma região primeiro.", ephemeral=True)
            return
        regiao_id = int(self.values[0])
        view = PainelRegiaoView(regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class NovaRegiaoModal(discord.ui.Modal, title="Nova Região"):
    nome = discord.ui.TextInput(label="Nome da região", placeholder="Ex: Novo Mundo", max_length=100)
    rotulo_local = discord.ui.TextInput(
        label="Como chamar os locais? (ilha, rota...)", placeholder="ilha", default="ilha", max_length=30
    )
    mencoes_texto = discord.ui.TextInput(
        label="Menções no rodapé (opcional)", required=False,
        placeholder="||<@&ID_DO_CARGO>||", style=discord.TextStyle.paragraph, max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        nome_val = self.nome.value.strip()
        if rdb.nome_regiao_existe(nome_val):
            await interaction.response.send_message(f"❌ Já existe uma região chamada **{nome_val}**.", ephemeral=True)
            return
        ordem = len(rdb.listar_regioes())
        regiao_id = rdb.criar_regiao(
            nome=nome_val,
            rotulo_local=self.rotulo_local.value.strip() or "ilha",
            tem_clima=True,
            tem_procurado=True,
            locais_unicos_por_grupo=False,
            mencoes_texto=self.mencoes_texto.value.strip(),
            ordem=ordem,
        )
        view = PainelRegiaoView(regiao_id)
        embed = await view.build_embed()
        embed.set_footer(text="Região criada! Adicione locais, clima e templates abaixo.")
        await interaction.response.edit_message(embed=embed, view=view)


# ---------------------------------------------------------------------------
# PAINEL DE UMA REGIÃO
# ---------------------------------------------------------------------------

class PainelRegiaoView(PainelBaseView):
    def __init__(self, regiao_id: int):
        super().__init__()
        self.regiao_id = regiao_id

    async def build_embed(self) -> discord.Embed:
        r = rdb.obter_regiao(self.regiao_id)
        locais = rdb.listar_locais(self.regiao_id)
        grupos = rdb.listar_grupos_template(self.regiao_id)
        categorias_clima = rdb.listar_categorias_clima(self.regiao_id)

        embed = discord.Embed(title=f"🗺️ Região: {r['nome']}", color=discord.Color.gold())
        embed.add_field(name="Rótulo de local", value=r["rotulo_local"], inline=True)
        embed.add_field(name="Status", value="🟢 Ativa" if r["ativa"] else "🔴 Inativa", inline=True)
        embed.add_field(name="Ordem", value=str(r["ordem"]), inline=True)
        embed.add_field(name="📍 Locais", value=str(len(locais)) or "0", inline=True)
        embed.add_field(name="📝 Grupos de template", value=str(len(grupos)), inline=True)
        embed.add_field(name="🌦️ Categorias de clima", value=str(len(categorias_clima)), inline=True)
        embed.add_field(
            name="Interruptores",
            value=(
                f"{EMOJI_ON if r['tem_clima'] else EMOJI_OFF} Clima\n"
                f"{EMOJI_ON if r['tem_procurado'] else EMOJI_OFF} Procurado (planilha)\n"
                f"{EMOJI_ON if r['locais_unicos_por_grupo'] else EMOJI_OFF} Locais únicos por linha\n"
                f"{EMOJI_ON if r['ativa'] else EMOJI_OFF} Ativa no jornal"
            ),
            inline=False,
        )
        embed.add_field(name="Menções no rodapé", value=r["mencoes_texto"] or "*(nenhuma)*", inline=False)
        return embed

    # --- linha 0: navegação de conteúdo ---
    @discord.ui.button(label="Locais", style=discord.ButtonStyle.primary, emoji="📍", row=0)
    async def locais(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LocaisView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)

    @discord.ui.button(label="Templates", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = TemplatesView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)

    @discord.ui.button(label="Clima", style=discord.ButtonStyle.primary, emoji="🌦️", row=0)
    async def clima(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ClimaView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)

    # --- linha 1: edição de textos ---
    @discord.ui.button(label="Info Geral", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def info_geral(self, interaction: discord.Interaction, button: discord.ui.Button):
        r = rdb.obter_regiao(self.regiao_id)
        await interaction.response.send_modal(InfoGeralModal(self.regiao_id, r))

    @discord.ui.button(label="Textos de Cabeçalho", style=discord.ButtonStyle.secondary, emoji="🎨", row=1)
    async def cabecalho(self, interaction: discord.Interaction, button: discord.ui.Button):
        r = rdb.obter_regiao(self.regiao_id)
        await interaction.response.send_modal(CabecalhoModal(self.regiao_id, r))

    @discord.ui.button(label="Textos de Procurado", style=discord.ButtonStyle.secondary, emoji="🎯", row=1)
    async def procurado_textos(self, interaction: discord.Interaction, button: discord.ui.Button):
        r = rdb.obter_regiao(self.regiao_id)
        await interaction.response.send_modal(ProcuradoTextosModal(self.regiao_id, r))

    # --- linha 2: toggles rápidos ---
    @discord.ui.button(label="Alternar Clima", style=discord.ButtonStyle.secondary, emoji="🌦️", row=2)
    async def toggle_clima(self, interaction: discord.Interaction, button: discord.ui.Button):
        r = rdb.obter_regiao(self.regiao_id)
        rdb.editar_regiao(self.regiao_id, tem_clima=int(not r["tem_clima"]))
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="Alternar Procurado", style=discord.ButtonStyle.secondary, emoji="🎯", row=2)
    async def toggle_procurado(self, interaction: discord.Interaction, button: discord.ui.Button):
        r = rdb.obter_regiao(self.regiao_id)
        rdb.editar_regiao(self.regiao_id, tem_procurado=int(not r["tem_procurado"]))
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="Alternar Ativa", style=discord.ButtonStyle.secondary, emoji="🔌", row=2)
    async def toggle_ativa(self, interaction: discord.Interaction, button: discord.ui.Button):
        r = rdb.obter_regiao(self.regiao_id)
        rdb.editar_regiao(self.regiao_id, ativa=int(not r["ativa"]))
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    # --- linha 3: preview / excluir / voltar ---
    @discord.ui.button(label="Pré-visualizar", style=discord.ButtonStyle.success, emoji="👁️", row=3)
    async def preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer IMEDIATAMENTE: buscar dados (ex: planilha do Google) pode
        # passar de 3s e a interação expira (erro "Unknown interaction").
        await interaction.response.defer(ephemeral=True, thinking=True)
        r = rdb.obter_regiao(self.regiao_id)
        pool = []
        try:
            import database as db
            pool = db.listar_procurados()
        except Exception:
            pool = []
        texto, _ = rengine.gerar_boletim_regiao(r, pool, teste=True)
        if len(texto) > 1900:
            texto = texto[:1900] + "\n... (cortado na pré-visualização)"
        await interaction.followup.send(f"**Pré-visualização de {r['nome']}:**\n\n{texto}", ephemeral=True)

    @discord.ui.button(label="Excluir Região", style=discord.ButtonStyle.danger, emoji="🗑️", row=3)
    async def excluir(self, interaction: discord.Interaction, button: discord.ui.Button):
        r = rdb.obter_regiao(self.regiao_id)
        view = ConfirmarExclusaoView(
            texto_confirmacao=f"Excluir a região **{r['nome']}** e tudo dentro dela (locais, clima, templates)?",
            on_confirmar=lambda i: self._confirmar_exclusao(i),
        )
        await interaction.response.edit_message(content=None, embed=None, view=view)

    async def _confirmar_exclusao(self, interaction: discord.Interaction):
        rdb.excluir_regiao(self.regiao_id)
        await interaction.response.edit_message(
            content="🗑️ Região excluída.", embed=build_embed_menu_principal(), view=MenuPrincipalView()
        )

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=3)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_embed_menu_principal(), view=MenuPrincipalView())


class ConfirmarExclusaoView(PainelBaseView):
    def __init__(self, texto_confirmacao: str, on_confirmar):
        super().__init__(timeout=60)
        self.texto_confirmacao = texto_confirmacao
        self.on_confirmar = on_confirmar

    @discord.ui.button(label="Sim, excluir", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.on_confirmar(interaction)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_embed_menu_principal(), view=MenuPrincipalView())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        ok = await super().interaction_check(interaction)
        return ok


class InfoGeralModal(discord.ui.Modal, title="Editar Info Geral"):
    def __init__(self, regiao_id, regiao):
        super().__init__()
        self.regiao_id = regiao_id
        self.nome = discord.ui.TextInput(label="Nome", default=regiao["nome"], max_length=100)
        self.rotulo_local = discord.ui.TextInput(label="Rótulo de local (ilha/rota)", default=regiao["rotulo_local"], max_length=30)
        self.ordem = discord.ui.TextInput(label="Ordem (número)", default=str(regiao["ordem"]), max_length=5)
        self.mencoes_texto = discord.ui.TextInput(
            label="Menções no rodapé", required=False, default=regiao["mencoes_texto"],
            style=discord.TextStyle.paragraph, max_length=300,
        )
        for item in (self.nome, self.rotulo_local, self.ordem, self.mencoes_texto):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        novo_nome = self.nome.value.strip()
        if rdb.nome_regiao_existe(novo_nome, ignorar_id=self.regiao_id):
            await interaction.response.send_message(f"❌ Já existe outra região chamada **{novo_nome}**.", ephemeral=True)
            return
        try:
            ordem_val = int(self.ordem.value.strip())
        except ValueError:
            ordem_val = 0
        rdb.editar_regiao(
            self.regiao_id,
            nome=novo_nome,
            rotulo_local=self.rotulo_local.value.strip() or "ilha",
            ordem=ordem_val,
            mencoes_texto=self.mencoes_texto.value.strip(),
        )
        view = PainelRegiaoView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class CabecalhoModal(discord.ui.Modal, title="Textos de Cabeçalho"):
    def __init__(self, regiao_id, regiao):
        super().__init__()
        self.regiao_id = regiao_id
        self.cabecalho = discord.ui.TextInput(
            label="Cabeçalho ({teste} {regiao})", default=regiao["cabecalho_template"],
            style=discord.TextStyle.paragraph, max_length=300,
        )
        self.introducao = discord.ui.TextInput(
            label="Introdução ({regiao})", default=regiao["introducao_template"], max_length=200,
        )
        self.clima_titulo = discord.ui.TextInput(
            label="Título do clima ({regiao})", default=regiao["clima_titulo_template"], max_length=200,
        )
        for item in (self.cabecalho, self.introducao, self.clima_titulo):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        rdb.editar_regiao(
            self.regiao_id,
            cabecalho_template=self.cabecalho.value,
            introducao_template=self.introducao.value,
            clima_titulo_template=self.clima_titulo.value,
        )
        view = PainelRegiaoView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class ProcuradoTextosModal(discord.ui.Modal, title="Textos de Procurado/Marinheiro"):
    def __init__(self, regiao_id, regiao):
        super().__init__()
        self.regiao_id = regiao_id
        self.pirata = discord.ui.TextInput(
            label="Texto Pirata ({local} {nome} {nome_upper})", default=regiao["procurado_pirata_texto"],
            style=discord.TextStyle.paragraph, max_length=400,
        )
        self.marinheiro = discord.ui.TextInput(
            label="Texto Marinheiro ({local} {nome})", default=regiao["procurado_marinheiro_texto"],
            style=discord.TextStyle.paragraph, max_length=400,
        )
        self.vazio = discord.ui.TextInput(
            label="Texto quando não há ninguém", default=regiao["procurado_vazio_texto"],
            style=discord.TextStyle.paragraph, max_length=300,
        )
        for item in (self.pirata, self.marinheiro, self.vazio):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        rdb.editar_regiao(
            self.regiao_id,
            procurado_pirata_texto=self.pirata.value,
            procurado_marinheiro_texto=self.marinheiro.value,
            procurado_vazio_texto=self.vazio.value,
        )
        view = PainelRegiaoView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


# ---------------------------------------------------------------------------
# LOCAIS
# ---------------------------------------------------------------------------

class LocaisView(PainelBaseView):
    def __init__(self, regiao_id: int):
        super().__init__()
        self.regiao_id = regiao_id
        locais = rdb.listar_locais(regiao_id)
        if locais:
            self.add_item(SelectRemoverLocal(regiao_id, locais))

    async def build_embed(self) -> discord.Embed:
        r = rdb.obter_regiao(self.regiao_id)
        locais = rdb.listar_locais(self.regiao_id)
        embed = discord.Embed(title=f"📍 Locais de {r['nome']}", color=discord.Color.green())
        if locais:
            nomes = ", ".join(l["nome"] for l in locais)
            if len(nomes) > 1000:
                nomes = nomes[:1000] + "..."
            embed.description = nomes
        else:
            embed.description = "*Nenhum local cadastrado ainda.*"
        embed.set_footer(text=f"{len(locais)} locais · use o botão abaixo para adicionar (aceita vários separados por vírgula)")
        return embed

    @discord.ui.button(label="Adicionar Local(is)", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdicionarLocalModal(self.regiao_id))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PainelRegiaoView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class SelectRemoverLocal(discord.ui.Select):
    def __init__(self, regiao_id, locais):
        self.regiao_id = regiao_id
        options = [discord.SelectOption(label=l["nome"][:100], value=str(l["id"])) for l in locais[:25]]
        super().__init__(placeholder="🗑️ Selecionar local(is) para remover...", options=options,
                          min_values=1, max_values=len(options), row=0)

    async def callback(self, interaction: discord.Interaction):
        for local_id in self.values:
            rdb.remover_local(int(local_id))
        view = LocaisView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class AdicionarLocalModal(discord.ui.Modal, title="Adicionar Local(is)"):
    nomes = discord.ui.TextInput(
        label="Nome(s), separados por vírgula", style=discord.TextStyle.paragraph,
        placeholder="Ilha A, Ilha B, Ilha C", max_length=1000,
    )

    def __init__(self, regiao_id):
        super().__init__()
        self.regiao_id = regiao_id

    async def on_submit(self, interaction: discord.Interaction):
        nomes_lista = [n.strip() for n in self.nomes.value.split(",") if n.strip()]
        if nomes_lista:
            rdb.adicionar_locais(self.regiao_id, nomes_lista)
        view = LocaisView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


# ---------------------------------------------------------------------------
# TEMPLATES (grupos + variações com peso)
# ---------------------------------------------------------------------------

class TemplatesView(PainelBaseView):
    def __init__(self, regiao_id: int):
        super().__init__()
        self.regiao_id = regiao_id
        grupos = rdb.listar_grupos_template(regiao_id)
        if grupos:
            self.add_item(SelectGrupoTemplate(regiao_id, grupos))

    async def build_embed(self) -> discord.Embed:
        r = rdb.obter_regiao(self.regiao_id)
        grupos = rdb.listar_grupos_template(self.regiao_id)
        embed = discord.Embed(
            title=f"📝 Grupos de Template — {r['nome']}",
            description="Cada grupo gera **uma linha** no boletim, sorteando uma variação com base no peso.\n"
                        "Use `{local}` no texto da variação para inserir um local sorteado.",
            color=discord.Color.purple(),
        )
        if grupos:
            for g in grupos:
                n_var = len(rdb.listar_variacoes(g["id"]))
                embed.add_field(
                    name=f"#{g['ordem']} — {g['nome']}",
                    value=f"{n_var} variação(ões) · usa local: {EMOJI_ON if g['usa_local'] else EMOJI_OFF}",
                    inline=False,
                )
        else:
            embed.add_field(name="Nenhum grupo ainda", value="Crie um grupo para começar (ex: Rumor, Mestre...).", inline=False)
        return embed

    @discord.ui.button(label="Novo Grupo", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def novo_grupo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NovoGrupoModal(self.regiao_id))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PainelRegiaoView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class SelectGrupoTemplate(discord.ui.Select):
    def __init__(self, regiao_id, grupos):
        self.regiao_id = regiao_id
        options = [
            discord.SelectOption(label=f"#{g['ordem']} {g['nome']}"[:100], value=str(g["id"]))
            for g in grupos[:25]
        ]
        super().__init__(placeholder="✏️ Selecionar grupo para editar...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        grupo_id = int(self.values[0])
        view = GrupoDetailView(self.regiao_id, grupo_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class NovoGrupoModal(discord.ui.Modal, title="Novo Grupo de Template"):
    nome = discord.ui.TextInput(label="Nome do grupo", placeholder="Ex: Rumor de Tesouro", max_length=100)
    ordem = discord.ui.TextInput(label="Ordem (número)", default="0", max_length=5)
    usa_local = discord.ui.TextInput(label="Usa {local}? (sim/nao)", default="sim", max_length=5)

    def __init__(self, regiao_id):
        super().__init__()
        self.regiao_id = regiao_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            ordem_val = int(self.ordem.value.strip())
        except ValueError:
            ordem_val = 0
        usa_local_val = self.usa_local.value.strip().lower() in ("sim", "s", "yes", "y", "true", "1")
        rdb.criar_grupo_template(self.regiao_id, self.nome.value.strip(), ordem=ordem_val, usa_local=usa_local_val)
        view = TemplatesView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class GrupoDetailView(PainelBaseView):
    def __init__(self, regiao_id: int, grupo_id: int):
        super().__init__()
        self.regiao_id = regiao_id
        self.grupo_id = grupo_id
        variacoes = rdb.listar_variacoes(grupo_id)
        if variacoes:
            self.add_item(SelectVariacao(regiao_id, grupo_id, variacoes))

    async def build_embed(self) -> discord.Embed:
        grupo = None
        for g in rdb.listar_grupos_template(self.regiao_id):
            if g["id"] == self.grupo_id:
                grupo = g
                break
        variacoes = _pct_txt(rdb.listar_variacoes(self.grupo_id))
        embed = discord.Embed(
            title=f"📝 Grupo: {grupo['nome'] if grupo else '?'}",
            description="Cada variação tem um **peso** — quanto maior, mais chance de ser sorteada.\n"
                        "A porcentagem mostrada é relativa ao total do grupo.",
            color=discord.Color.purple(),
        )
        if variacoes:
            for v in variacoes:
                texto = v["texto"] if len(v["texto"]) <= 200 else v["texto"][:200] + "..."
                embed.add_field(name=f"peso {v['peso']} (≈{v['porcentagem']}%)", value=texto, inline=False)
        else:
            embed.add_field(name="Nenhuma variação ainda", value="Adicione pelo menos uma.", inline=False)
        return embed

    @discord.ui.button(label="Adicionar Variação", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VariacaoModal(self.regiao_id, self.grupo_id))

    @discord.ui.button(label="Excluir Grupo", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def excluir_grupo(self, interaction: discord.Interaction, button: discord.ui.Button):
        rdb.excluir_grupo_template(self.grupo_id)
        view = TemplatesView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = TemplatesView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class SelectVariacao(discord.ui.Select):
    def __init__(self, regiao_id, grupo_id, variacoes):
        self.regiao_id = regiao_id
        self.grupo_id = grupo_id
        options = [
            discord.SelectOption(label=(v["texto"][:95] + "...") if len(v["texto"]) > 95 else v["texto"], value=str(v["id"]))
            for v in variacoes[:25]
        ]
        super().__init__(placeholder="✏️ Selecionar variação para editar/remover...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        variacao_id = int(self.values[0])
        view = EditarOuRemoverVariacaoView(self.regiao_id, self.grupo_id, variacao_id)
        await interaction.response.edit_message(content=None, embed=await view.build_embed(), view=view)


class EditarOuRemoverVariacaoView(PainelBaseView):
    def __init__(self, regiao_id, grupo_id, variacao_id):
        super().__init__()
        self.regiao_id = regiao_id
        self.grupo_id = grupo_id
        self.variacao_id = variacao_id

    async def build_embed(self):
        variacoes = rdb.listar_variacoes(self.grupo_id)
        v = next((x for x in variacoes if x["id"] == self.variacao_id), None)
        embed = discord.Embed(title="Editar Variação", color=discord.Color.purple())
        embed.add_field(name="Texto atual", value=v["texto"] if v else "?", inline=False)
        embed.add_field(name="Peso atual", value=str(v["peso"]) if v else "?", inline=False)
        return embed

    @discord.ui.button(label="Editar", style=discord.ButtonStyle.primary, emoji="✏️")
    async def editar(self, interaction: discord.Interaction, button: discord.ui.Button):
        variacoes = rdb.listar_variacoes(self.grupo_id)
        v = next((x for x in variacoes if x["id"] == self.variacao_id), None)
        await interaction.response.send_modal(VariacaoModal(self.regiao_id, self.grupo_id, variacao_existente=v))

    @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        rdb.remover_variacao(self.variacao_id)
        view = GrupoDetailView(self.regiao_id, self.grupo_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = GrupoDetailView(self.regiao_id, self.grupo_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class VariacaoModal(discord.ui.Modal, title="Variação de Template"):
    def __init__(self, regiao_id, grupo_id, variacao_existente=None):
        super().__init__()
        self.regiao_id = regiao_id
        self.grupo_id = grupo_id
        self.variacao_existente = variacao_existente
        self.texto = discord.ui.TextInput(
            label="Texto (use {local} se aplicável)", style=discord.TextStyle.paragraph,
            default=variacao_existente["texto"] if variacao_existente else "",
            placeholder="Boatos sobre ruínas inexploradas em **{local}**.", max_length=500,
        )
        self.peso = discord.ui.TextInput(
            label="Peso (número, quanto maior mais comum)",
            default=str(variacao_existente["peso"]) if variacao_existente else "1", max_length=5,
        )
        self.add_item(self.texto)
        self.add_item(self.peso)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            peso_val = max(1, int(self.peso.value.strip()))
        except ValueError:
            peso_val = 1
        if self.variacao_existente:
            rdb.editar_variacao(self.variacao_existente["id"], texto=self.texto.value, peso=peso_val)
        else:
            rdb.adicionar_variacao(self.grupo_id, self.texto.value, peso=peso_val)
        view = GrupoDetailView(self.regiao_id, self.grupo_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


# ---------------------------------------------------------------------------
# CLIMA (categorias + opções com peso)
# ---------------------------------------------------------------------------

class ClimaView(PainelBaseView):
    def __init__(self, regiao_id: int):
        super().__init__()
        self.regiao_id = regiao_id
        categorias = rdb.listar_categorias_clima(regiao_id)
        if categorias:
            self.add_item(SelectCategoriaClima(regiao_id, categorias))

    async def build_embed(self) -> discord.Embed:
        r = rdb.obter_regiao(self.regiao_id)
        categorias = rdb.listar_categorias_clima(self.regiao_id)
        embed = discord.Embed(
            title=f"🌦️ Clima — {r['nome']}",
            description="Cada categoria (ex: temperatura, vento) sorteia uma opção com base no peso.",
            color=discord.Color.blue(),
        )
        if categorias:
            for c in categorias:
                n_op = len(rdb.listar_opcoes_clima(c["id"]))
                embed.add_field(name=f"#{c['ordem']} — {c['nome']}", value=f"{n_op} opção(ões)", inline=False)
        else:
            embed.add_field(name="Nenhuma categoria ainda", value="Crie uma (ex: temperatura, vento, precipitação).", inline=False)
        return embed

    @discord.ui.button(label="Nova Categoria", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def nova_categoria(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NovaCategoriaClimaModal(self.regiao_id))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PainelRegiaoView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class SelectCategoriaClima(discord.ui.Select):
    def __init__(self, regiao_id, categorias):
        self.regiao_id = regiao_id
        options = [
            discord.SelectOption(label=f"#{c['ordem']} {c['nome']}"[:100], value=str(c["id"]))
            for c in categorias[:25]
        ]
        super().__init__(placeholder="✏️ Selecionar categoria para editar...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        categoria_id = int(self.values[0])
        view = CategoriaClimaDetailView(self.regiao_id, categoria_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class NovaCategoriaClimaModal(discord.ui.Modal, title="Nova Categoria de Clima"):
    nome = discord.ui.TextInput(label="Nome", placeholder="Ex: temperatura", max_length=50)
    ordem = discord.ui.TextInput(label="Ordem (número)", default="0", max_length=5)
    frase = discord.ui.TextInput(
        label="Frase ({categoria} {opcao})", style=discord.TextStyle.paragraph,
        default="- A {categoria} hoje está... **{opcao}**.", max_length=300,
    )

    def __init__(self, regiao_id):
        super().__init__()
        self.regiao_id = regiao_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            ordem_val = int(self.ordem.value.strip())
        except ValueError:
            ordem_val = 0
        rdb.criar_categoria_clima(self.regiao_id, self.nome.value.strip(), ordem=ordem_val, frase=self.frase.value)
        view = ClimaView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class CategoriaClimaDetailView(PainelBaseView):
    def __init__(self, regiao_id: int, categoria_id: int):
        super().__init__()
        self.regiao_id = regiao_id
        self.categoria_id = categoria_id
        opcoes = rdb.listar_opcoes_clima(categoria_id)
        if opcoes:
            self.add_item(SelectOpcaoClima(regiao_id, categoria_id, opcoes))

    async def build_embed(self) -> discord.Embed:
        categoria = None
        for c in rdb.listar_categorias_clima(self.regiao_id):
            if c["id"] == self.categoria_id:
                categoria = c
                break
        opcoes = _pct_txt(rdb.listar_opcoes_clima(self.categoria_id))
        embed = discord.Embed(
            title=f"🌦️ Categoria: {categoria['nome'] if categoria else '?'}",
            description=f"Frase usada: `{categoria['frase']}`" if categoria else "",
            color=discord.Color.blue(),
        )
        if opcoes:
            for o in opcoes:
                embed.add_field(name=o["opcao"], value=f"peso {o['peso']} (≈{o['porcentagem']}%)", inline=True)
        else:
            embed.add_field(name="Nenhuma opção ainda", value="Adicione pelo menos uma (ex: Amena, Frio, Calor).", inline=False)
        return embed

    @discord.ui.button(label="Adicionar Opção", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OpcaoClimaModal(self.regiao_id, self.categoria_id))

    @discord.ui.button(label="Excluir Categoria", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def excluir(self, interaction: discord.Interaction, button: discord.ui.Button):
        rdb.excluir_categoria_clima(self.categoria_id)
        view = ClimaView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ClimaView(self.regiao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class SelectOpcaoClima(discord.ui.Select):
    def __init__(self, regiao_id, categoria_id, opcoes):
        self.regiao_id = regiao_id
        self.categoria_id = categoria_id
        options = [discord.SelectOption(label=o["opcao"][:100], value=str(o["id"])) for o in opcoes[:25]]
        super().__init__(placeholder="✏️ Selecionar opção para editar/remover...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        opcao_id = int(self.values[0])
        view = EditarOuRemoverOpcaoView(self.regiao_id, self.categoria_id, opcao_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class EditarOuRemoverOpcaoView(PainelBaseView):
    def __init__(self, regiao_id, categoria_id, opcao_id):
        super().__init__()
        self.regiao_id = regiao_id
        self.categoria_id = categoria_id
        self.opcao_id = opcao_id

    async def build_embed(self):
        opcoes = rdb.listar_opcoes_clima(self.categoria_id)
        o = next((x for x in opcoes if x["id"] == self.opcao_id), None)
        embed = discord.Embed(title="Editar Opção de Clima", color=discord.Color.blue())
        embed.add_field(name="Opção atual", value=o["opcao"] if o else "?", inline=True)
        embed.add_field(name="Peso atual", value=str(o["peso"]) if o else "?", inline=True)
        return embed

    @discord.ui.button(label="Editar", style=discord.ButtonStyle.primary, emoji="✏️")
    async def editar(self, interaction: discord.Interaction, button: discord.ui.Button):
        opcoes = rdb.listar_opcoes_clima(self.categoria_id)
        o = next((x for x in opcoes if x["id"] == self.opcao_id), None)
        await interaction.response.send_modal(OpcaoClimaModal(self.regiao_id, self.categoria_id, opcao_existente=o))

    @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        rdb.remover_opcao_clima(self.opcao_id)
        view = CategoriaClimaDetailView(self.regiao_id, self.categoria_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CategoriaClimaDetailView(self.regiao_id, self.categoria_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


class OpcaoClimaModal(discord.ui.Modal, title="Opção de Clima"):
    def __init__(self, regiao_id, categoria_id, opcao_existente=None):
        super().__init__()
        self.regiao_id = regiao_id
        self.categoria_id = categoria_id
        self.opcao_existente = opcao_existente
        self.opcao = discord.ui.TextInput(
            label="Nome da opção", default=opcao_existente["opcao"] if opcao_existente else "",
            placeholder="Ex: Calor", max_length=100,
        )
        self.peso = discord.ui.TextInput(
            label="Peso (número, quanto maior mais comum)",
            default=str(opcao_existente["peso"]) if opcao_existente else "1", max_length=5,
        )
        self.add_item(self.opcao)
        self.add_item(self.peso)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            peso_val = max(1, int(self.peso.value.strip()))
        except ValueError:
            peso_val = 1
        if self.opcao_existente:
            rdb.editar_opcao_clima(self.opcao_existente["id"], opcao=self.opcao.value.strip(), peso=peso_val)
        else:
            rdb.adicionar_opcao_clima(self.categoria_id, self.opcao.value.strip(), peso=peso_val)
        view = CategoriaClimaDetailView(self.regiao_id, self.categoria_id)
        await interaction.response.edit_message(embed=await view.build_embed(), view=view)


# ---------------------------------------------------------------------------
# COG
# ---------------------------------------------------------------------------

class RegioesAdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        rdb.init_db()

    @app_commands.command(name="regioes", description="Abre o painel de gerenciamento de regiões do jornal.")
    @is_allowed_role()
    async def regioes_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=build_embed_menu_principal(), view=MenuPrincipalView(), ephemeral=True)


async def setup(bot):
    await bot.add_cog(RegioesAdminCog(bot))