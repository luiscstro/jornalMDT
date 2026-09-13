import discord
from discord import app_commands
from discord.ext import commands
import random
import datetime
import json
import os
import asyncio
import re

ARQUIVO_DADOS = "exploracao_data.json"

# ==========================================
# ⚙️ DADOS PADRÃO 
# ==========================================
DADOS_PADRAO = {
    "paradise": {
        "titulo": "Exploração: Paradise",
        "cor": 13938487, # Dourado
        "itens": [
            {"nome": "Ruínas", "chance": 80, "tipo": "normal", "msg_sim": "parece ter algo valioso nessa ilha.", "msg_nao": "não parece ter nada de valioso nessa ilha."},
            {"nome": "Contratação", "chance": 30, "tipo": "prof_profissional"},
            {"nome": "Poneglyph", "chance": 25, "tipo": "poneglyph"}
        ]
    },
    "blues": {
        "titulo": "Exploração: Blues",
        "cor": 4620980, # Azul
        "itens": [
            {"nome": "Ruínas", "chance": 75, "tipo": "normal", "msg_sim": "parece ter algo valioso nessa ilha.", "msg_nao": "não parece ter nada de valioso nessa ilha."},
            {"nome": "Contratação", "chance": 30, "tipo": "prof_amador"},
            {"nome": "Poneglyph", "chance": 1, "tipo": "poneglyph"}
        ]
    }
}

# Dicionário de GIFs para os Poneglyphs
GIFS_PONEGLYPH = {
    "padrao": "https://media.tenor.com/gK9pM3n48UIAAAAC/poneglyph-one-piece.gif", 
    "akuma": "https://media.tenor.com/M6L5P18hXmUAAAAC/devil-fruit-one-piece.gif", 
    "meito": "https://media.tenor.com/w4pB2Qf1FhIAAAAC/zoro-one-piece.gif", 
    "arma": "https://media.tenor.com/yv-5N1tY2X8AAAAC/one-piece-shirahoshi.gif" 
}

# ==========================================
# 🖥️ SISTEMA DE UI (Botões e Caixas de Texto)
# ==========================================
class EnviarModal(discord.ui.Modal, title="Encaminhar Resultado"):
    canal_input = discord.ui.TextInput(
        label="Link ou ID do Canal de Destino",
        style=discord.TextStyle.short,
        placeholder="Cole o ID ou o Link do chat aqui...",
        required=True
    )

    def __init__(self, embeds_para_enviar):
        super().__init__()
        self.embeds_para_enviar = embeds_para_enviar

    async def on_submit(self, interaction: discord.Interaction):
        texto = self.canal_input.value
        match = re.search(r'(\d{17,20})', texto.split('/')[-1])
        
        if not match:
            await interaction.response.send_message("❌ Não consegui encontrar um ID de canal válido nisso aí.", ephemeral=True)
            return
        
        canal_id = int(match.group(1))
        canal_destino = interaction.client.get_channel(canal_id)

        if not canal_destino:
            await interaction.response.send_message("❌ Canal não encontrado! Tem certeza que o bot tem acesso a esse chat?", ephemeral=True)
            return

        try:
            await interaction.response.send_message("✅ Enviando...", ephemeral=True)
            for embed in self.embeds_para_enviar:
                await canal_destino.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("❌ Eu não tenho permissão para enviar mensagens nesse chat!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Ocorreu um erro ao enviar: {e}", ephemeral=True)

class EncaminharView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=None)
        self.embeds = embeds

        btn_encaminhar = discord.ui.Button(label="Encaminhar Resultado", style=discord.ButtonStyle.primary, emoji="📋")
        
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(EnviarModal(self.embeds))
            
        btn_encaminhar.callback = callback
        self.add_item(btn_encaminhar)


