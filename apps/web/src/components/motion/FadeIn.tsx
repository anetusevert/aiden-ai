'use client';

import { motion, type HTMLMotionProps } from 'framer-motion';

const defaultVariants = {
  hidden: { opacity: 0.97, y: 14 },
  visible: { opacity: 1, y: 0 },
};

export function FadeIn({
  children,
  delay = 0,
  className,
  ...props
}: HTMLMotionProps<'div'> & { delay?: number }) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={defaultVariants}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}
