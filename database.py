import random
import gspread
from google.oauth2.service_account import Credentials

# Configuração das credenciais do Google
ESCOPOS = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

_ultimo_erro_conexao = None


def obter_ultimo_erro_conexao():
    """Retorna a mensagem da última falha ao conectar no Google Sheets (ou
    None se a última tentativa deu certo). Usado pelos comandos pra mostrar
    o motivo real em vez de simplesmente dizer 'a planilha está vazia'."""
    return _ultimo_erro_conexao


def obter_aba():
    """Conecta à API do Google e retorna a aba 'Procurados' da planilha."""
    global _ultimo_erro_conexao
    try:
        # Carrega o arquivo JSON de credenciais que você colocou na pasta
        credenciais = Credentials.from_service_account_file("credenciais.json", scopes=ESCOPOS)
        cliente = gspread.authorize(credenciais)

        # Abra pelo nome exato da sua planilha no Google Drive
        planilha = cliente.open("Procurados Blues")
        aba = planilha.worksheet("Procurados")
        _ultimo_erro_conexao = None
        return aba
    except Exception as e:
        _ultimo_erro_conexao = str(e)
        print(f"❌ ERRO ao conectar com o Google Sheets: {e}")
        return None

def cadastrar_procurado(nome, tipo):
    ws = obter_aba()
    if not ws: return False
    
    # Verifica duplicados (ignorando maiúsculas e minúsculas)
    nomes_existentes = ws.col_values(1)[1:] # Pega todos os nomes pulando o cabeçalho
    if any(n.lower() == nome.lower() for n in nomes_existentes):
        return False
        
    ws.append_row([nome, tipo])
    return True

def remover_procurado(nome):
    ws = obter_aba()
    if not ws: return False
    
    valores = ws.get_all_values()
    for idx, row in enumerate(valores):
        if idx == 0: continue # Pula cabeçalho
        if row[0].lower() == nome.lower():
            # No gspread as linhas começam em 1, então o índice na lista + 1 corresponde à linha exata
            ws.delete_rows(idx + 1)
            return True
    return False

def atualizar_procurado(nome_antigo, nome_novo=None, novo_tipo=None):
    if not nome_novo and not novo_tipo:
        return "nada_para_fazer"
        
    ws = obter_aba()
    if not ws: return "erro_conexao"
    
    valores = ws.get_all_values()
    
    # Se for alterar o nome, verifica se o novo nome já pertence a outra pessoa
    if nome_novo:
        for idx, row in enumerate(valores):
            if idx == 0: continue
            if row[0].lower() == nome_novo.lower() and nome_novo.lower() != nome_antigo.lower():
                return "duplicado"
                
    # Procura pelo registro antigo para atualizar as colunas A e/ou B
    for idx, row in enumerate(valores):
        if idx == 0: continue
        if row[0].lower() == nome_antigo.lower():
            num_linha = idx + 1
            if nome_novo:
                ws.update_cell(num_linha, 1, nome_novo)
            if novo_tipo:
                ws.update_cell(num_linha, 2, novo_tipo)
            return "sucesso"
            
    return "nao_encontrado"

def listar_procurados():
    ws = obter_aba()
    if not ws: return []
    
    valores = ws.get_all_values()[1:] # Pega tudo pulando os cabeçalhos
    lista = [(row[0], row[1]) for row in valores if len(row) >= 2 and row[0] and row[1]]
    return sorted(lista, key=lambda x: x[0])

def buscar_procurados(filtro_nome):
    ws = obter_aba()
    if not ws: return []
    
    nomes = ws.col_values(1)[1:]
    lista = [(nome,) for nome in nomes if filtro_nome.lower() in nome.lower()]
    lista = sorted(lista, key=lambda x: x[0])
    return lista[:25] # Limite de autocomplete do Discord

def sortear_procurado():
    """Esta função agora é controlada pelo gerenciador do Jornal."""
    ws = obter_aba()
    if not ws: return None
    
    valores = ws.get_all_values()[1:]
    lista = [(row[0], row[1]) for row in valores if len(row) >= 2 and row[0] and row[1]]
    if not lista: return None
    return random.choice(lista)