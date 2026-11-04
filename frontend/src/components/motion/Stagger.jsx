import { motion, useReducedMotion } from "motion/react";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.2, 0, 0, 1] } },
};

/**
 * Wraps a list of items and staggers their entrance as the group scrolls
 * into view. Use <Stagger.Item> for each child. Collapses to a static
 * render under prefers-reduced-motion.
 */
export default function Stagger({ children, className = "", as = "div", ...rest }) {
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
      variants={container}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-10% 0px" }}
      {...rest}
    >
      {children}
    </Component>
  );
}

function StaggerItem({ children, as = "div", className = "", ...rest }) {
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
    <Component className={className} variants={item} {...rest}>
      {children}
    </Component>
  );
}

Stagger.Item = StaggerItem;
