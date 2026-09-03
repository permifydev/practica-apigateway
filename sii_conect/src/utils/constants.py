# Paleta de colores
NAVY = "#0A1F44"
NAVY_DARK = "#081833"
BG = "#F1F3F6"
GREEN = "#1E8E5A"
ORANGE = "#E8A33D"
BLUE = "#2F5FD6"
PURPLE = "#7C4DFF"
RED_BG = "#FDE7E7"
RED_TEXT = "#D14343"
YELLOW_BG = "#FCF0D8"
YELLOW_TEXT = "#B5790E"
GREY_TEXT = "#6B7280"
MENU_HOVER_BG = "#1AFFFFFF"
MENU_ACTIVE_BG = "#16295C"

# Diseño y cálculo
CARD_RADIUS = 16

# Tasa de retención legal por año (cronograma de aumento gradual hasta 17% en 2028).
# El SII siempre calcula con la tasa oficial vigente al emitir; esta tabla es solo
# para que la app muestre una vista previa correcta del monto líquido antes de emitir.
# IMPORTANTE: actualizar cuando el SII publique la tasa de años posteriores a 2028.
TASA_RETENCION_POR_ANIO = {
    2020: 0.1075, 2021: 0.1150, 2022: 0.1225, 2023: 0.1300,
    2024: 0.1375, 2025: 0.1450, 2026: 0.1525, 2027: 0.1600, 2028: 0.1700,
}


def tasa_retencion_vigente(anio: int | None = None) -> float:
    """Devuelve la tasa de retención legal para el año indicado (o el actual si se omite).
    Si el año es posterior al último definido en la tabla, usa la última tasa conocida (17%)."""
    import datetime
    anio = anio or datetime.date.today().year
    if anio in TASA_RETENCION_POR_ANIO:
        return TASA_RETENCION_POR_ANIO[anio]
    ultimo_anio = max(TASA_RETENCION_POR_ANIO)
    return TASA_RETENCION_POR_ANIO[ultimo_anio]