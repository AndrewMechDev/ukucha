import { useEffect, useState } from "react";

export default function PwaUpdatePrompt() {
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);

  useEffect(() => {
    if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return undefined;

    let activeRegistration: ServiceWorkerRegistration | undefined;
    navigator.serviceWorker.register("/sw.js").then((value) => {
      activeRegistration = value;
      if (value.waiting) setRegistration(value);

      value.addEventListener("updatefound", () => {
        const worker = value.installing;
        if (!worker) return;
        worker.addEventListener("statechange", () => {
          if (worker.state === "installed" && navigator.serviceWorker.controller) {
            setRegistration(value);
          }
        });
      });
    }).catch(() => {
      // La aplicación sigue funcionando aunque el navegador no permita PWA.
    });

    return () => {
      activeRegistration?.update().catch(() => undefined);
    };
  }, []);

  if (!registration) return null;

  return (
    <aside className="pwa-update-prompt" role="status">
      <span>Hay una nueva versión de Ukucha disponible.</span>
      <button type="button" onClick={() => {
        registration.waiting?.postMessage({ type: "SKIP_WAITING" });
        window.location.reload();
      }}>
        Actualizar
      </button>
    </aside>
  );
}
