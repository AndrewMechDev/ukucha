import { useEffect, useState } from "react";
import { apiGet } from "../services/api";

type HealthStatus = {
  status: string;
};

export default function Home() {
  const [status, setStatus] = useState<string>("conectando...");

  useEffect(() => {
    apiGet<HealthStatus>("/v1/health")
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("error de conexión"));
  }, []);

  return (
    <section>
      <h1>Ukucha</h1>
      <p>API: {status}</p>
    </section>
  );
}
