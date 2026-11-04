import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import IconButton from "../common/IconButton.jsx";
import styles from "./AuthLayout.module.css";

const NO_BACK_ROUTES = new Set(["/role"]);

export default function AuthLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const hideBack = NO_BACK_ROUTES.has(location.pathname);

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        {!hideBack && (
          <IconButton icon={ChevronLeft} label="Go back" onClick={() => navigate(-1)} variant="outline" />
        )}
        <Link to="/" className={styles.logo} aria-label="Memora Home">
          Memora
        </Link>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}
