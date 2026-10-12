"""PRUEBA 3 — ¿MetaBet deja leer las cuotas desde un servidor (Render)?

Programa chico, solo para la prueba. Cuando se abre la página que da Render:
abre metabet.tv con un navegador automático (sin iniciar sesión, sin apostar),
va a la liga de Bolivia y muestra lo que pudo leer, o el bloqueo que encontró.
No guarda nada y no toca el analizador de José.
"""
import html
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from playwright.sync_api import sync_playwright

URL = ("https://metabet.tv/es/sport/sports/football/bolivia/"
       "bolivia-premier-division/flt-1-1411-5346/")

LEER_JS = """() => {
  const sm = document.querySelector('sport-mobile');
  const t = sm && sm.shadowRoot ? sm.shadowRoot.textContent : '';
  return (t || '').replace(/\\s+/g, ' ').trim();
}"""


def probar():
    r = {"hora_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
         "titulo": "", "estado_http": "", "cloudflare": False,
         "texto_cuotas": "", "error": ""}
    try:
        with sync_playwright() as p:
            nav = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            pag = nav.new_page(locale="es-ES", user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"))
            resp = pag.goto(URL, wait_until="domcontentloaded", timeout=60000)
            r["estado_http"] = resp.status if resp else "sin respuesta"
            texto = ""
            for _ in range(20):          # hasta ~60 s esperando las cuotas
                pag.wait_for_timeout(3000)
                texto = pag.evaluate(LEER_JS)
                if "Resultado Final" in texto or "Empate" in texto:
                    break
            r["titulo"] = pag.title()
            cuerpo = pag.content().lower()
            r["cloudflare"] = ("just a moment" in cuerpo or "cf-challenge" in cuerpo
                               or "attention required" in cuerpo)
            i = texto.find("Bolivia. Liga Premier")
            r["texto_cuotas"] = texto[i:i + 1500] if i >= 0 else texto[:1500]
            nav.close()
    except Exception as e:  # noqa: BLE001 — en la prueba se muestra cualquier error
        r["error"] = f"{type(e).__name__}: {e}"
    return r


def pagina(r):
    hay = "Empate" in r["texto_cuotas"]
    veredicto = ("SÍ SE PUDIERON LEER CUOTAS DESDE RENDER" if hay else
                 "NO SE PUDIERON LEER CUOTAS DESDE RENDER")
    filas = "".join(f"<tr><td><b>{html.escape(k)}</b></td><td>{html.escape(str(v))}</td></tr>"
                    for k, v in r.items())
    return f"""<!doctype html><meta charset="utf-8">
<title>Prueba 3 MetaBet</title>
<h1 style="color:{'green' if hay else 'red'}">{veredicto}</h1>
<p>Página probada: {html.escape(URL)}</p>
<table border="1" cellpadding="6">{filas}</table>
<p>Recargá la página para volver a probar (tarda hasta un minuto).</p>"""


class Manejador(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/probar"):
            self.send_response(404)
            self.end_headers()
            return
        cuerpo = pagina(probar()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", "10000"))
    HTTPServer(("0.0.0.0", puerto), Manejador).serve_forever()
