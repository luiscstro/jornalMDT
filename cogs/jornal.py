import discord
from discord.ext import tasks, commands
from discord import app_commands
import datetime
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
        boletins, procurados_usados = self.gerar_boletins_completos(teste=teste)

        async def enviar_com_imagem(texto):
            # O Discord exige um novo objeto File para cada mensagem enviada
            arquivo_imagem = discord.File("image-1.png", filename="image-1.png")
            await canal.send(content=texto, file=arquivo_imagem)

        for texto in boletins.values():
            await enviar_com_imagem(texto)

        if not teste:
            # Edição oficial: esses nomes ficam bloqueados pro /procurado
            # até a próxima edição oficial ser postada.
            cdb.definir_jornal_atual(procurados_usados)

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
