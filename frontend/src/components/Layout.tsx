import { Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <>
      <header>
        <nav>
          <a href="/">Ukucha</a>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
