-- =====================================================================
--  Bitácora del Proyecto Productivo GPI  ·  Esquema para Supabase
--  Pegue TODO este archivo en Supabase > SQL Editor > New query > Run.
--  Se puede ejecutar más de una vez sin dañar los datos.
-- =====================================================================

-- ---------- Perfiles y roles ----------------------------------------
-- rol: aprendiz | instructor | lider   (lider = coordina, crea grupos y asigna)
create table if not exists public.perfiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  nombre      text not null default '',
  correo      text not null default '',
  rol         text not null default 'aprendiz' check (rol in ('aprendiz','instructor','lider')),
  creado_en   timestamptz not null default now()
);

-- Cada usuario nuevo queda como aprendiz; el líder cambia el rol desde la app.
create or replace function public.crear_perfil() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.perfiles (id, nombre, correo)
  values (new.id, coalesce(new.raw_user_meta_data->>'nombre', ''), coalesce(new.email, ''))
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists al_crear_usuario on auth.users;
create trigger al_crear_usuario after insert on auth.users
  for each row execute function public.crear_perfil();

-- ---------- Grupos y miembros ---------------------------------------
create table if not exists public.grupos (
  id          uuid primary key default gen_random_uuid(),
  nombre      text not null,
  ficha       text default '',
  empresa     text not null,
  sector      text default '',
  descripcion text default '',
  codigo      text not null unique default upper(substr(md5(random()::text), 1, 6)),
  activo      boolean not null default true,
  creado_por  uuid references public.perfiles(id),
  creado_en   timestamptz not null default now()
);

create table if not exists public.miembros (
  grupo_id  uuid references public.grupos(id) on delete cascade,
  perfil_id uuid references public.perfiles(id) on delete cascade,
  unido_en  timestamptz not null default now(),
  primary key (grupo_id, perfil_id)
);

-- Instructor técnico asignado a cada competencia (objetivo 1 a 8) de un grupo
create table if not exists public.asignaciones (
  grupo_id      uuid references public.grupos(id) on delete cascade,
  obj           smallint not null check (obj between 1 and 8),
  instructor_id uuid not null references public.perfiles(id),
  primary key (grupo_id, obj)
);

-- ---------- Bitácora ------------------------------------------------
-- obj = 0 es "General" (contexto de la empresa); 1 a 8 son los objetivos/competencias
create table if not exists public.evidencias (
  id          uuid primary key default gen_random_uuid(),
  grupo_id    uuid not null references public.grupos(id) on delete cascade,
  obj         smallint not null check (obj between 0 and 8),
  tipo        text not null check (tipo in ('foto','datos','nota','documento')),
  titulo      text not null,
  descripcion text default '',
  fuente      text default '',
  archivos    text[] not null default '{}',   -- rutas dentro del bucket "evidencias"
  autor       uuid references public.perfiles(id) default auth.uid(),
  creado_en   timestamptz not null default now()
);
create index if not exists evidencias_grupo_obj on public.evidencias (grupo_id, obj);

-- Análisis de la situación problémica que hacen los aprendices (uno por objetivo)
create table if not exists public.analisis (
  grupo_id       uuid not null references public.grupos(id) on delete cascade,
  obj            smallint not null check (obj between 1 and 8),
  alternativas   jsonb,             -- propuesta de la IA (hipótesis)
  elegida        smallint,          -- índice de la alternativa elegida
  respuestas     jsonb not null default '[]',
  planteamiento  text default '',
  causas         text default '',
  indicador      text default '',
  datos          text default '',
  retro_ia       jsonb,
  estado         text not null default 'borrador' check (estado in ('borrador','enviado')),
  actualizado_por uuid references public.perfiles(id) default auth.uid(),
  actualizado_en timestamptz not null default now(),
  primary key (grupo_id, obj)
);

-- Visto bueno del instructor técnico (se guarda el historial; vale el último)
create table if not exists public.vistos_buenos (
  id            uuid primary key default gen_random_uuid(),
  grupo_id      uuid not null references public.grupos(id) on delete cascade,
  obj           smallint not null check (obj between 1 and 8),
  instructor_id uuid not null references public.perfiles(id) default auth.uid(),
  estado        text not null check (estado in ('aprobado','ajustes')),
  observaciones text not null default '',
  niveles       jsonb,              -- opcional: niveles 1-4 de la rúbrica
  nota          numeric(2,1),
  creado_en     timestamptz not null default now()
);
create index if not exists vb_grupo_obj on public.vistos_buenos (grupo_id, obj, creado_en desc);

