# Navegação do Novo Mundo (Log Pose 3A)

Código: `cogs/navegacao.py` (comandos), `navegacao_engine.py` (regras, constantes de balanceamento no topo), `navegacao_db.py` (Google Sheets), `navegacao_dados.py` (ilhas de seed).

## Armazenamento (grátis e persistente)

Google Sheets, na mesma planilha "Procurados Blues" e com as mesmas credenciais (`credenciais.json`). Abas criadas sozinhas no primeiro uso:

| Aba | Colunas | Conteúdo |
|---|---|---|
| `NM_Ilhas` | area, nome, tipo, nota | Ilhas. Semeada uma vez a partir de `navegacao_dados.py`; depois é a fonte da verdade e pode ser editada à mão (cache de 60 s). |
| `NM_Bandos` | bando, estado (JSON), atualizado | Um bando por linha. |
| `NM_Log` | data, bando, evento, detalhe | Histórico só de anexar. |

Tipos de ilha: `inicial`, `sincronizavel`, `secreta`, `principal`, `totto` (o arquipélago), `totto_ilha` (ilhas dentro de Totto), `calm` (nota = nível 1 ou 2). Área: 1, 2, 3, 4 ou `calm`.

**Ilhas de Totto Land ainda não estão cadastradas.** Adicione linhas com área `2` e tipo `totto_ilha` em `NM_Ilhas`.

## Regras implementadas

1. Bando parte de Raijin, Risky Red ou Mystoria (`/navegacao_iniciar`).
2. `/navegar` sincroniza 3 ilhas distintas, cada agulha com tipo sorteado:
   - 🟢 Estável: CD normal, +1 progressão.
   - 🟡 Moderada: CD +2, +1,5 progressão.
   - 🔴 Instável: CD +5, **falha leva ao Calm Belt**, +3 progressões.
3. `/viajar bando agulha resultado`: o mestre informa o resultado do Teste de Navegação.
   - Sucesso: chega à ilha, ganha a progressão da agulha (área atual).
   - Falha: ilha secreta aleatória da **área atual** (sem progressão); se a agulha era Instável, ilha aleatória do **Calm Belt**. Em Totto Land não há ilha secreta: rola-se Desastre (`/encontromaritimo`).
4. Pool de sincronização: ilhas não visitadas da área atual (peso 1) e de áreas anteriores (peso `PESO_AREA_ANTERIOR` = 0,1). Ilhas de áreas ainda não exploradas nunca aparecem. Ilha visitada nunca volta.
5. Ilha principal (Dressrosa 1→2, Wano 2→3, Elbaph 3→Laugh Tale) entra no pool com 20 progressões na área (peso `PESO_PRINCIPAL` = 5). Ao chegar nela a progressão zera e a próxima área é liberada. Na área 4, Laugh Tale sempre aparece numa agulha.
6. **Totto Land** (Área 2):
   - Se uma agulha a sorteia (e o bando nunca saiu de lá), as 3 apontam pra ela. O bando vai (`/viajar`) ou espera 7 dias pra `/navegar` de novo (`forcar` ignora a espera).
   - Dentro: só ilhas `totto_ilha`, todas Estáveis, CD normal, +1 progressão cada, também contando pra área.
   - Sair: `/totto_sair` exige 5 progressões lá dentro. Depois, Totto vira ilha comum (uma agulha só) e dá pra voltar com as mesmas regras.
7. `/navegacao_ajustar` corrige área, progressão, local e flag de Totto (dessincroniza o Log Pose).

## Decisões assumidas (não vieram das regras; mude as constantes se não servir)

- Tipo da agulha: chance igual (1/3 cada), `PESOS_TIPO_AGULHA`.
- Progressão é ganha ao **chegar** na ilha. Ilhas secretas e do Calm Belt não dão progressão.
- Chegar na ilha principal e entrar em Totto Land não dão progressão.
- Calm Belt níveis 1 e 2 entram no mesmo sorteio (sem regra de nível por área).
- Hollow Horn é tratada como ilha comum da Área 2.
- "Reino Majiatsuka (área 2)" foi removido da lista da Área 1 (aparece só na Área 2).
- Nomes das ilhas principais (Dressrosa, Wano, Elbaph, Laugh Tale) foram adicionados por conta própria; não estavam nas listas.
