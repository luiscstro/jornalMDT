# Regras do Jornal

Fonte de verdade: `regioes_engine.py` + `regioes_db.py`. Tudo abaixo é configurável em `/regioes`, exceto onde indicado.

## Regiões

- Cada região tem: nome, `rotulo_local` (ex: "ilha", "rota"), ordem, ativa.
- Interruptores: `tem_clima`, `tem_procurado`, `locais_unicos_por_grupo`.
- `mencoes_texto` vai no rodapé (ex: `||<@&cargo>||`).
- Templates de texto: cabeçalho (`{teste}` e `{regiao}`), introdução, título do clima, textos do procurado (pirata, marinheiro, vazio).
- Região inativa não entra no boletim nem no `/procurado`.

## Seed inicial (só se `regioes.db` estiver vazio)

- East, South, North e West Blue: ~16 ilhas cada, clima, rumores, mestre, nakama, procurado.
- Paradise: rotas (Vermelha, Laranja, Azul, Verde, Amarela, Rosa, Branca), tesouro e procurado garantido, sem clima, com locais únicos por linha.
- Menções de rodapé só no West Blue e em Paradise.

## Sorteio de cada boletim

1. **Grupos de template** (ordem do grupo). Se `usa_local` e o texto tem `{local}`, sorteia um local da região.
   - Peso: `sortear_com_peso` usa o campo `peso` de cada variação.
   - Se `locais_unicos_por_grupo`, não repete local dentro do mesmo boletim (permite repetir só se acabarem).
2. **Procurado** (se `tem_procurado`): pega o primeiro do pool embaralhado (`pop`), sorteia um local. Marinheiro usa o texto de marinheiro; pirata usa o de pirata (com nome em maiúsculas). Pool vazio → texto de "vazio".
   - O pool é compartilhado entre regiões, então um nome não repete na mesma edição.
3. **Clima** (se `tem_clima`): cada categoria sorteia uma opção por peso. Título do clima só aparece se houver categoria com opção.

Ordem de renderização: cabeçalho → introdução → itens → clima → menções.

## Pesos

Peso é relativo: a porcentagem é `peso / soma_dos_pesos`. Peso 1 em todas = chances iguais. A UI mostra as porcentagens calculadas.

## Edição oficial × teste

- `/testar_noticia`: `teste=True`, título com `[TESTE]`, **não** trava procurados nem grava edição.
- `/rerrolar_jornal` e loop semanal: `teste=False`, gravam `jornal_atual` (nomes bloqueados) e `edicao_atual`.

## /rerrolar_variavel

- Parâmetros: `mar`, `variavel`, `mensagem_id` (opcional, ID ou link).
- Sem `mensagem_id`: usa a edição oficial salva para aquela região.
- Com `mensagem_id`: busca a mensagem, confirma que foi o bot que postou, e reconstrói o estado comparando as linhas com os templates **atuais**. Linhas não reconhecidas viram "(linha não reconhecida)" e não podem ser rerroladas.
- Variáveis: cada grupo de template, `procurado`, `clima` (todas as categorias) e cada `clima:<categoria>`.
- Ao rerrolar `procurado`, o pool exclui quem já está na edição atual e o procurado trocado.
- Edições `[TESTE]` não atualizam o registro oficial.

## Caça (`/procurado`) e travas

- Ver `REGRAS_SISTEMAS.md`.
- Nomes da edição atual do jornal ficam bloqueados para caça.
