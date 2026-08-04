import * as Label from "@radix-ui/react-label";
import type { InputHTMLAttributes } from "react";

type FormFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
};

export function FormField({ label, hint, id, className = "", ...props }: FormFieldProps) {
  const fieldId = id ?? props.name ?? label.toLowerCase().replaceAll(" ", "-");
  return (
    <div className="space-y-2">
      <Label.Root className="text-sm font-medium text-zinc-200" htmlFor={fieldId}>
        {label}
      </Label.Root>
      <input
        id={fieldId}
        className={`min-h-11 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-forge-300 focus:ring-2 focus:ring-forge-300/20 ${className}`}
        {...props}
      />
      {hint ? <p className="text-xs leading-5 text-zinc-500">{hint}</p> : null}
    </div>
  );
}
