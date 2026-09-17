import { BrowserRouter } from "react-router-dom";
import { SessionProvider } from "./SessionContext.jsx";
import { AssessmentProvider } from "./AssessmentContext.jsx";
import { ToastProvider } from "../components/common/ToastContext.jsx";
import AppRoutes from "./routes.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <AssessmentProvider>
          <ToastProvider>
            <a href="#main-content" className="skip-link">
              Skip to main content
            </a>
            <AppRoutes />
          </ToastProvider>
        </AssessmentProvider>
      </SessionProvider>
    </BrowserRouter>
  );
}
