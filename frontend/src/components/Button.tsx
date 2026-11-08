import type { ButtonHTMLAttributes } from "react";

const VARIANTS = {
  primary: "bg-indigo-600 text-white hover:bg-indigo-700",
  secondary: "border border-slate-300 bg-white hover:bg-slate-50",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof VARIANTS;
}

export default function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      className={`rounded-md px-4 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-indigo-600 disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}
