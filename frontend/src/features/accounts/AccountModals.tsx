import { useState } from "react";

import { Grid, SelectField, type Option } from "../../components/forms";
import { ConfirmModal, FormModal } from "../../components/Modal";
import { useNotify } from "../../components/Page";
import { Badge, Button, Field, Icon } from "../../components/ui";
import { formatLongDate } from "../../lib/format";
import { useForm } from "../../lib/useForm";
import { useSession } from "../../auth/AuthContext";
import { accountsApi, type Account, type AccountInput, type TemporaryPasswordInput } from "./api";

/** Contexto del formulario: qué roles puede crear quien lo usa y entre qué empresas elegir. */
export interface AccountOptions {
  roles: Option[];
  companies: { id: number; name: string }[];
  /** Fija la empresa (por ejemplo, al crear el acceso desde el detalle de la empresa). */
  company?: { id: number; name: string };
}

export function AccountFormModal({ account, options, onClose, onSaved }: {
  account?: Account; options: AccountOptions; onClose: () => void; onSaved: (account: Account) => void;
}) {
  const notify = useNotify();
  const singleRole = options.roles.length === 1 ? options.roles[0]?.value : undefined;
  const form = useForm<AccountInput>(account
    ? { first_name: account.first_name, last_name: account.last_name, email: account.email,
        company: account.company ? String(account.company.id) : "" }
    : { first_name: "", last_name: "", email: "", role: options.company ? "empresa" : (singleRole ?? ""),
        company: options.company ? String(options.company.id) : "", password1: "", password2: "" });
  const { values, set } = form;
  const role = account ? account.role : values.role;
  const needsCompany = role === "empresa";

  // La empresa actual de la cuenta se muestra aunque esté inactiva.
  const companies = [...options.companies];
  if (account?.company && !companies.some((c) => c.id === account.company?.id)) companies.push(account.company);

  async function save() {
    const input: AccountInput = { ...values };
    if (!needsCompany) delete input.company;
    const result = await form.submit(() => (account ? accountsApi.update(account.id, input) : accountsApi.create(input)));
    if (result) {
      notify(account ? "Cuenta actualizada" : "Cuenta creada");
      onSaved(result);
    }
  }

  const title = account ? "Editar cuenta" : options.company ? `Crear acceso para ${options.company.name}` : "Crear cuenta";
  return (
    <FormModal title={title} submitLabel={account ? "Guardar" : "Crear cuenta"} sending={form.sending} error={form.error}
      note={account ? undefined : "Comparte el correo y la contraseña temporal por un canal seguro. Al primer ingreso, el sistema pedirá una contraseña nueva."}
      onClose={onClose} onSubmit={() => void save()}>
      <Grid>
        <Field id="first_name" label="Nombres" value={values.first_name}
          onChange={(e) => set("first_name", e.target.value)} error={form.fieldError("first_name")} />
        <Field id="last_name" label="Apellidos" value={values.last_name}
          onChange={(e) => set("last_name", e.target.value)} error={form.fieldError("last_name")} />
      </Grid>
      <Field id="email" label="Correo electrónico" type="email" autoComplete="off" placeholder="nombre@empresa.com" value={values.email}
        onChange={(e) => set("email", e.target.value)} error={form.fieldError("email")} />
      {!account && !options.company && options.roles.length > 1 ? (
        <SelectField id="role" label="Rol" options={options.roles} placeholder="Selecciona el rol" value={values.role ?? ""}
          onChange={(e) => set("role", e.target.value)} error={form.fieldError("role")} />
      ) : null}
      {needsCompany && !options.company ? (
        <SelectField id="company" label="Empresa" placeholder="Selecciona la empresa" value={values.company ?? ""}
          options={companies.map((c) => ({ value: String(c.id), label: c.name }))}
          hint="La cuenta solo verá los datos de esta empresa."
          onChange={(e) => set("company", e.target.value)} error={form.fieldError("company")} />
      ) : null}
      {account ? null : (
        <Grid>
          <Field id="password1" label="Contraseña temporal" type="password" autoComplete="new-password" value={values.password1 ?? ""}
            hint="Deberá cambiarla la primera vez que ingrese."
            onChange={(e) => set("password1", e.target.value)} error={form.fieldError("password1")} />
          <Field id="password2" label="Repite la contraseña" type="password" autoComplete="new-password" value={values.password2 ?? ""}
            onChange={(e) => set("password2", e.target.value)} error={form.fieldError("password2")} />
        </Grid>
      )}
    </FormModal>
  );
}

