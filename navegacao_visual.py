"""
navegacao_visual.py
--------------------
GIF animado do Log Pose de 3 agulhas. O corpo, as bolhas de vidro, a argola e a
pulseira vêm de uma IMAGEM do anime (assets/logpose_base.png, já sem as agulhas);
o código só desenha por cima as 3 agulhas, o aro colorido de cada bolha e o
número da agulha.

Animação: as agulhas giram sem rumo, desaceleram, balançam e assentam apontando
pras ilhas. Ao assentar, o aro de cada bolha acende na cor do tipo
(verde = Estável, âmbar = Moderada, vermelho = Instável). Quando Totto Land é
apontada, as 3 agulhas apontam pro mesmo lado e os aros ficam rosa.

Usa Pillow. É CPU (~1-2 s): chame via asyncio.to_thread. Devolve BytesIO (GIF)
ou None se algo falhar (ex: imagem ausente) — o comando segue sem a animação.
"""

import io
import math
import os
import random

CAMINHO_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logpose_base.png")

LARG_ORIG = 700          # tamanho da imagem original
LARG_SAIDA = 520         # largura do GIF (a altura segue a proporção)
SS = 3                   # supersampling das agulhas (suaviza as bordas)

# (x, y, raio) de cada bolha na imagem original: topo, esquerda, direita
BOLHAS = ((306, 139, 115), (175, 362, 115), (454, 346, 115))

CONTORNO = (58, 42, 38)
MENTA = (196, 240, 228)
MENTA_SOMBRA = (150, 206, 196)
CARMIM = (168, 36, 92)
SOMBRA = (62, 128, 120, 150)
ARO_NEUTRO = (110, 190, 160)
CORES_TIPO = {"E": (72, 206, 120), "M": (244, 190, 56), "I": (232, 72, 66), "T": (238, 104, 164)}

_cache = {"base": None}


def _fonte(tamanho: int):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:  # Pillow antigo
        return ImageFont.load_default()


def _base():
    """Imagem do Log Pose já no tamanho de saída (carrega uma vez)."""
    if _cache["base"] is None:
        from PIL import Image
        img = Image.open(CAMINHO_BASE).convert("RGB")
        alt = round(img.height * LARG_SAIDA / img.width)
        _cache["base"] = img.resize((LARG_SAIDA, alt), Image.LANCZOS)
    return _cache["base"]


