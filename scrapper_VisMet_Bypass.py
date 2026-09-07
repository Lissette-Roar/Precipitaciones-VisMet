import datetime
import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FECHA_INICIO_HISTORICO = datetime.date(2026, 8, 1)  # 01-08-2026


def obtener_ruta_archivo_anio(fecha_dt):
    """Genera la ruta del archivo CSV según el año de la fecha procesada."""
    anio = fecha_dt.year
    return os.path.join(BASE_DIR, f"origen_vismet_{anio}.csv")


def obtener_ultimas_fechas_guardadas(fecha_dt):
    """Devuelve las fechas guardadas para el año correspondiente."""
    archivo_csv = obtener_ruta_archivo_anio(fecha_dt)
    if not os.path.exists(archivo_csv):
        return set()

    try:
        df = pd.read_csv(archivo_csv, usecols=["Fecha"], encoding="utf-8-sig")
        return set(df["Fecha"].dropna().unique())
    except Exception:
        return set()


def guardar_en_csv(df, fecha_dt):
    """Anexa las filas al CSV del año correspondiente."""
    archivo_csv = obtener_ruta_archivo_anio(fecha_dt)
    hdr = not os.path.exists(archivo_csv)
    df.to_csv(
        archivo_csv,
        mode="a",
        header=hdr,
        index=False,
        encoding="utf-8-sig",
    )


def consultar_y_descargar_dia(page, fecha_datos):
    """Interactúa con el sitio web de VisMet para obtener los datos del día."""
    fecha_consulta = fecha_datos + datetime.timedelta(days=1)
    fecha_consulta_str = fecha_consulta.strftime("%d/%m/%Y")
    fecha_etiqueta_str = fecha_datos.strftime("%d-%m-%Y")

    print(
        f"\n[+] Procesando {fecha_etiqueta_str} (Formulario: {fecha_consulta_str} 0:00, 24h)..."
    )

    try:
        # 1. Asegurar pestaña Consulta
        boton_consulta = page.locator("button:has-text('Consulta')")
        if boton_consulta.is_visible():
            boton_consulta.click()
            time.sleep(0.5)

        # 2. Tipear Fecha simulando teclado
        input_fecha = None
        for inp in page.locator("input").all():
            val = inp.input_value()
            if "/" in val or inp.get_attribute("type") == "text":
                input_fecha = inp
                break

        if input_fecha:
            input_fecha.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            input_fecha.type(fecha_consulta_str, delay=100)
            page.keyboard.press("Enter")
            page.keyboard.press("Tab")
            time.sleep(0.5)

        # 3. Seleccionar Hora '0:00'
        for sel in page.locator("select").all():
            options = sel.inner_text()
            if "0:00" in options or "00:00" in options:
                try:
                    sel.select_option(label="0:00")
                except Exception:
                    sel.select_option(index=0)
                break

        # 4. Seleccionar Rango '24'
        for inp in page.locator("input").all():
            val = inp.input_value()
            if (
                val in ["1", "24", "48", "72"]
                or inp.get_attribute("type") == "number"
            ):
                inp.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                inp.type("24", delay=100)
                page.keyboard.press("Enter")
                break

        # 5. Clic en 'Ver Resultados' y esperar respuesta del servidor
        print(
            "    -> Presionando 'Ver Resultados' y esperando respuesta de datos..."
        )
        with page.expect_response(
            lambda r: "vismet.cr2.cl/api" in r.url
            or "export" in r.url
            or r.status == 200,
            timeout=15000,
        ):
            page.click("button:has-text('Ver Resultados')")

        time.sleep(3)

        # 6. Descargar el archivo CSV
        selector_csv = "text='Exportar Datos del Mapa'"
        page.wait_for_selector(selector_csv, timeout=30000)

        with page.expect_download(timeout=40000) as download_info:
            page.click(selector_csv)

        download = download_info.value
        temp_path = download.path()

        try:
            df = pd.read_csv(temp_path, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(temp_path, encoding="latin-1")

        if not df.empty and len(df.columns) > 1:
            df["Fecha"] = fecha_etiqueta_str
            return df
        else:
            print(f"    X Datos vacíos para {fecha_etiqueta_str}.")
            return None

    except Exception as e:
        print(f"    X Error en consulta para {fecha_etiqueta_str}: {e}")
        return None


def ejecutar_proceso():
    ayer = datetime.date.today() - datetime.timedelta(days=1)

    with sync_playwright() as p:
        # headless=True activado para ejecución transparente en la nube, en caso de escritorio puede ser false
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print("Navegando a VisMet...")
        page.goto("https://vismet.cr2.cl/", wait_until="networkidle")
        time.sleep(2)

        fecha_curr = FECHA_INICIO_HISTORICO
        while fecha_curr <= ayer:
            fecha_str = fecha_curr.strftime("%d-%m-%Y")
            fechas_existentes = obtener_ultimas_fechas_guardadas(fecha_curr)
            archivo_destino = os.path.basename(
                obtener_ruta_archivo_anio(fecha_curr)
            )

            if fecha_str in fechas_existentes:
                print(
                    f"✓ {fecha_str} ya existe en '{archivo_destino}'. Omitiendo..."
                )
            else:
                df_dia = consultar_y_descargar_dia(page, fecha_curr)
                if df_dia is not None and not df_dia.empty:
                    guardar_en_csv(df_dia, fecha_curr)
                    print(
                        f"    ✓ Guardadas {len(df_dia)} filas en '{archivo_destino}' para {fecha_str}"
                    )

            fecha_curr += datetime.timedelta(days=1)

        browser.close()

    print("\n--- PROCESO FINALIZADO EXITOSAMENTE ---")


if __name__ == "__main__":
    ejecutar_proceso()
