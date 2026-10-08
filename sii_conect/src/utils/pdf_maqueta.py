"""PDF MAQUETA de una boleta (no es un documento del SII).

Se usa mientras no hay creditos en apigateway.cl: genera un PDF simple de una
pagina con los datos de la boleta, que se guarda en Storage igual que un PDF
real ({usuario_id}/{boleta_id}.pdf) y se anota en boletas.pdf_path.

Hecho con Python puro (sin librerias extra), asi no hay que instalar nada en
Render. No incluye RUT (se protegen).
"""


def _clp(valor) -> str:
    try:
        return "$" + f"{float(valor or 0):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def _texto_pdf(texto: str) -> str:
    """Escapa un texto para usarlo dentro de ( ) en un PDF (latin-1)."""
    t = str(texto).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return t.encode("latin-1", "replace").decode("latin-1")


def generar_pdf_maqueta(titulo: str, datos: list[tuple[str, str]]) -> bytes:
    """Devuelve los bytes de un PDF de 1 pagina (carta) con:
      - aviso grande: PDF MAQUETA - NO ES UN DOCUMENTO DEL SII
      - titulo (ej. 'BOLETA DEMO 1')
      - una fila 'Etiqueta: valor' por cada elemento de 'datos'."""
    ancho, alto = 612, 792
    ops = []

    # Marco y franja del aviso
    ops.append("0.8 w 40 40 532 712 re S")
    ops.append("0.92 g 40 690 532 62 re f 0 g")
    ops.append(f"BT /F2 18 Tf 60 726 Td ({_texto_pdf('PDF MAQUETA - NO ES UN DOCUMENTO DEL SII')}) Tj ET")
    ops.append(f"BT /F1 10 Tf 60 704 Td ({_texto_pdf('Documento de demostracion generado por SII Connect. Sin validez tributaria.')}) Tj ET")

    # Titulo
    ops.append(f"BT /F2 22 Tf 60 640 Td ({_texto_pdf(titulo)}) Tj ET")
    ops.append("0.5 w 60 628 m 552 628 l S")

    # Datos
    y = 596
    for etiqueta, valor in datos:
        ops.append(f"BT /F2 12 Tf 60 {y} Td ({_texto_pdf(etiqueta)}) Tj ET")
        ops.append(f"BT /F1 12 Tf 220 {y} Td ({_texto_pdf(valor)}) Tj ET")
        y -= 26

    # Pie
    ops.append(f"BT /F1 9 Tf 60 60 Td ({_texto_pdf('Este archivo es una maqueta para pruebas. No reemplaza la boleta oficial emitida en el SII.')}) Tj ET")

    contenido = "\n".join(ops).encode("latin-1")

    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {ancho} {alto}] "
         f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>").encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(contenido)).encode() + b" >>\nstream\n" + contenido + b"\nendstream",
    ]

    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones = []
    for i, obj in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for pos in posiciones:
        salida += f"{pos:010d} 00000 n \n".encode()
    salida += (f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
               f"startxref\n{inicio_xref}\n%%EOF\n").encode()
    return bytes(salida)


def pdf_maqueta_boleta(titulo: str, boleta: dict, emisor_nombre: str, receptor_nombre: str) -> bytes:
    """Arma la maqueta con los datos de una fila de 'boletas' (sin RUT)."""
    fecha = str(boleta.get("fecha_emision") or "")[:10]
    if len(fecha) == 10 and fecha[4] == "-":
        fecha = f"{fecha[8:10]}-{fecha[5:7]}-{fecha[0:4]}"
    tasa = boleta.get("tasa_retencion")
    tasa_txt = f"{float(tasa) * 100:.2f}%".replace(".", ",") if tasa is not None else "---"
    datos = [
        ("Folio", str(boleta.get("folio_sii") or "---")),
        ("Fecha de emision", fecha or "---"),
        ("Emisor", emisor_nombre or "---"),
        ("Receptor", receptor_nombre or "---"),
        ("Descripcion", str(boleta.get("descripcion") or "---")),
        ("Monto bruto", _clp(boleta.get("monto_bruto"))),
        ("Retencion", f"{_clp(boleta.get('monto_retenido'))} ({tasa_txt})"),
        ("Monto liquido", _clp(boleta.get("monto_liquido"))),
        ("Estado", str(boleta.get("estado") or "---").capitalize()),
    ]
    return generar_pdf_maqueta(titulo, datos)