-- Revisiones de la presentación (avance de un objetivo o final con los 8)
create table if not exists public.revisiones (
  id              uuid primary key default gen_random_uuid(),
  grupo_id        uuid not null references public.grupos(id) on delete cascade,
  tipo            text not null check (tipo in ('avance','final')),
  obj             smallint check (obj between 1 and 8),
  archivo_nombre  text default '',
  archivo_ruta    text,             -- ruta en el bucket (si el archivo cupo)
  diapositivas    int,
  contenido       jsonb,            -- texto y transcripción de imágenes por diapositiva
  propuesta       jsonb,            -- lo que propuso la IA
  resultado       jsonb,            -- niveles validados por el instructor
  nota            numeric(2,1),
  aprueba         boolean,
  recomendaciones text default '',
  oportunidades   text default '',
  observaciones   text default '',
  estado          text not null default 'propuesta' check (estado in ('propuesta','validada')),
  subido_por      uuid references public.perfiles(id) default auth.uid(),
  validado_por    uuid references public.perfiles(id),
  validado_en     timestamptz,
  creado_en       timestamptz not null default now()
);
create index if not exists rev_grupo on public.revisiones (grupo_id, creado_en desc);

-- ---------- Funciones de apoyo para los permisos --------------------
create or replace function public.mi_rol() returns text
language sql stable security definer set search_path = public as $$
  select rol from public.perfiles where id = auth.uid()
$$;

create or replace function public.es_staff() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select rol in ('instructor','lider') from public.perfiles where id = auth.uid()), false)
$$;

create or replace function public.es_lider() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select rol = 'lider' from public.perfiles where id = auth.uid()), false)
$$;

create or replace function public.es_miembro(g uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.miembros where grupo_id = g and perfil_id = auth.uid())
$$;

