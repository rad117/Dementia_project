import { Outlet } from "react-router-dom";
import PublicHeader from "./PublicHeader.jsx";
import Footer from "./Footer.jsx";

export default function PublicLayout() {
  return (
    <>
      <PublicHeader />
      <main id="main-content">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}