export function PasswordModal({ account, onClose, onSaved }: { account: Account; onClose: () => void; onSaved: () => void }) {
  const notify = useNotify();
  const form = useForm<TemporaryPasswordInput>({ new_password1: "", new_password2: "" });

  async function save() {
    if (await form.submit((input) => accountsApi.setPassword(account.id, input))) {
      notify("Contraseña temporal asignada");
      onSaved();
    }
  }

  return (
    <FormModal title="Asignar contraseña temporal" submitLabel="Guardar contraseña" sending={form.sending} error={form.error}
      note={`Cuenta: ${account.email}. La sesión abierta de esa persona se cerrará.`} onClose={onClose} onSubmit={() => void save()}>
      <Field id="new_password1" label="Nueva contraseña temporal" type="password" autoComplete="new-password"
        hint="La persona deberá cambiarla al ingresar." value={form.values.new_password1}
        onChange={(e) => form.set("new_password1", e.target.value)} error={form.fieldError("new_password1")} />
      <Field id="new_password2" label="Repite la contraseña" type="password" autoComplete="new-password" value={form.values.new_password2}
        onChange={(e) => form.set("new_password2", e.target.value)} error={form.fieldError("new_password2")} />
    </FormModal>
  );
}

function ActiveModal({ account, onClose, onSaved }: { account: Account; onClose: () => void; onSaved: () => void }) {
  const notify = useNotify();
  const form = useForm({});
  const deactivating = account.is_active;

  async function confirm() {
    if (await form.submit(() => accountsApi.setActive(account.id, !deactivating))) {
      notify(deactivating ? "Cuenta desactivada" : "Cuenta activada");
      onSaved();
    }
  }

  return (
    <ConfirmModal title={deactivating ? "Desactivar cuenta" : "Activar cuenta"} danger={deactivating}
      confirmLabel={deactivating ? "Desactivar" : "Activar"} sending={form.sending} error={form.error}
      message={deactivating
        ? `${account.email} no podrá ingresar hasta que la actives de nuevo. Su historia se conserva.`
        : `${account.email} podrá ingresar otra vez con su contraseña actual.`}
      onClose={onClose} onConfirm={() => void confirm()} />
  );
}

export function AccountStatus({ account }: { account: Account }) {
  if (!account.is_active) return <Badge>Desactivada</Badge>;
  if (account.must_change_password) return <Badge tone="amber">Clave temporal</Badge>;
  return <Badge tone="teal">Activa</Badge>;
}

export function lastLogin(account: Account): string {
  return account.last_login ? `último ingreso ${formatLongDate(account.last_login.slice(0, 10))}` : "aún no ingresa";
}

type Open = "edit" | "password" | "active" | null;

/** Editar, asignar clave temporal y activar o desactivar. Nadie se desactiva a sí mismo. */
export function AccountActions({ account, options, onChanged }: { account: Account; options: AccountOptions; onChanged: () => void }) {
  const { user } = useSession();
  const [open, setOpen] = useState<Open>(null);
  const close = () => setOpen(null);
  const done = () => {
    setOpen(null);
    onChanged();
  };
  const own = account.id === user.id;
  const iconButton = "rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900";

  return (
    <div className="flex shrink-0 justify-end gap-1">
      <button type="button" className={iconButton} title="Editar datos" onClick={() => setOpen("edit")}>
        <Icon name="pencil" /><span className="sr-only">Editar {account.email}</span>
      </button>
      {own ? null : (
        <>
          <button type="button" className={iconButton} title="Asignar contraseña temporal" onClick={() => setOpen("password")}>
            <Icon name="key-round" /><span className="sr-only">Contraseña de {account.email}</span>
          </button>
          <button type="button" className={`${iconButton} ${account.is_active ? "hover:text-red-700" : ""}`}
            title={account.is_active ? "Desactivar" : "Activar"} onClick={() => setOpen("active")}>
            <Icon name={account.is_active ? "ban" : "check"} />
            <span className="sr-only">{account.is_active ? "Desactivar" : "Activar"} {account.email}</span>
          </button>
        </>
      )}
      {open === "edit" ? <AccountFormModal account={account} options={options} onClose={close} onSaved={done} /> : null}
      {open === "password" ? <PasswordModal account={account} onClose={close} onSaved={done} /> : null}
      {open === "active" ? <ActiveModal account={account} onClose={close} onSaved={done} /> : null}
    </div>
  );
}

export function CreateAccountButton({ options, onCreated, label = "Crear cuenta", startOpen = false }: {
  options: AccountOptions; onCreated: () => void; label?: string; startOpen?: boolean;
}) {
  const [open, setOpen] = useState(startOpen);
  return (
    <>
      <Button onClick={() => setOpen(true)}><Icon name="user-plus" />{label}</Button>
      {open ? <AccountFormModal options={options} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); onCreated(); }} /> : null}
    </>
  );
}
