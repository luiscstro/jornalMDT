"""
ajuda_dados.py
---------------
Textos do /ajuda: categorias e a explicação de cada comando.

IMPORTANTE: ao criar, renomear ou remover um comando, atualize este arquivo.
(Há um teste simples no CLAUDE.md/docs pra conferir se está em dia.)

Cada comando:
  resumo   -> uma linha (aparece no embed geral)
  staff    -> True se só os cargos permitidos podem usar
  uso      -> como digitar
  params   -> [(nome, explicação)]
  detalhes -> explicação completa (markdown do Discord)
  ver      -> outros comandos relacionados
"""

CATEGORIAS = [
    ("🧭 Navegação do Novo Mundo", ["navegar", "navegacao"]),
    ("🌊 Encontros e exploração", ["encontromaritimo", "desafiodasilhas", "exploracao", "ler_poneglyph"]),
    ("🏴‍☠️ Procurados e caçadas", ["procurado", "procurados_ativos", "procurado_liberar", "cadastrar", "editar", "remover", "lista_procurados"]),
    ("📰 Jornal", ["testar_noticia", "rerrolar_jornal", "rerrolar_variavel", "regioes"]),
    ("❓ Outros", ["ajuda"]),
]

COMANDOS = {
    # ------------------------------------------------------------------ navegação
    "navegar": {
        "resumo": "Sincroniza o Log Pose 3A do bando (com animação e botões).",
        "staff": True,
        "uso": "/navegar bando:<nome> [forcar:<sim/não>]",
        "params": [
            ("bando", "Nome do bando (tem autocomplete)."),
            ("forcar", "Só pro mestre: ignora a espera de 1 semana quando as agulhas apontam pra Totto Land."),
        ],
        "detalhes": (
            "Sorteia **3 ilhas diferentes** pra onde o Log Pose aponta e o **tipo de cada agulha**:\n"
            "🟢 **Estável**: CD normal, +1 progressão.\n"
            "🟡 **Moderada**: CD **+2**, +1,5 progressão.\n"
            "🔴 **Instável**: CD **+5**, +3 progressões, e **falhar leva ao Calm Belt**.\n\n"
            "A mensagem sai com um **GIF animado** do Log Pose e botões **✅ Sucesso / ❌ Falha** pra cada agulha. "
            "Depois do Teste de Navegação, o mestre aperta o botão da agulha que o bando seguiu. Os botões "
            "**não expiram** (nem se o bot reiniciar), valem **uma vez só** e perdem a validade se o bando sincronizar de novo.\n\n"
            "**Sucesso:** o bando chega na ilha e ganha a progressão. **Falha:** vai parar numa Ilha Secreta da área "
            "(ou no Calm Belt, se a agulha era Instável), sem progressão.\n\n"
            "**Regras de área:** a ilha principal (Dressrosa → Wano → Elbaph) só pode aparecer com **20 progressões** na área. "
            "Ilhas de áreas já exploradas ainda aparecem, mas com chance baixa. Ilha visitada não volta.\n\n"
            "**Totto Land (Área 2):** se uma agulha sortear o arquipélago, **todas** apontam pra ele. O bando vai (botão de sucesso) "
            "ou espera 1 semana pra sincronizar de novo."
        ),
        "ver": ["navegacao", "encontromaritimo"],
    },
    "navegacao": {
        "resumo": "Painel da staff: bandos, ilhas visitadas, ajustes e cadastro de ilhas.",
        "staff": True,
        "uso": "/navegacao",
        "params": [],
        "detalhes": (
            "Abre o **painel de controle** da navegação (só você vê). Escolha um bando no menu pra:\n"
            "🧭 **Navegar**: sincroniza o Log Pose e posta a mensagem com GIF e botões no canal.\n"
            "🏝️ **Ilhas visitadas**: lista na ordem da viagem, por Área 1 a 4, Totto Land, Ilhas Secretas e Calm Belt, "
            "com visitadas/total de cada grupo.\n"
            "🍬 **Sair de Totto**: libera o bando do arquipélago (exige 5 progressões lá dentro).\n"
            "✏️ **Ajustar**: corrige área, progressão, local e se está em Totto Land (dessincroniza o Log Pose).\n"
            "🔄 **Atualizar** e ⬅️ **Voltar**.\n\n"
            "No menu principal: ➕ **Novo bando** (parte de Raijin, Risky Red ou Mystoria) e 🏝️ **Ilhas** "
            "(cadastrar e remover ilhas, ex: as ilhas internas de Totto Land: área `2`, tipo `totto_ilha`).\n\n"
            "O rodapé mostra em qual banco de dados os dados estão guardados."
        ),
        "ver": ["navegar"],
    },
    # ------------------------------------------------------------------ encontros / exploração
    "encontromaritimo": {
        "resumo": "Sorteia o que acontece enquanto a tripulação navega.",
        "staff": True,
        "uso": "/encontromaritimo regiao:<região> [debug:<sim/não>]",
        "params": [
            ("regiao", "Paradise, Novo Mundo, Calm Belt ou Totto Land."),
            ("debug", "Mostra o número sorteado."),
        ],
        "detalhes": (
            "Sorteia um encontro de acordo com a região (cada tabela soma 100%):\n"
            "• **Paradise:** 60% caçada na ilha, 14% bando pirata (ND 9), 14% Marinha (ND 10), 6% caçador de recompensa (ND 11), 6% Rei do Mar (ND 11).\n"
            "• **Novo Mundo:** 60% caçada, 14% pirata (ND 14), 14% Marinha (ND 15), 6% caçador (ND 16), 6% Rei do Mar (ND 16).\n"
            "• **Calm Belt:** 40% nada, 30% Rei do Mar, 12% caçador, 9% pirata, 9% Marinha (todos ND 16).\n"
            "• **Totto Land:** não usa tabela, rola um **Desastre (1d6)**: frotas Tarte (dano em d10), Oficiais Doces que tiram deslocamento, "
            "ou o Embate (Técnica Combinada, escape com Navegação CD 25).\n\n"
            "**Caçada na ilha** quer dizer que um procurado anda arrumando confusão na região (sem combate direto)."
        ),
        "ver": ["desafiodasilhas", "navegar", "procurado"],
    },
    "desafiodasilhas": {
        "resumo": "Totto Land: sorteia o encontro ao iniciar uma exploração.",
        "staff": True,
        "uso": "/desafiodasilhas [nc:<0 a 10>] [debug:<sim/não>]",
        "params": [
            ("nc", "Nível de Confusão atual do bando (0 a 10)."),
            ("debug", "Mostra o número sorteado."),
        ],
        "detalhes": (
            "Rola **1d12** ao iniciar uma exploração em Totto Land:\n"
            "• **1 a 4:** passa despercebido.\n"
            "• **5 a 9:** Patrulha Doce.\n"
            "• **10 e 11:** Combatente Doce (ND 14).\n"
            "• **12:** Oficial Doce (ND 15).\n\n"
            "O **Nível de Confusão (NC)** tem prioridade sobre o dado: **NC 8 ou 9** força o **Exército da Fúria** (ND 16) e "
            "**NC 10** força um **General Doce** (ND 17).\n"
            "Estado de caçada do bando: NC 0-1 desconhecidos; 2-7 monitorados (CD de navegação **+1**); 8-9 inimigos públicos; 10 alvos marcados."
        ),
        "ver": ["encontromaritimo"],
    },
    "exploracao": {
        "resumo": "Mesa de exploração de uma ilha (One Piece RPG).",
        "staff": False,
        "uso": "/exploracao tier:<paradise|blues> [debug:<sim/não>]",
        "params": [
            ("tier", "Região explorada: `paradise` ou `blues`."),
            ("debug", "Mostra os números sorteados."),
        ],
        "detalhes": (
            "Sorteia o que há na ilha:\n"
            "• **Ruínas:** algo valioso? (80% em Paradise, 75% nos Blues)\n"
            "• **Professor** (30%) e **Contratado** (50%): alguém pra ensinar uma profissão ou trabalhar no navio. "
            "O contratado vem com rank: Infame 50%, Desconhecido 30%, Famoso 20% (Amador nos Blues, Profissional em Paradise).\n"
            "• **Poneglyph:** 25% em Paradise, 1% nos Blues. Se sair, use `/ler_poneglyph`.\n\n"
            "Depois do resultado aparece o botão **Encaminhar Resultado**, que envia o embed pra outro canal (ID ou link)."
        ),
        "ver": ["ler_poneglyph"],
    },
    "ler_poneglyph": {
        "resumo": "Leitura teatral de um Poneglyph encontrado.",
        "staff": False,
        "uso": "/ler_poneglyph",
        "params": [],
        "detalhes": (
            "Faz a cena de leitura de um Poneglyph, com mensagens uma a uma, e no fim sorteia o fragmento da história perdida:\n"
            "• 45%: +2 no próximo teste de identificar ruína.\n"
            "• 40%: caçador de tesouros no próximo *Identificar Ruínas* bem-sucedido.\n"
            "• 7%: Akuma no Mi garantida na próxima ruína.\n"
            "• 7%: arma Meito garantida na próxima ruína.\n"
            "• 1%: manuscritos de arma ancestral (+3 pontos de melhoria de navio).\n\n"
            "Também tem o botão de encaminhar a leitura pra outro canal."
        ),
        "ver": ["exploracao"],
    },
    # ------------------------------------------------------------------ procurados
    "procurado": {
        "resumo": "Registra a caça a um procurado e sorteia a ilha dele num mar.",
        "staff": True,
        "uso": "/procurado procurado:<nome> mar:<mar>",
        "params": [
            ("procurado", "Quem caçar (o autocomplete só mostra quem está disponível)."),
            ("mar", "Em qual mar procurar."),
        ],
        "detalhes": (
            "Você escolhe o procurado (pirata ou marinheiro) e o mar; só a **ilha** dentro do mar é sorteada (chance igual pra todas).\n"
            "Depois disso o procurado fica **travado por 2 semanas**: ninguém pode caçá-lo de novo até o prazo acabar.\n"
            "Quem está na **edição atual do jornal** também não pode ser caçado, pra não repetir o mesmo alvo em dois lugares.\n"
            "O embed mostra o caçador, o local e quando a trava libera."
        ),
        "ver": ["procurados_ativos", "procurado_liberar", "lista_procurados"],
    },
    "procurados_ativos": {
        "resumo": "Lista as caçadas em andamento e quando cada trava libera.",
        "staff": True,
        "uso": "/procurados_ativos",
        "params": [],
        "detalhes": "Mostra, só pra você, cada caçada ativa com mar, local, caçador e quando a trava de 2 semanas libera.",
        "ver": ["procurado", "procurado_liberar"],
    },
    "procurado_liberar": {
        "resumo": "Libera a trava de um procurado antes do prazo.",
        "staff": True,
        "uso": "/procurado_liberar nome:<procurado>",
        "params": [("nome", "Procurado com caçada ativa (autocomplete).")],
        "detalhes": "Apaga a trava de 2 semanas de um procurado, que já pode ser caçado de novo. Use quando uma caçada acabou antes do prazo.",
        "ver": ["procurados_ativos", "procurado"],
    },
    "cadastrar": {
        "resumo": "Cadastra um procurado na planilha do Google.",
        "staff": True,
        "uso": "/cadastrar nome:<nome> tipo:<Pirata|Marinheiro>",
        "params": [("nome", "Nome completo."), ("tipo", "Pirata ou Marinheiro.")],
        "detalhes": (
            "Adiciona o nome na planilha \"Procurados Blues\". Não aceita nome repetido (maiúsculas e minúsculas não contam). "
            "O tipo muda o texto do jornal: pirata vira \"PROCURADO!\" e marinheiro vira atividade da Marinha."
        ),
        "ver": ["editar", "remover", "lista_procurados"],
    },
    "editar": {
        "resumo": "Edita nome ou tipo de um procurado.",
        "staff": True,
        "uso": "/editar nome_antigo:<nome> [nome_novo:<nome>] [novo_tipo:<tipo>]",
        "params": [
            ("nome_antigo", "Nome atual (autocomplete)."),
            ("nome_novo", "Novo nome (vazio = mantém)."),
            ("novo_tipo", "Novo tipo (vazio = mantém)."),
        ],
        "detalhes": "Informe pelo menos o novo nome ou o novo tipo. Não deixa trocar pra um nome que já pertence a outro registro.",
        "ver": ["cadastrar", "remover"],
    },
    "remover": {
        "resumo": "Remove um procurado da planilha.",
        "staff": True,
        "uso": "/remover nome:<nome exato>",
        "params": [("nome", "Nome exato (autocomplete).")],
        "detalhes": "Apaga o registro da planilha. Não dá pra desfazer pelo bot.",
        "ver": ["cadastrar", "editar"],
    },
    "lista_procurados": {
        "resumo": "Mostra a lista completa de procurados e marinheiros.",
        "staff": True,
        "uso": "/lista_procurados",
        "params": [],
        "detalhes": (
            "Lê a planilha do Google e mostra todos com o tipo, só pra você. Se não conseguir conectar, mostra o motivo do erro em vez de dizer que a lista está vazia."
        ),
        "ver": ["cadastrar", "procurado"],
    },
    # ------------------------------------------------------------------ jornal
    "testar_noticia": {
        "resumo": "Envia edições de teste do jornal no canal atual.",
        "staff": True,
        "uso": "/testar_noticia",
        "params": [],
        "detalhes": (
            "Gera e posta todas as regiões ativas **no canal onde você usou o comando**, com `[TESTE]` no título. "
            "Não trava procurados nem salva a edição, então é seguro pra conferir como o jornal ficaria."
        ),
        "ver": ["rerrolar_jornal", "regioes"],
    },
    "rerrolar_jornal": {
        "resumo": "Posta uma nova edição OFICIAL do jornal.",
        "staff": True,
        "uso": "/rerrolar_jornal",
        "params": [],
        "detalhes": (
            "Gera e posta uma edição **oficial** no canal de notícias. Os procurados que saírem nela ficam bloqueados pro `/procurado` "
            "até a próxima edição, e o estado é salvo pra você poder usar o `/rerrolar_variavel`.\n"
            "O jornal também sai sozinho **todo domingo às 15:00 (UTC)**."
        ),
        "ver": ["rerrolar_variavel", "testar_noticia"],
    },
    "rerrolar_variavel": {
        "resumo": "Rerrola só UMA variável (clima, procurado, mestre...) do jornal.",
        "staff": True,
        "uso": "/rerrolar_variavel mar:<região> variavel:<qual> [mensagem_id:<id ou link>]",
        "params": [
            ("mar", "Região do jornal."),
            ("variavel", "O que rerrolar (rumor, mestre, procurado, clima completo ou uma categoria de clima)."),
            ("mensagem_id", "ID ou link da mensagem a editar. Vazio = última edição oficial salva."),
        ],
        "detalhes": (
            "Edita a própria mensagem do jornal trocando só aquela variável. Ao rerrolar o **procurado**, o novo nome não pode ser "
            "quem já está na edição atual.\n"
            "Com `mensagem_id`, o bot reconstrói o que foi sorteado lendo o texto da mensagem; isso depende dos textos configurados em `/regioes` "
            "continuarem iguais aos da época. Só dá pra editar mensagens que o próprio bot postou."
        ),
        "ver": ["rerrolar_jornal", "regioes"],
    },
    "regioes": {
        "resumo": "Painel pra gerenciar as regiões do jornal.",
        "staff": True,
        "uso": "/regioes",
        "params": [],
        "detalhes": (
            "Painel com botões pra **criar e editar regiões** do jornal: locais (ilhas/rotas), grupos de template (rumores, mestre, nakama...) "
            "com variações e pesos, categorias de clima, textos de cabeçalho e menções do rodapé, e ativar/desativar uma região. "
            "Tudo é feito pelo Discord, sem mexer em código."
        ),
        "ver": ["testar_noticia", "rerrolar_jornal"],
    },
    # ------------------------------------------------------------------ outros
    "ajuda": {
        "resumo": "Explica os comandos do bot.",
        "staff": False,
        "uso": "/ajuda [comando:<nome>]",
        "params": [("comando", "Opcional: o comando que você quer entender melhor (tem autocomplete).")],
        "detalhes": "Sem argumento mostra um resumo de todos os comandos. Com um comando, mostra a explicação detalhada dele.",
        "ver": [],
    },
}