# ==========================================
# ⚓ CLASSE PRINCIPAL DO COG
# ==========================================
class Exploracao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dados = self.carregar_dados()

    def carregar_dados(self):
        if not os.path.exists(ARQUIVO_DADOS):
            self.salvar_dados(DADOS_PADRAO)
            return DADOS_PADRAO
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            self.salvar_dados(DADOS_PADRAO)
            return DADOS_PADRAO

    def salvar_dados(self, dados):
        with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        self.dados = dados

    def sortear_contratado(self, tipo):
        opcoes = ["Infame", "Desconhecido", "Famoso"]
        pesos = [50, 30, 20]
        escolhido = random.choices(opcoes, weights=pesos, k=1)[0]
        cargo = "Amador" if tipo == "prof_amador" else "Profissional"
        return f"{cargo}: {escolhido}"

    def sortear_poneglyph(self):
        opcoes = [
            {"texto": "Você encontrou diversos relatos e registros sobre o Século Perdido!", "bonus": "-# +2 no próximo teste de identificar ruína", "tipo_gif": "padrao"},
            {"texto": "As coisas encontradas nessa escritura parece se interligar com alguma outra...", "bonus": "-# Caçador de tesouros no próximo *Identificar Ruínas* bem sucedido.", "tipo_gif": "padrao"},
            {"texto": "Você descobriu uma lenda muito interessante, parece que em alguma ilha não muito distante há uma Akuma no Mi em um tesouro!", "bonus": "-# O próximo *Identificar ruínas* bem sucedido haverá uma akuma no mi garantida", "tipo_gif": "akuma"},
            {"texto": "Você descobriu um conto de um guerreiro interessante, parece que em alguma ilha não muito distante há uma arma Meito a ser dominada!", "bonus": "-# O próximo *Identificar ruínas* bem sucedido haverá uma Meito garantida", "tipo_gif": "meito"},
            {"texto": "Você encontrou manuscritos sobre um tipo de arma ancestral... talvez alguém habilidoso suficiente consiga usar bem essas instruções.", "bonus": "-# A tripulação recebe 3 pontos de melhoria de navio e passa a poder gastar no máximo 8 pontos em melhoria de navio", "tipo_gif": "arma"}
        ]
        pesos = [45, 40, 7, 7, 1]
        return random.choices(opcoes, weights=pesos, k=1)[0]

    async def tier_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=t.capitalize(), value=t) for t in self.dados.keys() if current.lower() in t.lower()]

    # ==========================
    # 🎲 COMANDO PRINCIPAL (MESA)
    # ==========================
    @app_commands.command(name="exploracao", description="Mesa de exploração (One Piece RPG)")
    @app_commands.autocomplete(tier=tier_autocomplete)
    async def exploracao(self, interaction: discord.Interaction, tier: str, debug: bool = False):
        
        await interaction.response.defer() 
        
        try:
            config = self.dados.get(tier)
            if not config:
                await interaction.followup.send(f"❌ A região `{tier}` não existe.")
                return

            embed_main = discord.Embed(title=f"🧭 {config.get('titulo', 'Exploração')}", color=config.get('cor', 0xFFFFFF))
            lista_itens = config.get("itens", [])

            for item in lista_itens:
                tipo_item = item.get("tipo", "normal")
                nome_item = item.get("nome", "Desconhecido")

                if tipo_item == "normal":
                    roll = round(random.uniform(0, 100), 1)
                    sucesso = roll < item.get("chance", 0)
                    debug_txt = f" `[debug: sorteou {roll} de {item.get('chance', 0)}%]`" if debug else ""
                    if sucesso:
                        embed_main.add_field(name=f"**{nome_item}**", value=f"_Sim_, {item.get('msg_sim', 'encontrado.')}{debug_txt}", inline=False)
                    else:
                        embed_main.add_field(name=f"**{nome_item}**", value=f"_Não_, {item.get('msg_nao', 'não encontrado.')}{debug_txt}", inline=False)

                elif tipo_item in ["prof_amador", "prof_profissional"]:
                    roll_prof = round(random.uniform(0, 100), 1)
                    roll_cont = round(random.uniform(0, 100), 1)
                    sucesso_prof = roll_prof < item.get("chance", 30)
                    sucesso_contratado = roll_cont < 50
                    debug_prof = f" `[debug: sorteou {roll_prof} de {item.get('chance', 30)}%]`" if debug else ""
                    debug_cont = f" `[debug: sorteou {roll_cont} de 50%]`" if debug else ""

                    if sucesso_prof:
                        embed_main.add_field(name="**Professor**", value=f"_Sim_, há uma pessoa disposta a ensinar uma nova profissão{debug_prof}", inline=False)
                    else:
                        embed_main.add_field(name="**Professor**", value=f"_Não_, não há ninguém disposto a ensinar uma nova profissão{debug_prof}", inline=False)

                    if sucesso_contratado:
                        rank = self.sortear_contratado(tipo_item)
                        embed_main.add_field(name="**Contratado**", value=f"_Sim_, há alguém disposto a trabalhar em seu navio, um _{rank}_{debug_cont}", inline=False)
                    else:
                        embed_main.add_field(name="**Contratado**", value=f"_Não_, não há ninguém disposto a trabalhar em seu navio{debug_cont}", inline=False)

                elif tipo_item == "poneglyph":
                    roll = round(random.uniform(0, 100), 1)
                    sucesso = roll < item.get("chance", 0)
                    debug_txt = f" `[debug: sorteou {roll} de {item.get('chance', 0)}%]`" if debug else ""
                    if sucesso:
                        embed_main.add_field(name="**Poneglyph**", value=f"_Sim_, espera... encontramos um monólito de pedra extremamente peculiar... *(Use o comando `/ler_poneglyph` para investigar!)*{debug_txt}", inline=False)
                    else:
                        embed_main.add_field(name="**Poneglyph**", value=f"_Não_, não há registros do que quer que seja isso (Não tem na ilha){debug_txt}", inline=False)

            embed_main.set_footer(text=f"Explorado por {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed_main)

            # Botão de encaminhar apenas o embed da mesa
            view_encaminhar = EncaminharView([embed_main])
            await interaction.channel.send("🛠️ **Opções do Mestre:** Deseja encaminhar a exploração para outro canal?", view=view_encaminhar)

        except Exception as e:
            await interaction.followup.send(f"⚠️ **Erro ao gerar exploração:** `{e}`")

    # ==========================
    # 📜 COMANDO PONEGLYPH (TEATRO)
    # ==========================
    @app_commands.command(name="ler_poneglyph", description="Faz a leitura teatral de um Poneglyph encontrado!")
    async def ler_poneglyph(self, interaction: discord.Interaction):
        
        await interaction.response.defer()
        
        try:
            # Inicia o Teatro
            await interaction.followup.send("Pera, pera um pouco... PERA PERA AÍ!")
            await asyncio.sleep(3)
            await interaction.channel.send("Vocês têm noção do que acabaram de encontrar?! Isso não é uma rocha qualquer!")
            await asyncio.sleep(4)
            await interaction.channel.send("É um **Poneglyph**! Um bloco de pedra indestrutível criado há mais de 800 anos...")
            await asyncio.sleep(4)
            await interaction.channel.send("O Governo Mundial apagaria nossa existência do mapa e faria um Buster Call agora mesmo só por olharmos para isso! Eles matariam para esconder os registros do Século Perdido e a queda do Grande Reino!")
            await asyncio.sleep(5)
            await interaction.channel.send("Fiquem quietos, deixem eu passar a mão por esses entalhes antigos... eu consigo ler um trecho...")
            await asyncio.sleep(3)

            # Sorteio Real
            resultado_poneglyph = self.sortear_poneglyph()
            descricao_final = f"**{resultado_poneglyph['texto']}**\n{resultado_poneglyph['bonus']}"
            
            embed_pone = discord.Embed(
                title="📜 Fragmento da História Perdida",
                description=descricao_final,
                color=0x2b2d31 
            )
            url_gif = GIFS_PONEGLYPH[resultado_poneglyph["tipo_gif"]]
            embed_pone.set_image(url=url_gif)
            
            await interaction.channel.send(embed=embed_pone)

            # Oferece a opção de encaminhar a leitura do Poneglyph
            view_encaminhar = EncaminharView([embed_pone])
            await interaction.channel.send("🛠️ **Opções do Mestre:** Encaminhar a leitura do Poneglyph para outro chat?", view=view_encaminhar)

        except Exception as e:
            await interaction.followup.send(f"⚠️ **Erro na leitura do Poneglyph:** `{e}`")

    # ==========================
    # 🛠️ COMANDOS DE ADMINISTRAÇÃO
    # ==========================

async def setup(bot):
    await bot.add_cog(Exploracao(bot))