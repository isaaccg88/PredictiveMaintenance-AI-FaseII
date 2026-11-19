# Fairness operacional en tres tipos de máquina

**Dato 100% sintético. No es fairness demográfica.**

| Tipo | Máquinas | Ventanas | Positivas | TPR/Recall | FPR | Precision | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 4 | 1639 | 142 | 0.725 | 0.030 | 0.696 | 0.963 |
| B | 4 | 1625 | 156 | 0.801 | 0.026 | 0.767 | 0.968 |
| C | 4 | 1632 | 144 | 0.819 | 0.033 | 0.707 | 0.964 |

**Brecha TPR entre tipos:** 0.094 (máximo − mínimo).
**Brecha FPR entre tipos:** 0.007 (máximo − mínimo).

**Interpretación:** la equidad operacional aquí evalúa paridad de detección por tipo de equipo. No prueba ausencia de sesgo en máquinas industriales reales.
Los cuatro equipos por subgrupo limitan inferencia estadística; requieren más unidades independientes y etiquetas maduras.
Se propone revisión técnica si la brecha TPR >0.10; este umbral es una política propuesta, no una norma legal.
