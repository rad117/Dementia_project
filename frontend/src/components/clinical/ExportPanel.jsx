import { useState } from "react";
import { Printer, Download, Loader2 } from "lucide-react";
import Button from "../common/Button.jsx";
import styles from "./ExportPanel.module.css";

async function exportToPdf(fileName) {
  const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
    import("jspdf"),
    import("html2canvas-pro"),
  ]);

  // The clinical layout's <main> is the one printable region -- sidebar,
  // topbar, and buttons live outside it, and .no-print marks anything
  // inside it (like this panel) that shouldn't appear in the export.
  const target = document.querySelector("main");
  if (!target) return;

  const canvas = await html2canvas(target, {
    backgroundColor: "#ffffff",
    scale: 2,
    onclone: (clonedDoc) => {
      clonedDoc.querySelectorAll(".no-print").forEach((el) => {
        el.style.display = "none";
      });
    },
  });

  const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const imgWidth = pageWidth;
  const imgHeight = (canvas.height * imgWidth) / canvas.width;

  // JPEG instead of PNG: this is a screenshot of a mostly-white report, not
  // a graphic needing lossless/alpha, and PNG at 2x scale ran ~13MB per page
  // vs ~1MB for JPEG at the same visual quality.
  const imgData = canvas.toDataURL("image/jpeg", 0.92);
  let heightLeft = imgHeight;
  let position = 0;

  pdf.addImage(imgData, "JPEG", 0, position, imgWidth, imgHeight);
  heightLeft -= pageHeight;

  while (heightLeft > 0) {
    position = heightLeft - imgHeight;
    pdf.addPage();
    pdf.addImage(imgData, "JPEG", 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;
  }

  pdf.save(fileName);
}

export default function ExportPanel({ fileName = "memora-export.pdf" }) {
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      await exportToPdf(fileName);
    } catch {
      // Falls back to the browser's own print-to-PDF path, which the
      // existing @media print rules (frontend/src/styles/globals.css)
      // already support end to end.
      window.print();
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className={`${styles.row} no-print`}>
      <Button variant="secondary" onClick={() => window.print()}>
        <Printer size={16} aria-hidden="true" /> Print
      </Button>
      <Button variant="secondary" onClick={handleExport} disabled={exporting}>
        {exporting ? (
          <Loader2 size={16} aria-hidden="true" className={styles.spinner} />
        ) : (
          <Download size={16} aria-hidden="true" />
        )}
        {exporting ? "Exporting…" : "Export PDF"}
      </Button>
    </div>
  );
}
