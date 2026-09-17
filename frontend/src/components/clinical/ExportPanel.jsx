import { Printer, Download } from "lucide-react";
import Button from "../common/Button.jsx";
import styles from "./ExportPanel.module.css";

export default function ExportPanel() {
  return (
    <div className={styles.row}>
      <Button variant="secondary" onClick={() => window.print()}>
        <Printer size={16} aria-hidden="true" /> Print
      </Button>
      <Button variant="secondary" onClick={() => window.print()}>
        <Download size={16} aria-hidden="true" /> Export PDF
      </Button>
    </div>
  );
}