create or replace function public.puede_ver(g uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select public.es_staff() or public.es_miembro(g)
$$;

create or replace function public.es_asignado(g uuid, o smallint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.asignaciones where grupo_id = g and obj = o and instructor_id = auth.uid())
$$;

-- El aprendiz se une a su grupo con el código que le da el instructor
create or replace function public.unirse_grupo(cod text) returns uuid
language plpgsql security definer set search_path = public as $$
declare g uuid;
begin
  if auth.uid() is null then raise exception 'Debe iniciar sesión'; end if;
  select id into g from public.grupos where codigo = upper(trim(cod)) and activo;
  if g is null then raise exception 'Código de grupo no válido'; end if;
  insert into public.miembros (grupo_id, perfil_id) values (g, auth.uid()) on conflict do nothing;
  return g;
end $$;

-- Solo el líder cambia roles
create or replace function public.asignar_rol(usuario uuid, nuevo_rol text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.es_lider() then raise exception 'Solo el líder puede cambiar roles'; end if;
  if nuevo_rol not in ('aprendiz','instructor','lider') then raise exception 'Rol no válido'; end if;
  update public.perfiles set rol = nuevo_rol where id = usuario;
end $$;

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

-- ---------- Seguridad por filas (RLS) -------------------------------
alter table public.perfiles      enable row level security;
alter table public.grupos        enable row level security;
alter table public.miembros      enable row level security;
alter table public.asignaciones  enable row level security;
alter table public.evidencias    enable row level security;
alter table public.analisis      enable row level security;
alter table public.vistos_buenos enable row level security;
alter table public.revisiones    enable row level security;

-- El usuario solo puede cambiar su propio nombre (el rol se cambia con asignar_rol)
revoke update on public.perfiles from authenticated, anon;
grant update (nombre) on public.perfiles to authenticated;

do $$ declare t text; begin
  foreach t in array array['perfiles','grupos','miembros','asignaciones','evidencias','analisis','vistos_buenos','revisiones'] loop
    execute coalesce((select string_agg(format('drop policy if exists %I on public.%I;', policyname, t), ' ')
             from pg_policies where schemaname = 'public' and tablename = t), 'select 1');
  end loop;
end $$;

-- perfiles
create policy perfiles_ver on public.perfiles for select to authenticated
  using (id = auth.uid() or public.es_staff() or rol in ('instructor','lider')
         or exists (select 1 from public.miembros a join public.miembros b on a.grupo_id = b.grupo_id
                    where a.perfil_id = auth.uid() and b.perfil_id = perfiles.id));
create policy perfiles_editar on public.perfiles for update to authenticated
  using (id = auth.uid()) with check (id = auth.uid());

-- grupos
create policy grupos_ver    on public.grupos for select to authenticated using (public.puede_ver(id));
create policy grupos_crear  on public.grupos for insert to authenticated with check (public.es_staff());
create policy grupos_editar on public.grupos for update to authenticated using (public.es_staff());
create policy grupos_borrar on public.grupos for delete to authenticated using (public.es_lider());

-- miembros
create policy miembros_ver    on public.miembros for select to authenticated using (public.puede_ver(grupo_id));
create policy miembros_crear  on public.miembros for insert to authenticated with check (public.es_staff());
create policy miembros_borrar on public.miembros for delete to authenticated using (public.es_staff());

-- asignaciones
create policy asig_ver    on public.asignaciones for select to authenticated using (public.puede_ver(grupo_id));
create policy asig_crear  on public.asignaciones for insert to authenticated with check (public.es_staff());
create policy asig_editar on public.asignaciones for update to authenticated using (public.es_staff());
create policy asig_borrar on public.asignaciones for delete to authenticated using (public.es_staff());

-- evidencias: el grupo y los instructores; borra quien la subió o un instructor
create policy ev_ver    on public.evidencias for select to authenticated using (public.puede_ver(grupo_id));
create policy ev_crear  on public.evidencias for insert to authenticated
  with check (public.puede_ver(grupo_id) and autor = auth.uid());
create policy ev_editar on public.evidencias for update to authenticated
  using (autor = auth.uid() or public.es_staff());
create policy ev_borrar on public.evidencias for delete to authenticated
  using (autor = auth.uid() or public.es_staff());

-- análisis: lo trabaja el grupo; los instructores lo ven y pueden devolverlo a borrador
create policy an_ver    on public.analisis for select to authenticated using (public.puede_ver(grupo_id));
create policy an_crear  on public.analisis for insert to authenticated with check (public.puede_ver(grupo_id));
create policy an_editar on public.analisis for update to authenticated using (public.puede_ver(grupo_id));

-- vistos buenos: solo el instructor asignado a esa competencia (o el líder)
create policy vb_ver   on public.vistos_buenos for select to authenticated using (public.puede_ver(grupo_id));
create policy vb_crear on public.vistos_buenos for insert to authenticated
  with check (instructor_id = auth.uid() and (public.es_asignado(grupo_id, obj) or public.es_lider()));

-- revisiones: el grupo sube su PPT y recibe la propuesta; solo instructores validan
create policy rev_ver    on public.revisiones for select to authenticated using (public.puede_ver(grupo_id));
create policy rev_crear  on public.revisiones for insert to authenticated
  with check (public.puede_ver(grupo_id) and estado = 'propuesta');
create policy rev_editar on public.revisiones for update to authenticated using (public.es_staff());
create policy rev_borrar on public.revisiones for delete to authenticated using (public.es_lider());

-- ---------- Almacenamiento de archivos (fotos, Excel, PPT) ----------
-- Bucket privado. Las rutas empiezan por el id del grupo: <grupo_id>/...
insert into storage.buckets (id, name, public, file_size_limit)
values ('evidencias', 'evidencias', false, 52428800)
on conflict (id) do nothing;

drop policy if exists "bitacora ver archivos" on storage.objects;
drop policy if exists "bitacora subir archivos" on storage.objects;
drop policy if exists "bitacora borrar archivos" on storage.objects;

create policy "bitacora ver archivos" on storage.objects for select to authenticated
  using (bucket_id = 'evidencias' and public.puede_ver(((storage.foldername(name))[1])::uuid));
create policy "bitacora subir archivos" on storage.objects for insert to authenticated
  with check (bucket_id = 'evidencias' and public.puede_ver(((storage.foldername(name))[1])::uuid));
create policy "bitacora borrar archivos" on storage.objects for delete to authenticated
  using (bucket_id = 'evidencias' and (owner = auth.uid() or public.es_staff()));

-- =====================================================================
--  DESPUÉS de crear su propia cuenta en la app, conviértase en líder
--  ejecutando esta línea (cambie el correo por el suyo):
--
--  update public.perfiles set rol = 'lider' where correo = 'su_correo@ejemplo.com';
-- =====================================================================

-- Permisos (proyectos nuevos de Supabase no los otorgan automáticamente; RLS sigue aplicando)
grant usage on schema public to authenticated;
grant select, insert, update, delete on all tables in schema public to authenticated;
grant usage, select on all sequences in schema public to authenticated;
grant execute on all functions in schema public to authenticated;

-- IMPORTANTE (seguridad): cada usuario solo puede cambiar su propio NOMBRE, no su rol.
-- (El "grant update on all tables" de arriba lo había abierto; esto lo vuelve a cerrar.)
revoke update on public.perfiles from authenticated, anon;
grant update (nombre) on public.perfiles to authenticated;
