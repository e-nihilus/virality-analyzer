# Fase 14 IA - Tareas Manuales Para Completar Integracion Real

Este documento lista solo las tareas manuales para pasar de la arquitectura preparada (adapters + feature flags + fallback) a integracion real de modelos en Fase 14.

## Estado actual

La arquitectura ya esta lista con:

- `VisualAnalyzerAdapter` (`heuristic` / `yolo`)
- `EmotionAnalyzerAdapter` (`heuristic` / `deepface`)
- `TemporalAnalyzerAdapter` (`heuristic` / `videomae`)
- `ExplanationGenerator` (`heuristic` / `qwen`) con cache en memoria
- Feature flags y fallback automatico si faltan dependencias

## 1. Preparacion del entorno Python

1. Activar entorno virtual.
2. Verificar version de Python (`3.11+`).
3. Actualizar `pip`.

Comandos tipicos (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
```

## 2. Instalar dependencias por provider

Instala solo lo que quieras activar.

### 2.1 YOLOv8 (Fase 14.1)

```powershell
pip install ultralytics
```

### 2.2 DeepFace (Fase 14.2)

```powershell
pip install deepface
```

Nota: `deepface` puede requerir backend de DL (TensorFlow/Keras segun version).

### 2.3 VideoMAE (Fase 14.3)

```powershell
pip install torch transformers
```

### 2.4 Qwen2.5-VL (Fase 14.4)

```powershell
pip install torch transformers
```

## 3. Variables de entorno a configurar

Puedes usar variables normales o con prefijo `AUREA_`.

### 3.1 Visual

- `VISUAL_ANALYZER_PROVIDER=heuristic|yolo`

### 3.2 Emotion

- `EMOTION_ANALYZER_PROVIDER=heuristic|deepface`

### 3.3 Temporal

- `ENABLE_TEMPORAL_ANALYSIS=true|false`
- `TEMPORAL_ANALYZER_PROVIDER=heuristic|videomae`

### 3.4 Explanation

- `EXPLANATION_PROVIDER=heuristic|qwen`
- `EXPLANATION_CACHE_ENABLED=true|false`

Ejemplo (PowerShell):

```powershell
$env:VISUAL_ANALYZER_PROVIDER = "yolo"
$env:EMOTION_ANALYZER_PROVIDER = "deepface"
$env:ENABLE_TEMPORAL_ANALYSIS = "true"
$env:TEMPORAL_ANALYZER_PROVIDER = "videomae"
$env:EXPLANATION_PROVIDER = "qwen"
$env:EXPLANATION_CACHE_ENABLED = "true"
```

## 4. Descarga de modelos/pesos (manual)

Debes decidir y gestionar manualmente:

1. Modelo concreto por provider.
2. Ruta de almacenamiento de pesos.
3. Versionado de modelos para reproducibilidad.

## 5. Pendiente para inferencia real

Todavia falta implementar en codigo:

1. Inference real en `YoloVisualAnalyzer`.
2. Inference real en `DeepFaceEmotionAnalyzer`.
3. Inference real en `VideoMAETemporalAnalyzer`.
4. Inference real en `QwenExplanationGenerator`.

## 6. Validacion manual recomendada

### 6.1 Imports

```powershell
python -c "import ultralytics; print('yolo ok')"
python -c "import deepface; print('deepface ok')"
python -c "import torch, transformers; print('videomae/qwen deps ok')"
```

### 6.2 Checklist funcional

1. `status=completed` en analisis.
2. Contrato JSON intacto.
3. `action_recognition_score` solo si temporal esta habilitado.
4. Qwen no modifica scores de viralidad.

## 7. Requisitos de sistema (GPU opcional)

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

## 8. Ubuntu (copy/paste rapido)

Ejecuta esto en tu servidor Ubuntu despues de `git pull`:

```bash
set -e

# 1) Paquetes de sistema
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip \
  ffmpeg git curl \
  libgl1 libglib2.0-0

# 2) Entrar al repo
cd /ruta/a/virality-analizer

# 3) Entorno virtual
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# 4) Dependencias base del backend
pip install -e backend

# 5) Dependencias Fase 14 (providers)
pip install ultralytics deepface torch transformers

# 6) Smoke test de imports
python -c "import ultralytics; print('yolo ok')"
python -c "import deepface; print('deepface ok')"
python -c "import torch, transformers; print('videomae/qwen deps ok')"

# 7) Feature flags (sesion actual)
export VISUAL_ANALYZER_PROVIDER=yolo
export EMOTION_ANALYZER_PROVIDER=deepface
export ENABLE_TEMPORAL_ANALYSIS=true
export TEMPORAL_ANALYZER_PROVIDER=videomae
export EXPLANATION_PROVIDER=qwen
export EXPLANATION_CACHE_ENABLED=true

# 8) Levantar backend
uvicorn app.main:app --reload --app-dir backend
```

Verificacion minima en otra terminal:

```bash
curl http://127.0.0.1:8000/api/viral-intelligence/health
curl http://127.0.0.1:8000/api/viral-intelligence/analysis/mock
```

Si quieres variables persistentes, agregalas en `~/.bashrc`.

## 9. Nota final importante

Aunque instales todo y actives flags, los providers de Fase 14 siguen en modo placeholder hasta implementar inferencia real en cada adapter. El sistema seguira funcionando por fallback heuristico sin romper el pipeline.
