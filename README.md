# Exportador de fotogramas de YouTube — Studio Moka

Proyecto fuente para Windows que descarga un vídeo de YouTube autorizado y exporta fotogramas JPG cada **1, 2, 4, 8 o 16 segundos**. Incluye selector de carpeta, progreso, cancelación y la identidad visual de Studio Moka.

## Requisitos

- Windows 11 de 64 bits.
- Python 3.12 de 64 bits, instalado desde `python.org` con el lanzador `py.exe`.
- Deno: `winget install DenoLand.Deno`.
- Para firmar: un certificado **RSA** de firma de código emitido por una autoridad de confianza y Windows SDK (`signtool.exe`).

## Compilar

Abre PowerShell en esta carpeta y ejecuta:

```powershell
.\build.ps1
```

El ejecutable se crea en:

```text
dist\Exportador de fotogramas de YouTube - Studio Moka.exe
```

El script crea un entorno virtual, instala versiones fijadas de las dependencias, ejecuta las pruebas y compila desde cero con PyInstaller. Deno y FFmpeg quedan incluidos en el ejecutable final.

## Firmar para Control inteligente de aplicaciones

La compilación limpia no garantiza por sí sola que Windows permita ejecutar un archivo nuevo. Para identificar a Studio Moka como publicador y mejorar la compatibilidad con Control inteligente de aplicaciones, firma el resultado con un certificado RSA confiable instalado en `Cert:\CurrentUser\My`:

```powershell
.\sign.ps1 -CertificateThumbprint "HUELLA_SHA1_DE_40_CARACTERES"
.\verify-signature.ps1
```

El nombre de empresa incluido en `version_info.txt` es únicamente metadato: **no sustituye una firma Authenticode**. No incluyas certificados, contraseñas ni archivos `.pfx` dentro del proyecto o del repositorio.

Microsoft también ofrece Trusted Signing. Consulta la documentación oficial: <https://learn.microsoft.com/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control>

## Ejecutar desde código durante el desarrollo

Después de ejecutar una vez `build.ps1`, puedes iniciar la interfaz con:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe .\src\app.py
```

## Estructura

- `src/app.py`: interfaz, descarga, progreso y exportación.
- `src/core.py`: validación, nombres seguros y comando FFmpeg.
- `assets/`: logo PNG e icono ICO de Studio Moka.
- `tests/`: pruebas automatizadas.
- `StudioMokaFrameExporter.spec`: configuración reproducible de PyInstaller.
- `build.ps1`: compilación limpia.
- `sign.ps1`: firma Authenticode por huella de certificado.
- `verify-signature.ps1`: comprobación independiente de la firma.

## Seguridad y uso

- Descarga únicamente contenido propio o para el que tengas autorización.
- No desactives Control inteligente de aplicaciones ni el antivirus para ejecutar compilaciones sin firma.
- Revisa el código y ejecuta las pruebas antes de distribuir una versión.
