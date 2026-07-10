import discord
from discord.ext import tasks, commands
from discord import app_commands
import datetime
import random
import database as db

# --- CONFIGURAÇÕES ---
DIA_DA_SEMANA_UTC = 0
HORA_ATUALIZACAO_UTC = datetime.time(hour=15, minute=0, tzinfo=datetime.timezone.utc)
ID_CANAL_JORNAL = 1220562194232508426 
ID_ROLE_1 = "1221255954708959324"
ID_ROLE_2 = "1283492761039011851"
ID_ROLE_3 = "1220345032079572995"
TEXTO_MENCOES = f"||<@&{ID_ROLE_1}> <@&{ID_ROLE_2}> <@&{ID_ROLE_3}> ||"

CARGOS_PERMITIDOS_IDs = {
    1405643389105606767,  # Dev's
    1227977596671885393,  # Supervisores
    1222232432527413389,  # Moderadores
    1475504976037154959   # P3rcy  
}

# --- BANCO DE DADOS METEOROLÓGICO ---
CLIMA_OPCOES = {
    "temperatura": [("Amena", 7), ("Frio", 2), ("Calor", 2)],
    "vento": [("Fraco", 7), ("Nenhum", 2), ("Forte", 2)],
    "precipitacao": [("Nenhuma", 7), ("Chuva ou Nevasca Fraca", 2), ("Chuva ou Nevasca intensa", 1)]
}

# --- LISTAS DE ILHAS POR REGIÃO ---
ILHAS_MARITIMAS = {
    "East Blue": [
        "Oykot Kingdom", "Polestar Island", "Cozia Island", "Mirrorball",
        "Conomi Island", "Grand Serenity", "Baratie", "Gecko Island",
        "Island of Rare Animals", "Organ Islands", "Crescent Isle",
        "Tequila Wolf", "Goat Island", "Shimotsuki", "Sixis Island", "Down Island"
    ],
    "South Blue": [
        "Baterilla", "Behemoth Island", "Black Drum Kingdom", "Briar Island",
        "Briss Kingdom", "Centaurea", "Clockwork Island", "Deadman's Key",
        "Fort Justice", "Karate Island", "Kyuka Island", "Mokora",
        "Reino Torino", "Ryujin Island", "Sorbet Kingdom", "South Pole"
    ],
    "North Blue": [
        "Blackpine Kingdom", "Deul Kingdom", "Downs Island", "Flevance Kingdom",
        "Frostharbor Island", "Germa Kingdom", "Kuen Island", "Lvneel Kingdom",
        "Minion Island", "North Pole", "Notice Island", "Rakesh",
        "Red Line", "Rubeck Island", "Spider Miles", "Swallow Island", "Whiteland Kingdom"
    ],
    "West Blue": [
        "80th Branch", "Arlen Island", "Ballywood Kingdom", "Blackreef Island",
        "East Blue", "Ferrônia", "Fogreach", "Ilisia Kingdom", "Isla Fortuna",
        "Kano Kuni", "Las Camp", "North Blue", "Ohara", "Red Line",
        "Saint Aurelia", "Soja Island", "South Blue", "Stormhaven",
        "Toroa Island", "Vespera Island"
    ]
}

RANKS_OPCOES = ["Amador:Infame", "Amador: Desconhecido", "Amador: Famoso"]

RUMOR_TEMPLATES = [
    "Boatos sobre ruínas inexploradas em **{ilha}**.",
    "Dizem que um tesouro antigo está enterrado em **{ilha}**.",
    "Um mapa misterioso aponta para um tesouro escondido em **{ilha}**."
]

PARADISE_ROTAS = ["Vermelha", "Laranja", "Azul", "Verde", "Amarela", "Rosa", "Branca"]
PARADISE_TEMPLATES = {
    "tesouro": ["Ouvimos muitos boatos de piratas sortudos encontrando tesouros recheados na **rota {rota}**! (Caçador de Tesouros)"],
    "procurado": ["Há rumores de um possível encontro de figurões piratas na **rota {rota}**! (procurado garantido)"]
}

# --- AUXILIARES ---
def is_allowed_role():
    def predicate(interaction: discord.Interaction) -> bool:
        user_role_ids = {role.id for role in interaction.user.roles}
        return bool(user_role_ids.intersection(CARGOS_PERMITIDOS_IDs))
    return app_commands.check(predicate)

