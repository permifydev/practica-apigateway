# Formato de fechas del panel: corto y numerico en todas las tablas y fichas
# (ej. 08-10-2026 y 08-10-2026 13:16), en vez de "8 de octubre de 2026 a las 13:16".
# Las horas se muestran en hora de Chile (TIME_ZONE en settings.py).
DATE_FORMAT = "d-m-Y"
DATETIME_FORMAT = "d-m-Y H:i"
SHORT_DATE_FORMAT = "d-m-Y"
SHORT_DATETIME_FORMAT = "d-m-Y H:i"
TIME_FORMAT = "H:i"
YEAR_MONTH_FORMAT = "F Y"
MONTH_DAY_FORMAT = "j \\d\\e F"
FIRST_DAY_OF_WEEK = 1  # lunes
# Para escribir fechas en los formularios (ej. el mes de una venta)
DATE_INPUT_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]
DATETIME_INPUT_FORMATS = ["%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
