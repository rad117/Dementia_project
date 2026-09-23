import { useRef } from "react";
import { motion, useMotionValue, useSpring, useReducedMotion } from "motion/react";

/**
 * Cursor-follow hover physics for a single primary CTA. Wraps (does not
 * replace) whatever's passed as children -- e.g. <MagneticButton><Button
 * variant="accent">Get started</Button></MagneticButton>. Marketing CTAs
 * only (Landing/RoleSelect); clinical action buttons stay utilitarian.
 */
export default function MagneticButton({ children, strength = 0.3, className = "" }) {
  const ref = useRef(null);
  const reduce = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 300, damping: 20 });
  const sy = useSpring(y, { stiffness: 300, damping: 20 });

  if (reduce) {
    return (
      <span ref={ref} className={className}>
        {children}
      </span>
    );
  }

  function onMouseMove(e) {
    const r = ref.current.getBoundingClientRect();
    x.set((e.clientX - r.left - r.width / 2) * strength);
    y.set((e.clientY - r.top - r.height / 2) * strength);
  }

  function onMouseLeave() {
    x.set(0);
    y.set(0);
  }

  return (
    <motion.span
      ref={ref}
      className={className}
      style={{ x: sx, y: sy, display: "inline-block" }}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
    >
      {children}
    </motion.span>
  );
}
