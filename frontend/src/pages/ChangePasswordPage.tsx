import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import { toApiError, type ApiError } from "../api/client";
import { useAuth, useSession } from "../auth/AuthContext";
import { Button, Card, Field, FormError, linkButtonClass, Logo } from "../components/ui";

export function ChangePasswordPage() {
  const { user } = useSession();
  const { changePassword, logout } = useAuth();
  const navigate = useNavigate();
  const [values, setValues] = useState({ old_password: "", new_password1: "", new_password2: "" });
  const [error, setError] = useState<ApiError | null>(null);
  const [sending, setSending] = useState(false);
  const forced = user.must_change_password;

  const update = (name: keyof typeof values) => (event: ChangeEvent<HTMLInputElement>) =>
    setValues((current) => ({ ...current, [name]: event.target.value }));

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      await changePassword(values);
      navigate("/", { replace: true });
    } catch (cause) {
      setError(toApiError(cause));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-ink-50 p-6">
      <div className="w-full max-w-md">
        <div className="mb-10"><Logo /></div>
        <h1 className="font-display text-[1.75rem] font-bold leading-tight">Cambiar contraseña</h1>
        <p className="mb-6 mt-2 text-sm text-ink-500">
          {forced
            ? "Ingresaste con una contraseña temporal. Elige una propia para continuar; solo tú la conocerás."
            : "Usa al menos 8 caracteres que no sean fáciles de adivinar."}
        </p>
        <Card className="p-6">
          <form onSubmit={handleSubmit} noValidate>
            {error && !Object.keys(error.fields).some((name) => name !== "__all__") ? <FormError error={error} /> : null}
            <Field id="old_password" label="Contraseña actual" type="password" autoComplete="current-password"
              value={values.old_password} onChange={update("old_password")} error={error?.field("old_password")} />
            <Field id="new_password1" label="Contraseña nueva" type="password" autoComplete="new-password"
              hint="Mínimo 8 caracteres, que no sea común ni solo números."
              value={values.new_password1} onChange={update("new_password1")} error={error?.field("new_password1")} />
            <Field id="new_password2" label="Confirma la contraseña nueva" type="password" autoComplete="new-password"
              value={values.new_password2} onChange={update("new_password2")} error={error?.field("new_password2")} />
            <div className="flex justify-end gap-2 border-t border-ink-100 pt-4">
              {forced ? (
                <Button type="button" variant="secondary" onClick={() => void logout().then(() => navigate("/ingresar"))}>Salir</Button>
              ) : (
                <Link to="/" className={linkButtonClass("secondary")}>Cancelar</Link>
              )}
              <Button type="submit" disabled={sending}>{sending ? "Guardando…" : "Guardar contraseña"}</Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
