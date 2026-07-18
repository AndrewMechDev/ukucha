import { useEffect, useState } from "react";

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export default function PwaInstallButton({ collapsed }: { collapsed: boolean }) {
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [showInstructions, setShowInstructions] = useState(false);

  useEffect(() => {
    const handleInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };

    window.addEventListener("beforeinstallprompt", handleInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", handleInstallPrompt);
  }, []);

  const install = async () => {
    if (!installPrompt) {
      setShowInstructions(true);
      return;
    }
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  };

  return (
    <div className="pwa-install-wrap">
      <button className={`pwa-install-button${collapsed ? " pwa-install-button--collapsed" : ""}`} type="button" onClick={install} aria-label="Instalar Ukucha">
        <span className="material-symbols-rounded" aria-hidden="true">install_mobile</span>
        {!collapsed && <span>Instalar Ukucha</span>}
      </button>
      {showInstructions && !collapsed && <span className="pwa-install-hint">Usa el icono de instalación de Chrome o Edge en la barra de direcciones.</span>}
    </div>
  );
}