def _desenhar_bolha(frame, cx, cy, r, graus, aro, numero, brilho, fonte_cache={}):
    """Desenha o aro colorido, o número, a agulha e o pino de UMA bolha no `frame`."""
    from PIL import Image, ImageDraw
    margem = 16
    lado = int(2 * (r + margem))
    S = SS
    patch = Image.new("RGBA", (lado * S, lado * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(patch)
    c = lado * S / 2
    R = r * S

    def circ(x, y, rr, **kw):
        d.ellipse([x - rr, y - rr, x + rr, y + rr], **kw)

    # halo que se expande quando a agulha assenta
    if brilho > 0:
        rr = R * (1.0 + 0.10 * (1 - brilho)) + 2 * S
        circ(c, c, rr, outline=aro + (int(200 * brilho),), width=int(4 * S))
    # aro colorido do vidro (por dentro da borda)
    circ(c, c, R * 0.93, outline=aro + (200,), width=int(0.055 * R))

    # selo numerado, embaixo, por baixo da agulha
    if numero is not None:
        nr = 0.15 * R
        nx, ny = c, c + 0.68 * R
        circ(nx, ny, nr, fill=(20, 40, 44, 200), outline=aro + (255,), width=int(2.2 * S))
        fonte = _fonte(int(0.2 * R))
        d.text((nx, ny), str(numero), fill=(250, 250, 250, 255), font=fonte, anchor="mm")

    # agulha: losango menta na frente, ponta carmim atrás
    a = math.radians(graus)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    frente, tras, larg = 0.82 * R, 0.46 * R, 0.17 * R
    P = (c, c)
    pf = (c + ux * frente, c + uy * frente)
    pt = (c - ux * tras, c - uy * tras)
    pe = (c + vx * larg, c + vy * larg)
    pd = (c - vx * larg, c - vy * larg)

    def deslocar(pts, dx, dy):
        return [(x + dx, y + dy) for x, y in pts]

    d.polygon(deslocar([pf, pe, pt, pd], 0.06 * R, 0.08 * R), fill=SOMBRA)       # sombra no vidro
    d.polygon([pf, pe, P, pd], fill=MENTA + (255,))
    d.polygon([pf, pd, P], fill=MENTA_SOMBRA + (255,))                           # meia face em sombra
    d.polygon([pt, pe, P, pd], fill=CARMIM + (255,))
    d.line([pf, pe, pt, pd, pf], fill=CONTORNO + (255,), width=int(1.8 * S), joint="curve")
    d.line([pf, P], fill=(110, 160, 154, 255), width=int(1.0 * S))
    # pino branco
    bx, by = c + 0.13 * R, c - 0.27 * R
    d.line([P, (bx, by)], fill=(236, 240, 240, 255), width=int(2.6 * S))
    circ(bx, by, 0.085 * R, fill=(255, 255, 255, 255), outline=(150, 160, 164, 255), width=int(1 * S))

    patch = patch.resize((lado, lado), Image.LANCZOS)
    frame.alpha_composite(patch, (int(round(cx - lado / 2)), int(round(cy - lado / 2))))


def _frame(base, angulos, aros, numeros, brilho):
    frame = base.convert("RGBA")
    k = LARG_SAIDA / LARG_ORIG
    for (x, y, r), ang, aro, num in zip(BOLHAS, angulos, aros, numeros):
        _desenhar_bolha(frame, x * k, y * k, r * k, ang, aro, num, brilho)
    return frame.convert("RGB")


def gerar_gif_logpose(tipos: list, totto: bool = False, seed=None):
    """tipos: 'E'/'M'/'I' por agulha (1 a 3). Retorna BytesIO do GIF ou None."""
    try:
        from PIL import Image
        rng = random.Random(seed)
        n = max(1, min(3, len(tipos)))
        base = _base()

        if totto:
            alvo = rng.uniform(0, 360)
            finais = [alvo] * 3
            aros_finais = [CORES_TIPO["T"]] * 3
            numeros = [None] * 3
        else:
            finais = [rng.uniform(0, 360) for _ in range(3)]
            aros_finais = [CORES_TIPO.get(t, ARO_NEUTRO) for t in tipos[:3]]
            aros_finais += [ARO_NEUTRO] * (3 - len(aros_finais))
            numeros = [i + 1 if i < n else None for i in range(3)]

        voltas = [rng.choice([2, 3]) * 360 * rng.choice([1, -1]) for _ in range(3)]
        neutro = [ARO_NEUTRO] * 3
        sem_aro = [None] * 3
        frames, duracoes = [], []

        giro = 14                                 # gira e desacelera
        for f in range(giro):
            p = f / (giro - 1)
            suave = 1 - (1 - p) ** 3
            angs = [fin + (1 - suave) * v for fin, v in zip(finais, voltas)]
            frames.append(_frame(base, angs, neutro, sem_aro, 0))
            duracoes.append(45)

        balanco = 10                              # balança e assenta (como uma bússola de verdade)
        for f in range(1, balanco + 1):
            amp = 26 * math.exp(-0.32 * f)
            angs = [fin + amp * math.cos(0.95 * f + k) for k, fin in enumerate(finais)]
            frames.append(_frame(base, angs, neutro, sem_aro, 0))
            duracoes.append(55)

        for f in range(6):                        # assentou: aro acende com um pulso
            frames.append(_frame(base, finais, aros_finais, numeros, 1 - f / 5))
            duracoes.append(70)
        frames.append(_frame(base, finais, aros_finais, numeros, 0))
        duracoes.append(3500)                     # segura o resultado antes de repetir

        # paleta única (tirada do quadro final, que tem todas as cores) -> GIF menor e sem cintilar
        paleta = frames[-1].quantize(colors=250, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        frames = [fr.quantize(palette=paleta, dither=Image.Dither.NONE) for fr in frames]
        buf = io.BytesIO()
        frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:],
                       duration=duracoes, loop=0, optimize=False)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"⚠️ Não consegui gerar o GIF do Log Pose: {e}")
        return None
