"""
navegacao_visual.py
--------------------
GIF animado do Log Pose de 3 agulhas (o do anime): corpo bege arredondado com
3 bolhas de vidro verde-água, uma agulha (losango menta + ponta carmim, com
pino branco) em cada bolha, argola amarela e pulseira rosa.

Animação: as agulhas giram sem rumo, desaceleram, balançam e assentam apontando
pras ilhas. Ao assentar, o aro de cada bolha acende na cor do tipo
(verde = Estável, âmbar = Moderada, vermelho = Instável). Quando Totto Land é
apontada, as 3 agulhas apontam pro mesmo lado e os aros ficam rosa.

Usa Pillow. É CPU (~1-2 s): chame via asyncio.to_thread. Devolve BytesIO (GIF)
ou None se algo falhar — o comando segue sem a animação.
"""

import io
import math
import random

LARG, ALT = 520, 440
ESC = 2  # supersampling pra suavizar as bordas

FUNDO = (22, 30, 46)
PULSEIRA = (238, 150, 150)
PULSEIRA_SOMBRA = (200, 118, 122)
CORPO = (226, 192, 150)
CORPO_CLARO = (240, 214, 176)
CORPO_ESCURO = (196, 160, 118)
CONTORNO = (58, 42, 38)
ARGOLA = (250, 214, 70)
ARGOLA_ESCURA = (214, 168, 40)
VIDRO_BORDA = (40, 88, 80)
VIDRO_CENTRO = (190, 238, 226)
VIDRO_FUNDO = (110, 196, 182)
MENTA = (196, 240, 228)
MENTA_SOMBRA = (150, 206, 196)
CARMIM = (168, 36, 92)
SOMBRA_AGULHA = (82, 158, 148)
ARO_NEUTRO = (96, 176, 150)
CORES_TIPO = {"E": (72, 206, 120), "M": (244, 190, 56), "I": (232, 72, 66), "T": (238, 104, 164)}

CENTRO = (232, 222)          # centro do corpo
RAIO_CORPO = 184
RAIO_BOLHA = 66
# posição (dx, dy) das 3 bolhas: topo, esquerda-baixo, direita-baixo
POS_BOLHAS = ((0, -96), (-86, 52), (86, 52))
COMP_FRENTE, COMP_TRAS, LARG_AGULHA = 54, 30, 18


def _s(v):
    return v * ESC


def _fonte(tamanho: int):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:  # Pillow antigo
        return ImageFont.load_default()


def _mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def _circulo(d, cx, cy, r, **kw):
    d.ellipse([_s(cx - r), _s(cy - r), _s(cx + r), _s(cy + r)], **kw)