async def procurado_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    procurados = db.buscar_procurados(current)
    return [app_commands.Choice(name=nome, value=nome) for (nome,) in procurados]

def sortear_item_com_peso(lista_de_opcoes_com_peso):
    descricoes, pesos = zip(*lista_de_opcoes_com_peso)
    return random.choices(descricoes, weights=pesos, k=1)[0]


class JornalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.postar_noticias_semanais.start()

    def cog_unload(self):
        self.postar_noticias_semanais.cancel()

    def gerar_boletins_completos(self, teste=False):
        """
        Sorteia e constrói as 5 mensagens independentes.
        Garante que um procurado sorteado em um mar não apareça em nenhum outro.
        """
        pool_procurados = db.listar_procurados()
        random.shuffle(pool_procurados)
        
        mensagens = {}
        titulo_teste = "[TESTE] " if teste else ""

        # --- GERAÇÃO DOS 4 BLUES ---
        for mar, ilhas in ILHAS_MARITIMAS.items():
            ilha_rumor = random.choice(ilhas)
            rumor_final = random.choice(RUMOR_TEMPLATES).format(ilha=ilha_rumor)

            ilha_mestre = random.choice(ilhas)
            mestre_final = f"Procurando um mestre? Em **{ilha_mestre}**, temos um **professor** querendo ensinar piratas dispostos a aprender."

            ilha_nakama = random.choice(ilhas)
            rank_nakama = random.choice(RANKS_OPCOES)
            nakama_final = f"Não quer um mestre? Que tal um nakama provisório pro seu barco? Temos um **{rank_nakama}** em **{ilha_nakama}**!"

            if pool_procurados:
                nome_p, tipo_p = pool_procurados.pop(0) 
                if tipo_p == 'Marinheiro':
                    ilha_marinha = random.choice(ilhas)
                    procurado_final = f"Parece que tem atividade da Marinha em **{ilha_marinha}** sob o comando de **{nome_p}**!"
                else:
                    ilha_p = random.choice(ilhas)
                    procurado_final = f"**PROCURADO!** Está sendo contado pelos ventos que terror está sendo propagado em **{ilha_p}**, sob as ordens de **{nome_p.upper()}**"
            else:
                procurado_final = "Semana tranquila... Nenhum pirata notável foi reportado pelas autoridades."

            temp = sortear_item_com_peso(CLIMA_OPCOES["temperatura"])
            vento = sortear_item_com_peso(CLIMA_OPCOES["vento"])
            precip = sortear_item_com_peso(CLIMA_OPCOES["precipitacao"])

            msg_mar = (
                f"# {titulo_teste}RAINBOW NEWS - EXPRESS ({mar.upper()})\n"
                "-# Por Typist Mustang\n\n"
                f"## Fatos semanais sobre o {mar}! \n"
                f"- {rumor_final}\n- {mestre_final}\n- {nakama_final}\n- {procurado_final}\n\n"
                f"## Boletim do tempo - {mar}\n"
                f"- Oh yes! A temperatura hoje está... **{temp.upper()}**.\n"
                f"- Icem as velas, ou não pois hoje temos Vento... **{vento.upper()}**.\n"
                f"- E por último mas não menos importante, para as donas de casa que deixaram roupas no varal a previsão é de... **{precip.upper()}**.\n"
            )
            mensagens[mar] = msg_mar

        # --- GERAÇÃO DO PARADISE ---
        rota_tesouro, rota_procurado = random.sample(PARADISE_ROTAS, 2)
        rumor_paradise_1 = random.choice(PARADISE_TEMPLATES["tesouro"]).format(rota=rota_tesouro.upper())
        rumor_paradise_2 = random.choice(PARADISE_TEMPLATES["procurado"]).format(rota=rota_procurado.upper())

        msg_paradise = (
            f"# {titulo_teste}RAINBOW NEWS - EXPRESS (PARADISE)\n"
            "-# Por Typist Mustang\n\n"
            "## Fatos semanais sobre o Paradise! \n"
            f"- {rumor_paradise_1}\n- {rumor_paradise_2}\n\n"
            f"{TEXTO_MENCOES}"
        )
        mensagens["Paradise"] = msg_paradise

        return mensagens

    async def enviar_boletins(self, canal, teste=False):
        boletins = self.gerar_boletins_completos(teste=teste)
        
        # Função auxiliar para abrir a imagem fisicamente e enviar junto com o texto
        async def enviar_com_imagem(texto):
            # O Discord exige um novo objeto File para cada mensagem enviada
            arquivo_imagem = discord.File("image-1.png", filename="image-1.png")
            await canal.send(content=texto, file=arquivo_imagem)

        # Envia as 5 mensagens anexando a imagem física em cada uma delas
        await enviar_com_imagem(boletins["East Blue"])
        await enviar_com_imagem(boletins["South Blue"])
        await enviar_com_imagem(boletins["North Blue"])
        await enviar_com_imagem(boletins["West Blue"])
        await enviar_com_imagem(boletins["Paradise"])

    @tasks.loop(time=HORA_ATUALIZACAO_UTC)
    async def postar_noticias_semanais(self):
        if datetime.datetime.now(datetime.timezone.utc).weekday() != DIA_DA_SEMANA_UTC:
            return
        
        print(f"[{datetime.datetime.now()}] Segunda-feira! Postando os 5 boletins informativos...")
        try:
            canal = self.bot.get_channel(ID_CANAL_JORNAL)
            if not canal:
                print(f"❌ ERRO: Canal com ID {ID_CANAL_JORNAL} não encontrado.")
                return
            await self.enviar_boletins(canal, teste=False)
            print("✅ Todas as 5 edições do jornal foram publicadas!")
        except Exception as e:
            print(f"❌ ERRO ao tentar postar edições do jornal: {e}")

    @postar_noticias_semanais.before_loop
    async def before_postar_noticias(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="testar_noticia", description="Força o envio das 5 edições de teste no canal atual.")
    @is_allowed_role()
    async def testar_noticia_slash(self, interaction: discord.Interaction):
        print("Forçando envio de notícias globais (teste)...")
        try:
            await interaction.response.send_message("✅ Gerando e enviando as 5 edições de teste...", ephemeral=True)
            await self.enviar_boletins(interaction.channel, teste=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ERRO ao gerar edições de teste: {e}", ephemeral=True)

    @app_commands.command(name="cadastrar", description="Cadastra um novo procurado na planilha do Google.")
    @is_allowed_role()
    @app_commands.describe(nome="O nome completo.", tipo="O tipo (Pirata ou Marinheiro).")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Pirata", value="Pirata"),
        app_commands.Choice(name="Marinheiro", value="Marinheiro")
    ])
    async def cadastrar_procurado_slash(self, interaction: discord.Interaction, nome: str, tipo: app_commands.Choice[str]):
        # O Defer avisa o Discord para esperar (pode levar até 15 minutos agora)
        await interaction.response.defer(ephemeral=True)
        
        if db.cadastrar_procurado(nome, tipo.value):
            # Como usamos o defer, a resposta final deve ser com 'followup.send'
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
        await interaction.response.defer(ephemeral=True)
        
        if nome_novo is None and novo_tipo is None:
            await interaction.followup.send("❌ Forneça pelo menos um novo nome ou tipo para atualizar.")
            return
        
        tipo_valor = novo_tipo.value if novo_tipo else None
        resultado = db.atualizar_procurado(nome_antigo, nome_novo=nome_novo, novo_tipo=tipo_valor)

        if resultado == "sucesso":
            msg = f"✅ Planilha atualizada para **{nome_antigo}**!"
            if nome_novo: msg += f"\n- Novo nome: **{nome_novo}**"
            if tipo_valor: msg += f"\n- Novo tipo: **{tipo_valor}**"
            await interaction.followup.send(msg)
        elif resultado == "nao_encontrado":
            await interaction.followup.send(f"❌ Erro! **{nome_antigo}** não consta na planilha.")
        elif resultado == "duplicado":
            await interaction.followup.send(f"❌ Erro! O nome **{nome_novo}** já está alocado a outro registro.")

    @app_commands.command(name="lista_procurados", description="Puxa a lista completa de procurados da nuvem.")
    @is_allowed_role()
    async def lista_procurados_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        lista = db.listar_procurados()
        if not lista:
            await interaction.followup.send("ℹ️ A planilha do Google está vazia.")
            return

        embed = discord.Embed(title="Lista Global de Procurados & Marinheiros", color=discord.Color.orange())
        texto_lista = "\n".join(f"• **{nome}** (Tipo: *{tipo}*)" for (nome, tipo) in lista)
        
        if len(texto_lista) > 4000:
            texto_lista = texto_lista[:4000] + "\n... (Muitos dados para exibir tudo aqui)"

        embed.description = texto_lista
        await interaction.followup.send(embed=embed)

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