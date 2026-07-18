import { useNavigate } from "react-router-dom";

export default function Copilot() {
  const navigate = useNavigate();

  return (
    <div className="timeline-mobile-screen">
      <div className="timeline-mobile-sheet copilot-mobile-sheet">
        <div className="timeline-drag-handle" aria-hidden="true" />
        <header className="timeline-mobile-header">
          <div><p className="eyebrow">ASISTENCIA SINTÉTICA</p><h1>Copiloto IA <span>· Ukucha-03</span></h1></div>
          <button type="button" className="timeline-close" onClick={() => navigate(-1)} aria-label="Cerrar Copiloto">×</button>
        </header>
        <div className="copilot-mobile-content">
          <article><time>10:21:58</time><p>Zona 3: O₂ al 19.6%, cerca del límite legal. Prioridad alta.</p></article>
          <article><time>10:22:06</time><p>Persona detectada a 12 m. Recomiendo mantener el canal de voz abierto.</p></article>
          <article><time>10:22:14</time><p>Ruta despejada hacia el punto de extracción norte.</p></article>
          <label><input placeholder="Preguntar al copiloto..." /><span>↵</span></label>
        </div>
      </div>
    </div>
  );
}