def _fundo_estatico():
    """Pulseira, argola, corpo e bolhas (a parte que não se mexe), em alta resolução."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (_s(LARG), _s(ALT)), FUNDO)
    d = ImageDraw.Draw(img)
    cx, cy = CENTRO

    # pulseira (atrás do corpo)
    d.rounded_rectangle([_s(0), _s(cy - 52), _s(LARG), _s(cy + 58)], radius=_s(30), fill=PULSEIRA)
    d.rounded_rectangle([_s(0), _s(cy + 34), _s(LARG), _s(cy + 58)], radius=_s(24), fill=PULSEIRA_SOMBRA)

    # argola amarela, à direita (parte dela fica atrás do corpo)
    ax, ay = cx + RAIO_CORPO - 6, cy - 6
    d.ellipse([_s(ax - 34), _s(ay - 118), _s(ax + 44), _s(ay + 118)], outline=ARGOLA_ESCURA, width=_s(20))
    d.ellipse([_s(ax - 34), _s(ay - 118), _s(ax + 44), _s(ay + 118)], outline=ARGOLA, width=_s(14))
    d.arc([_s(ax - 26), _s(ay - 108), _s(ax + 36), _s(ay + 108)], 285, 345, fill=(255, 244, 190), width=_s(4))

    # corpo (esfera de madeira clara)
    _circulo(d, cx, cy + 4, RAIO_CORPO, fill=CONTORNO)
    for k in range(34):                       # gradiente radial, claro no canto superior esquerdo
        t = k / 33
        r = RAIO_CORPO - 3 - t * (RAIO_CORPO - 10)
        _circulo(d, cx - 22 * t, cy - 20 * t, r, fill=_mix(CORPO_ESCURO, CORPO_CLARO, t))
    # base do corpo (apoio)
    d.polygon([(_s(cx - 34), _s(cy + RAIO_CORPO - 4)), (_s(cx + 34), _s(cy + RAIO_CORPO - 4)),
               (_s(cx + 30), _s(cy + RAIO_CORPO + 24)), (_s(cx - 30), _s(cy + RAIO_CORPO + 24))], fill=(150, 120, 96))

    # bolhas de vidro
    for dx, dy in POS_BOLHAS:
        bx, by = cx + dx, cy + dy
        _circulo(d, bx, by, RAIO_BOLHA + 3, fill=CONTORNO)
        for k in range(26):
            t = k / 25
            r = RAIO_BOLHA - t * (RAIO_BOLHA - 8)
            _circulo(d, bx - 10 * t, by - 12 * t, r, fill=_mix(VIDRO_FUNDO, VIDRO_CENTRO, t))
        d.arc([_s(bx - RAIO_BOLHA + 10), _s(by - RAIO_BOLHA + 10), _s(bx + RAIO_BOLHA - 10), _s(by + RAIO_BOLHA - 10)],
              195, 265, fill=(244, 255, 252), width=_s(5))       # brilho do vidro
        _circulo(d, bx - 30, by - 36, 5, fill=(255, 255, 255))
    return img


def _agulha(d, px, py, graus, cor_frente=MENTA, sombra=True):
    """Losango da agulha apontando pra `graus` (0 = direita, 90 = baixo)."""
    a = math.radians(graus)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    frente = (px + ux * COMP_FRENTE, py + uy * COMP_FRENTE)
    tras = (px - ux * COMP_TRAS, py - uy * COMP_TRAS)
    e = (px + vx * LARG_AGULHA, py + vy * LARG_AGULHA)
    di = (px - vx * LARG_AGULHA, py - vy * LARG_AGULHA)

    def pts(*ps, dx=0, dy=0):
        return [(_s(x + dx), _s(y + dy)) for x, y in ps]

    if sombra:
        d.polygon(pts(frente, e, tras, di, dx=4, dy=5), fill=SOMBRA_AGULHA)
    d.polygon(pts(frente, e, (px, py), di), fill=cor_frente)            # parte menta (frente)
    d.polygon(pts(frente, di, (px, py)), fill=MENTA_SOMBRA)             # meia face em sombra
    d.polygon(pts(tras, e, (px, py), di), fill=CARMIM)                  # ponta carmim (trás)
    d.line(pts(frente, e, tras, di, frente), fill=CONTORNO, width=_s(2), joint="curve")
    d.line(pts(frente, (px, py)), fill=(120, 170, 164), width=_s(1))


def _pino(d, px, py):
    d.line([(_s(px), _s(py)), (_s(px + 9), _s(py - 18))], fill=(236, 240, 240), width=_s(3))
    _circulo(d, px + 9, py - 19, 6, fill=(255, 255, 255), outline=(150, 160, 164), width=_s(1))


def _frame(base, angulos, aros, numeros, brilho):
    """angulos: 3 ângulos; aros: 3 cores de aro; numeros: 3 rótulos (ou None);
    brilho: 0..1 intensidade do pulso de luz do aro (quando a agulha assenta)."""
    from PIL import Image, ImageDraw
    img = base.copy()
    d = ImageDraw.Draw(img)
    cx, cy = CENTRO
    fonte = _fonte(_s(14))

    for (dx, dy), ang, aro, num in zip(POS_BOLHAS, angulos, aros, numeros):
        bx, by = cx + dx, cy + dy
        if brilho > 0:                                           # halo que se expande
            r = RAIO_BOLHA + 2 + 12 * brilho
            _circulo(d, bx, by, r, outline=_mix(aro, FUNDO, brilho * 0.7), width=_s(3))
        _circulo(d, bx, by, RAIO_BOLHA - 2, outline=aro, width=_s(5))   # aro colorido do vidro
        _agulha(d, bx, by, ang)
        _pino(d, bx, by)
        if num is not None:                                      # selo numerado, do lado de fora da bolha
            nx, ny = bx + dx * 0.0, by
            # direção radial a partir do centro do corpo
            ux, uy = (dx, dy)
            n = math.hypot(ux, uy) or 1
            sx, sy = bx + ux / n * (RAIO_BOLHA + 12), by + uy / n * (RAIO_BOLHA + 12)
            _circulo(d, sx, sy, 13, fill=FUNDO, outline=aro, width=_s(3))
            d.text((_s(sx), _s(sy)), str(num), fill=(250, 250, 250), font=fonte, anchor="mm")
    return img.resize((LARG, ALT), Image.LANCZOS)


def gerar_gif_logpose(tipos: list, totto: bool = False, seed=None):
    """tipos: 'E'/'M'/'I' por agulha (1 a 3). Retorna BytesIO do GIF ou None."""
    try:
        from PIL import Image
        rng = random.Random(seed)
        n = max(1, min(3, len(tipos)))
        base = _fundo_estatico()

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
        frames, duracoes = [], []

        giro = 14                                 # gira e desacelera
        for f in range(giro):
            p = f / (giro - 1)
            suave = 1 - (1 - p) ** 3
            angs = [fin + (1 - suave) * v for fin, v in zip(finais, voltas)]
            frames.append(_frame(base, angs, neutro, [None] * 3, 0))
            duracoes.append(45)

        balanco = 10                              # balança e assenta (como uma bússola de verdade)
        for f in range(1, balanco + 1):
            amp = 26 * math.exp(-0.32 * f)
            angs = [fin + amp * math.cos(0.95 * f + k) for k, fin in enumerate(finais)]
            frames.append(_frame(base, angs, neutro, [None] * 3, 0))
            duracoes.append(55)

        for f in range(6):                        # assentou: aro acende com um pulso
            brilho = 1 - f / 5
            frames.append(_frame(base, finais, aros_finais, numeros, brilho))
            duracoes.append(70)
        frames.append(_frame(base, finais, aros_finais, numeros, 0))
        duracoes.append(3500)                     # segura o resultado antes de repetir

        frames = [fr.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for fr in frames]
        buf = io.BytesIO()
        frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:],
                       duration=duracoes, loop=0, optimize=False, disposal=2)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"⚠️ Não consegui gerar o GIF do Log Pose: {e}")
        return None
