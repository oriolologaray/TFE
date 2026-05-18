# Setup — Datasets y Notebooks (Python)

## Instalación

### Requisitos previos

- Python 3.11 o superior
- `pip`

### 1. Crear entorno virtual (recomendado)

```bash
python -m venv .venv
source .venv/bin/activate # macOS / Linux
.venv\Scripts\activate # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

Dependencias incluidas:

| Paquete | Versión mínima | Uso |
|---|---|---|
| `requests` | 2.32 | Descarga de datos StatsBomb |
| `pandas` | 2.2 | Manipulación del dataset |
| `numpy` | 1.26 | Operaciones numéricas |
| `tqdm` | 4.67 | Barras de progreso |
| `pyarrow` | 17.0 | Backend de lectura/escritura CSV eficiente |
| `scikit-learn` | 1.5 | Modelado (fases posteriores) |
| `matplotlib` | 3.9 | Visualizaciones |
| `seaborn` | 0.13 | Visualizaciones estadísticas |
| `jupyter` | 1.1 | Ejecución de notebooks |
| `ipykernel` | 6.29 | Kernel de Python para Jupyter |

---

## Uso

### Generar el dataset

Ejecutar siempre desde la carpeta `datasets/`:

```bash
cd datasets
python build_dataset.py
```

Descarga todos los partidos de [StatsBomb Open Data](https://github.com/statsbomb/open-data) y guarda el resultado en `datasets/statsbomb_events.csv`.

### Ejecutar el EDA

```bash
jupyter notebook notebooks/eda.ipynb
```

O abrir `notebooks/eda.ipynb` directamente desde VS Code con la extensión de Jupyter.

El notebook carga el CSV desde `../datasets/statsbomb_events.csv`.
