# underwritinggit (SAT + Buró)

Este repo contiene **solo** las pestañas de **SAT** y **Buró (UW)**, separadas del proyecto original.

## 1) Requisitos
- Python 3.10+

## 2) Ejecutar localmente
```bash
# 1) crear entorno
python -m venv .venv

# 2) activar
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

# 3) instalar deps
pip install -r requirements.txt

# 4) crear secrets
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# 5) editar .streamlit/secrets.toml y poner:
# - SYNTAGE_API_KEY
# - MOFFIN_TOKEN
# - [auth].users

# 6) correr
streamlit run app.py
```

## 3) Crear usuarios (login)
Este proyecto usa un login simple (usuario/contraseña) con hashes **bcrypt** guardados en `st.secrets`.

Genera el hash así:
```bash
python scripts/create_user.py carlos "MiPasswordSegura123"
```
Luego copia la línea que imprime y pégala dentro de:

`.streamlit/secrets.toml`
```toml
[auth]
users = {
  "carlos" = "$2b$12$...",
  "otro" = "$2b$12$..."
}
```

## 4) Subir a GitHub (repo público)
1. Crea un repo vacío en GitHub.
2. En tu máquina:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <TU_URL>
git push -u origin main
```

**Importante:**
- No subas `.streamlit/secrets.toml` ni `.env` (ya están en `.gitignore`).

## 5) Deploy
Si lo vas a desplegar en **Streamlit Community Cloud** (u otro servicio):
- Agrega los valores de `SYNTAGE_API_KEY`, `MOFFIN_TOKEN` y el bloque `[auth]` como **Secrets** del deployment.
- El repo puede ser público, pero el acceso queda restringido por el login.

## 6) Variables necesarias
- `SYNTAGE_API_KEY`: API key para Syntage
- `SYNTAGE_BASE_URL` (opcional): default `https://api.syntage.com`
- `MOFFIN_TOKEN`: token para Moffin

## 7) Estructura
- `app.py`: Streamlit app (router SAT/Buró + login)
- `auth.py`: login basado en `st.secrets["auth"]["users"]`
- `src/underwriting/...`: servicios (SAT y Buró) y dependencias mínimas
