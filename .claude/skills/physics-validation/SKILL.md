---
name: physics-validation
description: Cómo escribir y validar código físico en hestia_core y hestia_adapters — unidades, signos, conservación de energía y tests contra casos de referencia con tolerancias explícitas y cita. Usala al escribir o modificar cualquier cálculo térmico, orbital o radiativo.
---

# Validación de código físico

## Reglas

- **Unidades**: SI y Kelvin en todas las firmas. Sufijo de unidad en nombres no obvios (`power_w`, `area_m2`, `temperature_k`). Nunca °C fuera de la UI.
- **Signos**: documentá la convención en el docstring (ej. flujo positivo entrante al nodo).
- **Supuestos**: explicitalos en el docstring (estacionario, cuerpo gris, emisividad constante, etc.).
- **Conservación**: en redes y balances, test de que la suma de flujos cierra dentro de tolerancia.
- **Casos límite**: potencia cero, eclipse total, emisividad 0/1, β = 0 y β máximo; entradas no físicas deben fallar con error claro.
- **Determinismo**: mismas entradas → mismas salidas. Semillas fijas si hay aleatoriedad.

## Tests contra referencia

Cada función física nueva tiene al menos un test contra un valor calculado a mano o tomado de libro/norma:

```python
def test_single_node_equilibrium_temperature() -> None:
    # Reference: <autor, título, edición, ecuación/ejemplo y página>
    # Hand calculation: <expresión y valores>
    expected_k = ...
    assert result_k == pytest.approx(expected_k, rel=1e-6)  # tolerance: <por qué>
```

- Tolerancia explícita (`rel`/`abs`) y justificada en comentario.
- Citá la referencia en el test. TODO: bibliografía de referencia del proyecto (lista acordada de libros/normas ECSS).
- Tests de propiedades (monotonía, escalado, simetría) cuando aplique.

Al terminar, pedí revisión al subagente `physics-reviewer`.
