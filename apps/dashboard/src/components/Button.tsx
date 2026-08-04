import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonTone = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: ButtonTone;
  icon?: ReactNode;
};

const toneClasses: Record<ButtonTone, string> = {
  primary:
    "bg-forge-500 text-white shadow-lg shadow-forge-950/30 hover:bg-forge-300 hover:text-zinc-950",
  secondary: "border border-zinc-700 bg-zinc-900 text-zinc-100 hover:border-zinc-500",
  ghost: "text-zinc-300 hover:bg-zinc-800 hover:text-white",
};

export function Button({ className = "", tone = "primary", icon, children, ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-300 disabled:cursor-not-allowed disabled:opacity-60 ${toneClasses[tone]} ${className}`}
      {...props}
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}
