import { Link } from "react-router-dom";
import Button from "../../components/common/Button.jsx";

export default function NotFound() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "var(--space-4)", padding: "var(--space-6)", textAlign: "center" }}>
      <h1 style={{ fontSize: 32 }}>Page not found</h1>
      <p style={{ color: "var(--muted)", maxWidth: 420 }}>The page you're looking for doesn't exist or may have moved.</p>
      <Button as={Link} to="/" variant="accent">
        Return home
      </Button>
    </div>
  );
}
