import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import StyledSelect from "../components/StyledSelect";
import PanelModal from "../components/PanelModal";
import { useLanguage, type Language } from "../components/LanguageContext";

type SettingsCategory = "general" | "operation" | "thresholds" | "language" | "about";

function SegmentedSetting({ value, onChange }: { value: "Métrico" | "Imperial"; onChange: (value: "Métrico" | "Imperial") => void }) {
  const { t } = useLanguage();
  return (
    <div className="settings-segmented" role="group" aria-label="Sistema de unidades">
      {(["Métrico", "Imperial"] as const).map((item) => (
        <button
          className={value === item ? "is-selected" : ""}
          type="button"
          onClick={() => onChange(item)}
          key={item}
        >
          {item === "Métrico" ? t("metrico") : t("imperial")}
        </button>
      ))}
    </div>
  );
}

function SettingSection({ title, children }: { title: string; children: ReactNode }) {
  return <section className="settings-section"><h2>{title}</h2>{children}</section>;
}

export default function Settings({ onClose }: { onClose?: () => void }) {
  const { language, setLanguage, t } = useLanguage();
  const [darkTheme, setDarkTheme] = useState(() => {
    return localStorage.getItem("theme") !== "light";
  });
  const [units, setUnits] = useState<"Métrico" | "Imperial">("Métrico");
  const [category, setCategory] = useState<SettingsCategory>("general");

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  useEffect(() => {
    if (darkTheme) {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.setAttribute("data-theme", "light");
      localStorage.setItem("theme", "light");
    }
  }, [darkTheme]);

  return (
    <PanelModal
      eyebrow={t("configuracion_del_sistema")}
      title={t("ajustes")}
      titleId="settings-panel-title"
      onClose={() => onClose?.()}
      className="settings-panel-modal"
    >
      <div className="settings-panel-layout">
        <nav className="settings-category-nav" aria-label="Categorías de ajustes">
          {([
            ["general", "tune", t("general")],
            ["operation", "straighten", t("operacion")],
            ["thresholds", "policy", t("normativa")],
            ["language", "language", t("idioma")],
            ["about", "info", t("acerca_de")],
          ] as const).map(([id, icon, label]) => (
            <button
              className={category === id ? "is-active" : ""}
              type="button"
              onClick={() => setCategory(id)}
              key={id}
            >
              <span className="material-symbols-rounded">{icon}</span>
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="settings-panel-content">
          {category === "general" && (
            <SettingSection title={t("apariencia")}>
              <div className="settings-row">
                <div>
                  <strong>{t("tema")}</strong>
                  <span>{t("pref_contraste")}</span>
                </div>
                <div className="theme-control">
                  <span className={!darkTheme ? "is-active" : ""}>{t("claro")}</span>
                  <button
                    className={`settings-toggle${darkTheme ? " is-on" : ""}`}
                    type="button"
                    role="switch"
                    aria-checked={darkTheme}
                    aria-label="Cambiar tema"
                    onClick={() => setDarkTheme((value) => !value)}
                  >
                    <i />
                  </button>
                  <span className={darkTheme ? "is-active" : ""}>{t("oscuro")}</span>
                </div>
              </div>
            </SettingSection>
          )}
          {category === "operation" && (
            <SettingSection title={t("unidades_de_medida")}>
              <div className="settings-row">
                <div>
                  <strong>{t("sistema")}</strong>
                  <span>{t("formato_distancias")}</span>
                </div>
                <SegmentedSetting value={units} onChange={setUnits} />
              </div>
            </SettingSection>
          )}
          {category === "thresholds" && (
            <SettingSection title={t("umbrales_normativos")}>
              <div className="settings-reference-list">
                <div><span>CO</span><strong>25 ppm</strong></div>
                <div><span>H₂S</span><strong>10 ppm</strong></div>
                <div><span>O₂ mínimo</span><strong>19.5%</strong></div>
                <div><span>CH₄ alarma</span><strong>0.5% / 1.0%</strong></div>
              </div>
              <p className="settings-note">{t("solo_referencia")}</p>
            </SettingSection>
          )}
          {category === "language" && (
            <SettingSection title={t("idioma")}>
              <div className="settings-row">
                <div>
                  <strong>{t("idioma")}</strong>
                  <span>{t("idioma_interfaz")}</span>
                </div>
                <StyledSelect
                  ariaLabel={t("idioma")}
                  value={language}
                  onChange={(val) => setLanguage(val as Language)}
                  options={[
                    { label: "Español", value: "Español" },
                    { label: "English", value: "English" },
                  ]}
                />
              </div>
            </SettingSection>
          )}
          {category === "about" && (
            <SettingSection title={t("acerca_de")}>
              <div className="settings-about">
                <strong>v0.1.0 · {t("build_hackathon")}</strong>
                <p>{t("acerca_desc")}</p>
              </div>
            </SettingSection>
          )}
        </div>
      </div>
    </PanelModal>
  );
}
