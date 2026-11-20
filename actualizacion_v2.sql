-- Bitácora GPI · actualización v2 (contraseña temporal)
-- Si ya ejecutó supabase_schema.sql antes del 20/11/2026, pegue SOLO este archivo
-- en Supabase > SQL Editor > New query > Run.

-- Solo el líder asigna una contraseña temporal a quien la olvidó
create extension if not exists pgcrypto with schema extensions;
create or replace function public.restablecer_clave(usuario uuid, nueva text) returns void
language plpgsql security definer set search_path = public, extensions as $$
begin
  if not public.es_lider() then raise exception 'Solo el líder puede restablecer contraseñas'; end if;
  if length(coalesce(nueva, '')) < 6 then raise exception 'La contraseña debe tener al menos 6 caracteres'; end if;
  update auth.users set encrypted_password = crypt(nueva, gen_salt('bf')), updated_at = now() where id = usuario;
end $$;
revoke execute on function public.restablecer_clave(uuid, text) from anon, public;
grant execute on function public.restablecer_clave(uuid, text) to authenticated;
