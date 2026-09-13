import discord
from discord.ext import commands
import traceback
from dotenv import load_dotenv # <--- Ferramenta de raio-x de erros adicionada

import os
load_dotenv()
TOKEN = os.getenv("TOKEN_DISCORD")

class BotBase(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="jornal!", intents=intents)

    async def setup_hook(self):
        print("--- Carregando Cogs ---")
        
        # 1. CARREGA O JORNAL
        try:
            await self.load_extension("cogs.jornal")
            print("✅ Cog 'jornal' carregado com sucesso.")
        except Exception as e:
            print("❌ Erro FATAL ao carregar o cog 'jornal':")
            traceback.print_exc() # <--- Isso vai mostrar a linha exata do erro!

        # 2. CARREGA A EXPLORAÇÃO (Mesa RPG)
        try:
            await self.load_extension("cogs.exploracao")
            print("✅ Cog 'exploracao' carregado com sucesso.")
        except Exception as e:
            print("❌ Erro FATAL ao carregar o cog 'exploracao':")
            traceback.print_exc()

        # 3. CARREGA O PAINEL DE REGIÕES (/regioes)
        try:
            await self.load_extension("cogs.regioes_admin")
            print("✅ Cog 'regioes_admin' carregado com sucesso.")
        except Exception as e:
            print("❌ Erro FATAL ao carregar o cog 'regioes_admin':")
            traceback.print_exc()

        # 4. CARREGA A CAÇA A PROCURADOS (/procurado)
        try:
            await self.load_extension("cogs.procurado")
            print("✅ Cog 'procurado' carregado com sucesso.")
        except Exception as e:
            print("❌ Erro FATAL ao carregar o cog 'procurado':")
            traceback.print_exc()

        # SINCRONIZA TODOS OS COMANDOS
        print("--- Sincronizando Comandos Slash ---")
        try:
            synced = await self.tree.sync()
            print(f"✅ Sincronizados {len(synced)} comandos globais.")
        except Exception as e:
            print(f"❌ Erro ao sincronizar comandos slash: {e}")

    async def on_ready(self):
        print(f"✅ Bot '{self.user.name}' está 100% online e operante!")

if __name__ == "__main__":
    bot = BotBase()
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ ERRO ao iniciar o bot: {e}")