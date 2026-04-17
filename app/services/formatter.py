from __future__ import annotations

from app.schemas.domain import ResultadoFinal


def format_resultado_final(resultado: ResultadoFinal) -> str:
    lines = ["Comparacion completada con evidencia.", ""]
    lines.append("Diferencias:")
    lines.extend([f"- {item}" for item in resultado.diferencias] or ["- Sin diferencias concluyentes."])
    lines.append("")
    lines.append("Similitudes:")
    lines.extend([f"- {item}" for item in resultado.similitudes] or ["- Sin similitudes concluyentes."])
    lines.append("")
    lines.append("Ventajas:")
    lines.extend([f"- {item}" for item in resultado.ventajas] or ["- Sin ventajas concluyentes."])
    lines.append("")
    lines.append("Desventajas:")
    lines.extend([f"- {item}" for item in resultado.desventajas] or ["- Sin desventajas concluyentes."])
    lines.append("")
    lines.append("Conclusion:")
    lines.append(resultado.conclusion or "No fue posible generar una conclusion con la evidencia disponible.")
    if resultado.score_simple:
        lines.append("")
        lines.append("Score simple (alto=3, medio=2, bajo=1):")
        for provider, score in resultado.score_simple.items():
            lines.append(f"- {provider}: {score}")
    return "\n".join(lines)
