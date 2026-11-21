-- Bitácora GPI · actualización v3 (los aprendices pueden crear su grupo)
-- Pegue SOLO este archivo en Supabase > SQL Editor > New query > Run.

-- IMPORTANTE (seguridad): cada usuario solo puede cambiar su propio NOMBRE, no su rol.
-- (El "grant update on all tables" de arriba lo había abierto; esto lo vuelve a cerrar.)
revoke update on public.perfiles from authenticated, anon;
grant update (nombre) on public.perfiles to authenticated;

-- Un aprendiz puede crear el grupo de su empresa proyecto (queda como integrante).
-- Si ya existe un grupo activo con la misma ficha y empresa, lo une a ese en lugar de duplicarlo.
create or replace function public.crear_mi_grupo(p_nombre text, p_ficha text, p_empresa text, p_sector text default '')
returns json language plpgsql security definer set search_path = public as $$
declare g record; existente boolean := false;
begin
  if auth.uid() is null then raise exception 'Debe iniciar sesión'; end if;
  if coalesce(trim(p_nombre), '') = '' or coalesce(trim(p_empresa), '') = '' or coalesce(trim(p_ficha), '') = '' then
    raise exception 'Nombre del grupo, ficha y empresa son obligatorios';
  end if;
  select * into g from public.grupos
   where activo and lower(trim(ficha)) = lower(trim(p_ficha)) and lower(trim(empresa)) = lower(trim(p_empresa)) limit 1;
  if found then
    existente := true;
  else
    insert into public.grupos (nombre, ficha, empresa, sector, creado_por)
    values (trim(p_nombre), trim(p_ficha), trim(p_empresa), coalesce(trim(p_sector), ''), auth.uid())
    returning * into g;
  end if;
  insert into public.miembros (grupo_id, perfil_id) values (g.id, auth.uid()) on conflict do nothing;
  return json_build_object('id', g.id, 'codigo', g.codigo, 'nombre', g.nombre, 'existente', existente);
end $$;
revoke execute on function public.crear_mi_grupo(text, text, text, text) from anon, public;
grant execute on function public.crear_mi_grupo(text, text, text, text) to authenticated;
