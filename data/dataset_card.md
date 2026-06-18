# Dataset Card — Aurea Viral Intelligence V2

## Propósito

Dataset offline para entrenar modelos de retención y viralidad a partir de
features multimodales por ventana (`features/multimodal_windows.npz`) y labels de
engagement reales.

## Unidad de entrenamiento

- Entrada `x`: embedding multimodal por ventana temporal.
- Ventanas: 3s, stride 1s, generadas por la Fase 1.
- Salida `y`: labels de engagement de vídeo repetidos/alineados por ventana +
  `window_retention` derivado de `retention_curve` cuando exista.

## Columnas de labels

- `watch_time_ratio`
- `shares_rate`
- `saves_rate`
- `rewatch_rate`
- `retention_score`
- `hook_strength`
- `shareability`
- `novelty`
- `ragebait`
- `memeability`
- `window_retention`

Todos los scores deben estar en `[0, 1]`. Labels faltantes se codifican como
`NaN` para permitir entrenamiento multi-task con máscaras.

## Fuentes permitidas

Solo deben incluirse datos obtenidos legalmente, por ejemplo:

- APIs oficiales de la plataforma, respetando ToS.
- Exportes de analíticas de cuentas propias o con autorización.
- Logs internos de productos donde exista consentimiento y base legal.
- Datasets públicos con licencia compatible.

No se deben incluir vídeos/analíticas scrapeados sin permiso ni datos personales
no necesarios para el objetivo de entrenamiento.

## Privacidad y cumplimiento

- No almacenar PII si no es estrictamente necesaria.
- Remover identificadores directos de usuarios finales.
- Documentar base legal/consentimiento por fuente.
- Respetar GDPR/CCPA y políticas de cada plataforma.

## Sesgos esperados

- Sesgo de plataforma: métricas no son comparables directamente entre TikTok,
  Instagram, YouTube Shorts, etc.
- Sesgo de nicho/idioma: rendimiento puede variar por comunidad y lengua.
- Sesgo temporal: formatos virales cambian con tendencias.
- Sesgo de cuenta: audiencia previa del creador puede dominar el engagement.

## Construcción

1. Ejecutar análisis para generar features por `analysis_id`.
2. Preparar labels en CSV/JSONL según `data/schema.py`.
3. Opcionalmente normalizar exports propios:

```bash
python -m data.collectors.local_exports raw_export.csv data/labels.jsonl
```

4. Construir dataset:

```bash
python data/build_dataset.py --labels data/labels.jsonl --output data/datasets/v1
```

5. Validar:

```bash
python data/build_dataset.py --labels data/labels.jsonl --output data/datasets/v1 --check
```

Sin datos reales aún, la validación del tooling puede ejecutarse con:

```bash
python data/build_dataset.py --check
```
