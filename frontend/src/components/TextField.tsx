import { useId, type InputHTMLAttributes } from "react";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export default function TextField({ label, ...props }: TextFieldProps) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2"
        {...props}
      />
    </div>
  );
}
