import { motion, useReducedMotion } from "motion/react";

/**
 * Viewport-triggered entrance. Fires once, reuses the app's existing
 * --ease-standard cubic-bezier so JS motion matches CSS transitions
 * elsewhere. Collapses to a static render under prefers-reduced-motion.
 */
export default function FadeInUp({ children, delay = 0, as = "div", className = "", ...rest }) {
  const reduce = useReducedMotion();
  const Component = motion[as] ?? motion.div;

  if (reduce) {
    const Static = as;
    return (
      <Static className={className} {...rest}>
        {children}
      </Static>
    );
  }

  return (
    <Component
      className={className}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ duration: 0.5, ease: [0.2, 0, 0, 1], delay }}
      {...rest}
    >
      {children}
    </Component>
  );
}
