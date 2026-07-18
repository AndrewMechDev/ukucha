import { useState } from "react";
import type { ReactNode } from "react";
import StyledSelect from "../components/StyledSelect";

type SettingsCategory = "general" | "operation" | "thresholds" | "language" | "about";

function SegmentedSetting({ value, onChange }: { value: "Métrico" | "Imperial"; onChange: (value: "Métrico" | "Imperial") => void }) {
  return <div className="settings-segmented" role="group" aria-label="Sistema de unidades">{(["Métrico", "Imperial"] as const).map((item) => <button className={value === item ? "is-selected" : ""} type="button" onClick={() => onChange(item)} key={item}>{item}</button>)}</div>;
}

function SettingSection({ title, children }: { title: string; children: ReactNode }) {
  return <section className="settings-section"><h2>{title}</h2>{children}</section>;
}

export default function Settings({ onClose }: { onClose?: () => void }) {
  const [darkTheme, setDarkTheme] = useState(true);
  const [units, setUnits] = useState<"Métrico" | "Imperial">("Métrico");
  const [language, setLanguage] = useState("Español");
  const [category, setCategory] = useState<SettingsCategory>("general");

  return (
    <div className="settings-panel-backdrop" role="presentation" onClick={() => onClose?.()}>
      <section className="settings-panel-modal" role="dialog" aria-modal="true" aria-labelledby="settings-panel-title" onClick={(event) => event.stopPropagation()}>
        <header className="settings-panel-header"><div><p className="eyebrow">CONFIGURACIÓN DEL SISTEMA</p><h1 id="settings-panel-title">Ajustes</h1></div><button className="settings-panel-close" type="button" onClick={() => onClose?.()} aria-label="Cerrar ajustes"><span className="material-symbols-rounded">close</span></button></header>
        <div className="settings-panel-layout">
          <nav className="settings-category-nav" aria-label="Categorías de ajustes">
            {([
              ["general", "tune", "General"],
              ["operation", "straighten", "Operación"],
              ["thresholds", "policy", "Normativa"],
              ["language", "language", "Idioma"],
              ["about", "info", "Acerca de"],
            ] as const).map(([id, icon, label]) => <button className={category === id ? "is-active" : ""} type="button" onClick={() => setCategory(id)} key={id}><span className="material-symbols-rounded">{icon}</span><span>{label}</span></button>)}
          </nav>
          <div className="settings-panel-content">
            {category === "general" && <SettingSection title="Apariencia"><div className="settings-row"><div><strong>Tema</strong><span>Preferencia de contraste de la interfaz</span></div><div className="theme-control"><span className={!darkTheme ? "is-active" : ""}>Claro</span><button className={`settings-toggle${darkTheme ? " is-on" : ""}`} type="button" role="switch" aria-checked={darkTheme} aria-label="Cambiar tema" onClick={() => setDarkTheme((value) => !value)}><i /></button><span className={darkTheme ? "is-active" : ""}>Oscuro</span></div></div></SettingSection>}
            {category === "operation" && <SettingSection title="Unidades de medida"><div className="settings-row"><div><strong>Sistema</strong><span>Formato para distancias y lecturas</span></div><SegmentedSetting value={units} onChange={setUnits} /></div></SettingSection>}
            {category === "thresholds" && <SettingSection title="Umbrales normativos de referencia (D.S. 024-2016-EM)"><div className="settings-reference-list"><div><span>CO</span><strong>25 ppm</strong></div><div><span>H₂S</span><strong>10 ppm</strong></div><div><span>O₂ mínimo</span><strong>19.5%</strong></div><div><span>CH₄ alarma</span><strong>0.5% / 1.0%</strong></div></div><p className="settings-note">Solo referencia — no editable en esta versión</p></SettingSection>}
            {category === "language" && <SettingSection title="Idioma"><div className="settings-row"><div><strong>Idioma</strong><span>Idioma de la interfaz y mensajes del sistema</span></div><StyledSelect ariaLabel="Idioma" value={language} onChange={setLanguage} options={[{ label: "Español", value: "Español" }, { label: "English", value: "English" }]} /></div></SettingSection>}
            {category === "about" && <SettingSection title="Acerca de"><div className="settings-about"><strong>v0.1.0 · Build de hackathon</strong><p>Ukucha — asistencia SAR inspirada en la biomímesis y el trabajo de APOPO.</p></div></SettingSection>}
          </div>
        </div>
      </section>
    </div>
  );
}
