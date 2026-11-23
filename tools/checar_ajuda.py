"""
Confere se o /ajuda (ajuda_dados.py) está em dia com os comandos reais dos cogs:
lista comandos sem texto de ajuda, textos sobrando e divergência de "só staff".
Uso: python tools/checar_ajuda.py   (sai com código 1 se algo estiver fora de dia)
"""

import ast
import glob
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from ajuda_dados import CATEGORIAS, COMANDOS  # noqa: E402


def comandos_reais() -> dict:
    """{nome: só_staff} lidos do código (sem importar os cogs)."""
    reais = {}
    for arquivo in glob.glob(os.path.join(RAIZ, "cogs", "*.py")):
        with open(arquivo, encoding="utf-8") as f:
            arvore = ast.parse(f.read())
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            nome, staff = None, False
            for d in no.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "command":
                    nome = next((k.value.value for k in d.keywords if k.arg == "name"), nome)
                if isinstance(d, ast.Call) and getattr(d.func, "id", "") == "is_allowed_role":
                    staff = True
            if nome:
                reais[nome] = staff
    return reais


def main() -> int:
    reais = comandos_reais()
    categorizados = {n for _, nomes in CATEGORIAS for n in nomes}
    problemas = []
    problemas += [f"sem texto de ajuda: /{n}" for n in sorted(set(reais) - set(COMANDOS))]
    problemas += [f"ajuda de comando que não existe: /{n}" for n in sorted(set(COMANDOS) - set(reais))]
    problemas += [f"/{n}: staff={COMANDOS[n]['staff']} na ajuda, mas {reais[n]} no código"
                  for n in reais if n in COMANDOS and COMANDOS[n]["staff"] != reais[n]]
    problemas += [f"fora de categoria: /{n}" for n in sorted(set(COMANDOS) - categorizados)]
    problemas += [f"/{n}: 'ver' aponta pra /{v}, que não existe"
                  for n, c in COMANDOS.items() for v in c["ver"] if v not in COMANDOS]
    if problemas:
        print("\n".join(problemas))
        return 1
    print(f"OK: {len(reais)} comandos com ajuda em dia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
