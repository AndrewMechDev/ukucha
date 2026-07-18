import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section>
      <h1>404</h1>
      <p>No encontramos esta página.</p>
      <Link to="/">Volver al inicio</Link>
    </section>
  );
}
