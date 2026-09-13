"""
permissoes.py
--------------
Checagem de cargo compartilhada entre jornal.py e regioes_admin.py,
para não duplicar a lista de cargos permitidos em dois lugares.
"""

import discord
from discord import app_commands

CARGOS_PERMITIDOS_IDs = {
    1405643389105606767,  # Dev's
    1227977596671885393,  # Supervisores
    1222232432527413389,  # Moderadores
    1475504976037154959,  # P3rcy
}


def usuario_permitido(interaction: discord.Interaction) -> bool:
    user_role_ids = {role.id for role in interaction.user.roles}
    return bool(user_role_ids.intersection(CARGOS_PERMITIDOS_IDs))


def is_allowed_role():
    def predicate(interaction: discord.Interaction) -> bool:
        return usuario_permitido(interaction)
    return app_commands.check(predicate)
