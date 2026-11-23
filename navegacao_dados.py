"""
navegacao_dados.py
-------------------
Ilhas do Novo Mundo usadas pra semear a aba "NM_Ilhas" da planilha
(só na primeira vez; depois a planilha é a fonte da verdade e pode ser
editada à mão). Cada linha: (area, nome, tipo, nota).

area: 1, 2, 3, 4 ou "calm" (Calm Belt).
tipo:
  inicial        -> ilha de partida (nunca é sincronizada)
  sincronizavel  -> ilha comum que o Log Pose pode apontar
  secreta        -> só aparece ao falhar na navegação (da área atual)
  principal      -> ilha que libera a próxima área (Dressrosa, Wano, Elbaph, Laugh Tale)
  totto          -> o arquipélago Totto Land em si (sincronizável na Área 2)
  totto_ilha     -> ilha DENTRO de Totto Land (só sincronizável lá dentro)
  calm           -> ilha do Calm Belt (nota = nível 1 ou 2)
"""

NOME_TOTTO = "Arquipélago Totto Land"
NOME_LAUGH_TALE = "Laugh Tale"

INICIAIS = ["Risky Red", "Mystoria", "Raijin"]

_A1 = [
    "Nebulandia", "Silver Mine", "Alchemy", "Ilha Dock", "Ilha Mão", "Ilha Shinah",
    "Tomoshibi Island", "Ilha Dinamite", "Mar Profundo", "Ilhas Escondidas",
    "Ilha das Águias", "Vulture Black", "Hundred Hands", "Ilha dos Porcos",
    "New Marineford", "Reino Mogaro", "Ilha Champloo", "Ilha Kanto",
    "Ilha Gotham City", "Marriage Greenland", "Karai Bari", "Ilha do Laço",
    "Ilha dos Pássaros", "Ilha Nocturne", "G-5", "Madagascar",
    "Ilha Elriksheim", "Ilha de Nárvênia",
]
_A1_SECRETAS = ["Punk Hazard", "Jail Island", "Digital Art Island", "Fron Island (G-F)", "Tongari Island"]

_A2 = [
    "Ilha Onde se Conseguem Ovos", "Sarguardinho Isle", "Serpentia", "Raizes de Sangue",
    "Ilha No Cardinal", "Ilha Resorto", "Sphinx", "Reino Doerena", "Reino Majiatsuka",
    "Abismo dos Trevos", "Ilha Sidêria", "Foodvalten", "Arquipélago de Azuran",
    "Ilha Broc Coli", "Esmerald Isle", "G - S", "Império de Jade", "Ilha da Coroa",
    "Ilha Gartel", "Reino Standing", "Ilha Applenine", "Avalon", "Reino Aurea",
    "Ilha Porto Chibaralta", "Reino de Althain", "Reino Prodence", "Ilha Carnavália",
    "Ilha Lioness",
]
_A2_SECRETAS = [
    ("Ilha Carbador", "confirmar se será secreta"), ("Ilha do Labirinto", ""),
    ("Ilha Kinoko", ""), ("Strumia", ""), ("Ilha Paraíso", ""), ("Waford", ""),
]

_A3 = [
    "Tortuga", "Ilha Inicial", "Fortaleza Abandonada", "Ilha Windfall", "Terra do Nunca",
    "Reino Norveil", "Ilha do Abacaxi", "Hachinosu", "Dai-Gurren", "Tão Tão Distante",
    "Mugenjō", "Ilha Natsuyasumi", "Ilha Lodestar", "Valakian", "Ortzi", "Ilha Atarashi",
    "Arquipélago Kefir", "Ilha Chickenfoot", "Terra Prometida", "Ilha Winner",
    "Terra dos Dinossauros", "Ilha de Daire", "Númenor", "Província Insular Dokukyoku",
    "Reino Fêenka", "Ilha Ryunashi", "Ilha Peak Ode", "Reino Pepe", "Koaland",
    "Port Royal", "Ilha Pacturam", "Vella Nocte", "Egghead", "G - 14", "Monte Kintoki",
    "Gladius",
]
_A3_SECRETAS = [
    "Ilha da Xuxa", "Floresta do Santuário", "Ilha Poleiro do Dragão", "Black Rock",
    "Ilha da Fonte da Juventude", "Ilha da Morte", "Isla de Pelegostos", "Ilha Midori",
    "Ilha das Cruzes", "Ilha Togakure",
]

_CALM_1 = [
    "Reino de Zeal", "Reino Esquecido de Fonron", "Antillia", "R'lyeh",
    "Fortaleza dos Esqueletos", "Ilhas Ábaco", "Rugido do Diabo", "Reino de Fungiland",
    "Última Thule", "Tír na nÓg", "Ilha de Seiren", "Ilha do Tingle", "Torre dos Deuses",
    "Arquipélago Celeste de Lanayru", "Ilha Mercay", "Ilha Penglai",
]
_CALM_2 = [
    "Ilha da Garganta Cortada", "Terras Proibidas", "Hy-Brasil", "Gorgoroth",
    "Ilhas Cruzadas", "Dorsal Atlântica", "Celéstia", "Ilha Mekar",
    "Ilhas das Nuvens de Tempestade", "Ilha do Entardecer",
    "Arquipélago das Bolhas Perdidas", "Ilha Koholint", "Reino Submerso das Sereias",
    "Terras de Rat Fink", "Ilha Cubo", "Ratanabá",
]


def ilhas_seed() -> list:
    """[(area, nome, tipo, nota)] — ordem de gravação na planilha."""
    linhas = []
    linhas += [(1, n, "inicial", "") for n in INICIAIS]
    linhas += [(1, n, "sincronizavel", "") for n in _A1]
    linhas += [(1, n, "secreta", "") for n in _A1_SECRETAS]
    linhas.append((1, "Dressrosa", "principal", "libera a Área 2"))

    linhas += [(2, n, "sincronizavel", "") for n in _A2]
    linhas.append((2, "Arquipélago Hollow Horn", "sincronizavel", "especial"))
    linhas.append((2, NOME_TOTTO, "totto", "cadastre as ilhas internas como tipo totto_ilha"))
    linhas += [(2, n, "secreta", nota) for n, nota in _A2_SECRETAS]
    linhas.append((2, "Wano", "principal", "libera a Área 3"))

    linhas += [(3, n, "sincronizavel", "") for n in _A3]
    linhas += [(3, n, "secreta", "") for n in _A3_SECRETAS]
    linhas.append((3, "Elbaph", "principal", "libera Laugh Tale"))

    linhas.append((4, NOME_LAUGH_TALE, "principal", "destino final"))

    linhas += [("calm", n, "calm", "1") for n in _CALM_1]
    linhas += [("calm", n, "calm", "2") for n in _CALM_2]
    return linhas
