import type { ReactNode } from "react";

type Props = {
  id: string;
  label: string;
  hint?: string;
  children: ReactNode;
};

export function FormField({ id, label, hint, children }: Props) {
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint ? (
        <p className="field-hint" id={`${id}-hint`}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function FormError({ message }: { message: string | null }) {
  return (
    <div role="alert" className={message ? "alert alert-error" : undefined}>
      {message}
    </div>
  );
}

export function FormNotice({ message }: { message: string | null }) {
  return (
    <div role="status" className={message ? "alert alert-success" : undefined}>
      {message}
    </div>
  );
}
