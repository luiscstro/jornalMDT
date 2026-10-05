import discord
from discord.ext import tasks, commands
from discord import app_commands
import datetime
import re
import database as db
import regioes_db as rdb
import regioes_engine as rengine
import cacadas_db as cdb
from cogs.permissoes import is_allowed_role

# --- CONFIGURAÇÕES ---
DIA_DA_SEMANA_UTC = 6  # domingo (0=segunda ... 6=domingo)
HORA_ATUALIZACAO_UTC = datetime.time(hour=15, minute=0, tzinfo=datetime.timezone.utc)
ID_CANAL_JORNAL = 1220562194232508426

# NOTA: as ilhas, o clima (com peso/porcentagem), os templates de rumor e as
# regiões (East Blue, South Blue, Paradise, etc) NÃO estão mais hardcoded
# aqui. Tudo isso agora é gerenciado dentro do Discord com /regioes
# (ver regioes_admin.py) e persistido em regioes.db (regioes_db.py).
# Para adicionar uma região nova (ex: "Novo Mundo") não é preciso mexer
# neste arquivo — basta usar o painel /regioes.


async def procurado_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    procurados = db.buscar_procurados(current)
    return [app_commands.Choice(name=nome, value=nome) for (nome,) in procurados]


async def mar_jornal_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    current = (current or "").lower()
    nomes = [r["nome"] for r in rdb.listar_regioes(apenas_ativas=True)]
    return [app_commands.Choice(name=n, value=n) for n in nomes if current in n.lower()][:25]


async def variavel_jornal_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    regiao = rdb.obter_regiao_por_nome(getattr(interaction.namespace, "mar", None) or "")
    if not regiao:
        return []
    current = (current or "").lower()
    variaveis = rengine.listar_variaveis_regiao(regiao["id"])
    return [app_commands.Choice(name=rotulo, value=chave) for rotulo, chave in variaveis if current in rotulo.lower()][:25]


def interpretar_mensagem_id(valor: str):
    """Aceita o ID da mensagem (procurada no canal do jornal) ou o link dela
    (que já traz o canal). Retorna (canal_id, mensagem_id) ou None."""
    valor = valor.strip()
    m = re.search(r"(\d+)/(\d+)/?$", valor)
    if m:
        return int(m.group(1)), int(m.group(2))
    if valor.isdigit():
        return ID_CANAL_JORNAL, int(valor)
    return None


class JornalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        rdb.init_db()
        cdb.init_db()
        self.postar_noticias_semanais.start()

    def cog_unload(self):
        self.postar_noticias_semanais.cancel()

    def gerar_boletins_completos(self, teste=False):
        """Gera o dicionário {nome_regiao: texto} a partir das regiões
        cadastradas dinamicamente (ativas), na ordem configurada.
        Retorna (boletins, procurados_usados)."""
        return rengine.gerar_todos_boletins(teste=teste)

    async def enviar_boletins(self, canal, teste=False):
        boletins, procurados_usados, estados = self.gerar_boletins_completos(teste=teste)

        async def enviar_com_imagem(texto):
            # O Discord exige um novo objeto File para cada mensagem enviada
            arquivo_imagem = discord.File("image-1.png", filename="image-1.png")
            return await canal.send(content=texto, file=arquivo_imagem)

        registros = []
        for nome_regiao, texto in boletins.items():
            mensagem = await enviar_com_imagem(texto)
            registros.append((nome_regiao, canal.id, mensagem.id, estados[nome_regiao]))

        if not teste:
            # Edição oficial: esses nomes ficam bloqueados pro /procurado
            # até a próxima edição oficial ser postada.
            cdb.definir_jornal_atual(procurados_usados)
            # Guarda os sorteios + id das mensagens pra /rerrolar_variavel
            # conseguir trocar só uma variável editando a mensagem postada.
            cdb.salvar_edicao_atual(registros)

    @tasks.loop(time=HORA_ATUALIZACAO_UTC)
    async def postar_noticias_semanais(self):
        if datetime.datetime.now(datetime.timezone.utc).weekday() != DIA_DA_SEMANA_UTC:
            return

        print(f"[{datetime.datetime.now()}] Segunda-feira! Postando os boletins informativos...")
        try:
            canal = self.bot.get_channel(ID_CANAL_JORNAL)
            if not canal:
                print(f"❌ ERRO: Canal com ID {ID_CANAL_JORNAL} não encontrado.")
                return
            await self.enviar_boletins(canal, teste=False)
            print("✅ Todas as edições do jornal foram publicadas!")
        except Exception as e:
            print(f"❌ ERRO ao tentar postar edições do jornal: {e}")

    @postar_noticias_semanais.before_loop
    async def before_postar_noticias(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="testar_noticia", description="Força o envio das edições de teste no canal atual.")
    @is_allowed_role()
    async def testar_noticia_slash(self, interaction: discord.Interaction):
        print("Forçando envio de notícias globais (teste)...")
        try:
            await interaction.response.send_message("✅ Gerando e enviando as edições de teste...", ephemeral=True)
            await self.enviar_boletins(interaction.channel, teste=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ERRO ao gerar edições de teste: {e}", ephemeral=True)

    @app_commands.command(name="rerrolar_jornal", description="Gera e posta uma nova edição OFICIAL do jornal no canal de notícias.")
    @is_allowed_role()
    async def rerrolar_jornal_slash(self, interaction: discord.Interaction):
        # O defer() é importante aqui porque enviar várias imagens grandes pode demorar uns segundos
        await interaction.response.defer(ephemeral=True)

        canal_oficial = self.bot.get_channel(ID_CANAL_JORNAL)
        if not canal_oficial:
            await interaction.followup.send(f"❌ ERRO: Não consegui encontrar o canal oficial (ID: {ID_CANAL_JORNAL}).")
            return

        try:
            # teste=False garante que não terá a tag [TESTE] no título
            await self.enviar_boletins(canal_oficial, teste=False)
            await interaction.followup.send(f"✅ Sucesso! O jornal oficial foi rerrolado e postado lá no <#{ID_CANAL_JORNAL}>.")
        except Exception as e:
            await interaction.followup.send(f"❌ ERRO ao tentar gerar o jornal oficial: {e}")

    async def _buscar_mensagem(self, canal_id: int, mensagem_id: int) -> discord.Message:
        canal = self.bot.get_channel(canal_id) or await self.bot.fetch_channel(canal_id)
        return await canal.fetch_message(mensagem_id)

    @app_commands.command(name="rerrolar_variavel", description="Rerrola UMA variável (clima, procurado, mestre, rota...) de uma região do jornal.")
    @is_allowed_role()
    @app_commands.describe(
        mar="Qual região/mar do jornal.",
        variavel="Qual variável rerrolar.",
        mensagem_id="ID ou link da mensagem a editar (vazio = última edição oficial salva).",
    )
    @app_commands.autocomplete(mar=mar_jornal_autocomplete, variavel=variavel_jornal_autocomplete)
    async def rerrolar_variavel_slash(self, interaction: discord.Interaction, mar: str, variavel: str, mensagem_id: str = None):
        await interaction.response.defer(ephemeral=True)

        regiao = rdb.obter_regiao_por_nome(mar)
        if not regiao:
            await interaction.followup.send(f"❌ A região **{mar}** não existe.")
            return

        try:
            if mensagem_id:
                alvo = interpretar_mensagem_id(mensagem_id)
                if not alvo:
                    await interaction.followup.send("❌ Não entendi esse ID. Passe o ID da mensagem ou o link dela.")
                    return
                canal_id, msg_id = alvo
                mensagem = await self._buscar_mensagem(canal_id, msg_id)
                if mensagem.author.id != self.bot.user.id:
                    await interaction.followup.send("❌ Essa mensagem não foi postada por mim, não consigo editá-la.")
                    return
                # Reconstrói o que foi sorteado a partir do texto da própria mensagem.
                nomes_conhecidos = [n for (n, _) in db.listar_procurados()] + cdb.obter_jornal_atual()
                estado = rengine.reconstruir_estado(regiao, mensagem.content, nomes_conhecidos)
            else:
                registro = cdb.obter_edicao_regiao(mar)
                if not registro:
                    await interaction.followup.send(
                        f"❌ Não há edição oficial salva para **{mar}**. Passe o `mensagem_id` da mensagem "
                        f"do jornal que você quer editar."
                    )
                    return
                canal_id, msg_id = registro["channel_id"], registro["message_id"]
                estado = registro["estado"]
                mensagem = await self._buscar_mensagem(canal_id, msg_id)
        except discord.NotFound:
            await interaction.followup.send("❌ Não encontrei essa mensagem (foi apagada ou o ID está errado).")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Não consegui buscar a mensagem: {e}")
            return
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}")
            return

        nome_antigo = rengine.nome_procurado(estado)
        pool = None
        if variavel == rengine.CHAVE_PROCURADO:
            # Fora quem já está na edição atual e o procurado que vai ser trocado.
            pool = [(n, t) for (n, t) in db.listar_procurados()
                    if not cdb.nome_no_jornal_atual(n) and n != nome_antigo]

        try:
            novo_estado, novas_linhas = rengine.rerrolar_variavel(estado, variavel, pool)
            await mensagem.edit(content=rengine.renderizar_estado(novo_estado))
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Não consegui editar a mensagem do jornal: {e}")
            return

        # Edições de teste não entram no rastreio da edição oficial.
        if "[TESTE]" not in novo_estado["cabecalho"]:
            cdb.salvar_edicao_regiao(mar, canal_id, msg_id, novo_estado)
            if variavel == rengine.CHAVE_PROCURADO:
                cdb.trocar_no_jornal_atual(nome_antigo, rengine.nome_procurado(novo_estado))

        await interaction.followup.send(
            f"✅ **{mar}** atualizado! ({mensagem.jump_url})\n" + "\n".join(novas_linhas)
        )

    @app_commands.command(name="cadastrar", description="Cadastra um novo procurado na planilha do Google.")
    @is_allowed_role()
    @app_commands.describe(nome="O nome completo.", tipo="O tipo (Pirata ou Marinheiro).")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Pirata", value="Pirata"),
        app_commands.Choice(name="Marinheiro", value="Marinheiro")
    ])
    async def cadastrar_procurado_slash(self, interaction: discord.Interaction, nome: str, tipo: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        if db.cadastrar_procurado(nome, tipo.value):
            await interaction.followup.send(f"✅ **{nome}** (Tipo: **{tipo.value}**) foi salvo na planilha!")
        else:
            await interaction.followup.send(f"❌ Erro! **{nome}** já existe na planilha.")

    @app_commands.command(name="remover", description="Remove um registro da planilha pelo nome exato.")
    @is_allowed_role()
    @app_commands.describe(nome="O nome exato a ser removido.")
    @app_commands.autocomplete(nome=procurado_autocomplete)
    async def remover_procurado_slash(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer(ephemeral=True)

        if db.remover_procurado(nome):
            await interaction.followup.send(f"🗑️ **{nome}** foi apagado da planilha.")
        else:
            await interaction.followup.send(f"❌ Erro! **{nome}** não foi encontrado.")

    @app_commands.command(name="editar", description="Edita nome/tipo de um registro na planilha.")
    @is_allowed_role()
    @app_commands.describe(
        nome_antigo="O nome atual na planilha.",
        nome_novo="O novo nome (deixe vazio para manter).",
        novo_tipo="O novo tipo (deixe vazio para manter)."
    )
    @app_commands.autocomplete(nome_antigo=procurado_autocomplete)
    @app_commands.choices(novo_tipo=[
        app_commands.Choice(name="Pirata", value="Pirata"),
        app_commands.Choice(name="Marinheiro", value="Marinheiro")
    ])
    async def editar_procurado_slash(self, interaction: discord.Interaction, nome_antigo: str, nome_novo: str = None, novo_tipo: app_commands.Choice[str] = None):
        if nome_novo is None and novo_tipo is None:
            await interaction.response.send_message("❌ Forneça pelo menos um novo nome ou tipo para atualizar.", ephemeral=True)
            return

        tipo_valor = novo_tipo.value if novo_tipo else None
        resultado = db.atualizar_procurado(nome_antigo, nome_novo=nome_novo, novo_tipo=tipo_valor)

        if resultado == "sucesso":
            msg = f"✅ Planilha atualizada para **{nome_antigo}**!"
            if nome_novo: msg += f"\n- Novo nome: **{nome_novo}**"
            if tipo_valor: msg += f"\n- Novo tipo: **{tipo_valor}**"
            await interaction.response.send_message(msg, ephemeral=True)
        elif resultado == "nao_encontrado":
            await interaction.response.send_message(f"❌ Erro! **{nome_antigo}** não consta na planilha.", ephemeral=True)
        elif resultado == "duplicado":
            await interaction.response.send_message(f"❌ Erro! O nome **{nome_novo}** já está alocado a outro registro.", ephemeral=True)

    @app_commands.command(name="lista_procurados", description="Puxa a lista completa de procurados da nuvem.")
    @is_allowed_role()
    async def lista_procurados_slash(self, interaction: discord.Interaction):
        lista = db.listar_procurados()
        if not lista:
            erro = db.obter_ultimo_erro_conexao()
            if erro:
                await interaction.response.send_message(f"❌ Não consegui conectar à planilha do Google: `{erro}`", ephemeral=True)
            else:
                await interaction.response.send_message("ℹ️ A planilha do Google está vazia.", ephemeral=True)
            return

        embed = discord.Embed(title="Lista Global de Procurados & Marinheiros", color=discord.Color.orange())
        texto_lista = "\n".join(f"• **{nome}** (Tipo: *{tipo}*)" for (nome, tipo) in lista)

        if len(texto_lista) > 4000:
            texto_lista = texto_lista[:4000] + "\n... (Muitos dados para exibir tudo aqui)"

        embed.description = texto_lista
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(JornalCog(bot))
