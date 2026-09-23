/**
 * Double-bezel nested card: an outer shell (subtle tinted surface, hairline
 * ring, large radius) around an inner core (the actual content surface,
 * its own inner highlight, a smaller concentric radius) -- makes a card
 * read as machined hardware rather than a flat rectangle. Opt-in per card;
 * never applied to data tables (AssessmentsTable/PatientsTable) or the
 * Dashboard summary grid, which stay flat/dense by design.
 */
export default function Bezel({ children, className = "", innerClassName = "" }) {
  return (
    <div className={`rounded-[22px] bg-line/40 p-1.5 ring-1 ring-line-strong/50 ${className}`}>
      <div
        className={`rounded-[16px] bg-white shadow-[inset_0_1px_0_rgba(255,255,255,.5)] dark:shadow-[inset_0_1px_0_rgba(255,255,255,.06)] ${innerClassName}`}
      >
        {children}
      </div>
    </div>
  );
}
