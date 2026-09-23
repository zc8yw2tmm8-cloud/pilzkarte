-- Suchgaenge: jeder Gang in den Wald mit gesuchten Arten, Ergebnis je Art,
-- Suchaufwand und - bei Aufzeichnung - dem, was die Karte damals zeigte.
-- Grundlage, um spaeter zu pruefen, ob hohe Werte haeufiger zu Funden
-- fuehren.
--
-- Reihenfolge: zuerst 2026-09-23_suchgang_vorabpruefung.sql ausfuehren und
-- das Ergebnis pruefen lassen, dann dieses Skript im Supabase-SQL-Editor.
-- Alles laeuft in einer Transaktion: Weicht das vorhandene Schema ab,
-- bricht der Abgleich am Ende ab und nichts bleibt zurueck.
-- Mehrfaches Ausfuehren ist unschaedlich.

create table if not exists public.suchgang (
  id                   uuid primary key,
  benutzer             uuid not null default auth.uid()
                       references auth.users (id) on delete cascade,
  -- Tag der Suche (Europe/Berlin); Uhrzeiten nur bei Aufzeichnung
  datum                date not null,
  beginn               timestamptz,
  ende                 timestamptz,
  -- Tatsaechliche Suchzeit, nicht die Routendauer; null = unbekannt
  suchdauer_min        integer,
  arten                text[] not null,
  -- Je gesuchter Art: fund | nullfund | offen
  ergebnisse           jsonb not null default '{}'::jsonb,
  route                uuid,
  lat                  double precision,
  lon                  double precision,
  genauigkeit_m        real,
  -- Alte Rasterkennung am Startpunkt und alle beruehrten Zellen
  zelle                text,
  besuchte_zellen      text[] not null default '{}',
  raeumlich_gemischt   boolean not null default false,
  -- Momentaufnahme der damals angezeigten Werte; bei Nachtraegen leer
  angezeigt            jsonb,
  datenstand           date,
  -- Hash der mitgelieferten Bewertungsparameter - kein Modellfingerabdruck
  config_hash          text,
  modellversion        text,
  versionsstatus       text not null default 'legacy',
  auswertung_erlaubt   boolean not null default false,
  einwilligung_version text,
  einwilligung_zeit    timestamptz,
  quelle               text not null default 'aufzeichnung',
  notiz                text,
  angelegt             timestamptz not null default now(),

  constraint suchgang_quelle check (quelle in ('aufzeichnung', 'nachtrag')),
  constraint suchgang_versionsstatus check (versionsstatus in ('legacy', 'versioniert')),
  constraint suchgang_datum check (datum > date '2020-01-01'),
  -- Nachtraege haben weder Uhrzeit noch angezeigte Werte
  constraint suchgang_zeitangaben check (
    (quelle = 'aufzeichnung' and beginn is not null)
    or (quelle = 'nachtrag' and beginn is null and ende is null
        and angezeigt is null)),
  constraint suchgang_ende check (
    ende is null or (ende >= beginn and ende <= beginn + interval '24 hours')),
  constraint suchgang_suchdauer check (
    suchdauer_min is null or (suchdauer_min between 1 and 1440
      and (ende is null
           or suchdauer_min <= extract(epoch from ende - beginn) / 60 + 1))),
  constraint suchgang_arten check (cardinality(arten) between 1 and 11),
  constraint suchgang_ergebnisse check (
    jsonb_typeof(ergebnisse) = 'object' and pg_column_size(ergebnisse) <= 1000),
  constraint suchgang_ort check (
    (lat is null) = (lon is null)
    and (lat is null or (lat between -90 and 90 and lon between -180 and 180))),
  constraint suchgang_genauigkeit check (
    genauigkeit_m is null or genauigkeit_m between 0 and 100000),
  constraint suchgang_zellen check (cardinality(besuchte_zellen) <= 100),
  constraint suchgang_angezeigt check (
    angezeigt is null
    or (jsonb_typeof(angezeigt) = 'object' and pg_column_size(angezeigt) <= 16000)),
  constraint suchgang_einwilligung check (
    not auswertung_erlaubt
    or (einwilligung_version is not null and einwilligung_zeit is not null)),
  constraint suchgang_texte check (
    coalesce(length(notiz), 0) <= 2000
    and coalesce(length(zelle), 0) <= 40
    and coalesce(length(config_hash), 0) <= 64
    and coalesce(length(modellversion), 0) <= 64
    and coalesce(length(einwilligung_version), 0) <= 40)
);

create index if not exists suchgang_benutzer_datum
  on public.suchgang (benutzer, datum desc);

do $$
begin
  if (select data_type from information_schema.columns
      where table_schema = 'public' and table_name = 'route'
        and column_name = 'id') = 'uuid'
     and not exists (select 1 from pg_constraint
                     where conname = 'suchgang_route_fk') then
    alter table public.suchgang
      add constraint suchgang_route_fk foreign key (route)
      references public.route (id) on delete set null;
  end if;
end $$;

-- Inhalt pruefen, der sich nicht als einfache Bedingung schreiben laesst:
-- nur bekannte Arten, keine doppelt; Ergebnisse nur fuer gesuchte Arten und
-- nur mit erlaubten Werten; die Route gehoert derselben Person. Ein
-- Fremdschluessel prueft nur, dass es die Route gibt, nicht wem sie gehoert.
-- SECURITY INVOKER: Die Abfrage laeuft mit den Rechten der angemeldeten
-- Person; zusaetzlich wird der Eigentuemer ausdruecklich verglichen, weil
-- Mitleser fremde Routen lesen duerfen.
create or replace function public.suchgang_pruefen()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
declare
  bekannt constant text[] := array['steinpilz', 'sommersteinpilz', 'marone',
    'pfifferling', 'birkenpilz', 'schwefelporling', 'parasol',
    'hexenroehrling', 'netzhexe', 'reizker', 'krauseglucke'];
begin
  if not (new.arten <@ bekannt) then
    raise exception 'Unbekannte Pilzart im Suchgang';
  end if;
  if cardinality(new.arten) <> (select count(distinct a) from unnest(new.arten) a) then
    raise exception 'Pilzart doppelt im Suchgang';
  end if;
  if exists (select 1 from jsonb_each_text(new.ergebnisse) e
             where not (e.key = any (new.arten))
                or e.value not in ('fund', 'nullfund', 'offen')) then
    raise exception 'Ungueltiges Ergebnis im Suchgang';
  end if;
  if new.route is not null and not exists (
      select 1 from public.route r
      where r.id = new.route and r.benutzer = new.benutzer) then
    raise exception 'Route gehoert nicht zu diesem Suchgang';
  end if;
  return new;
end $$;

drop trigger if exists suchgang_pruefen on public.suchgang;
create trigger suchgang_pruefen
  before insert or update on public.suchgang
  for each row execute function public.suchgang_pruefen();

-- Nur die eigene Person: keine Freigabe fuer Mitleser
alter table public.suchgang enable row level security;

drop policy if exists suchgang_lesen on public.suchgang;
drop policy if exists suchgang_anlegen on public.suchgang;
drop policy if exists suchgang_aendern on public.suchgang;
drop policy if exists suchgang_loeschen on public.suchgang;

create policy suchgang_lesen on public.suchgang
  for select to authenticated using (benutzer = auth.uid());
create policy suchgang_anlegen on public.suchgang
  for insert to authenticated with check (benutzer = auth.uid());
create policy suchgang_aendern on public.suchgang
  for update to authenticated
  using (benutzer = auth.uid()) with check (benutzer = auth.uid());
create policy suchgang_loeschen on public.suchgang
  for delete to authenticated using (benutzer = auth.uid());

revoke all on public.suchgang from public, anon;
grant select, insert, update, delete on public.suchgang to authenticated;

-- Funde koennen einem Suchgang zugeordnet werden
alter table public.fund
  add column if not exists suchgang uuid
  references public.suchgang (id) on delete set null;

-- Ein Fund darf nur auf einen eigenen Suchgang zeigen
create or replace function public.fund_suchgang_pruefen()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  if new.suchgang is not null and not exists (
      select 1 from public.suchgang s
      where s.id = new.suchgang and s.benutzer = new.benutzer) then
    raise exception 'Suchgang gehoert nicht zu diesem Fund';
  end if;
  return new;
end $$;

drop trigger if exists fund_suchgang_pruefen on public.fund;
create trigger fund_suchgang_pruefen
  before insert or update of suchgang, benutzer on public.fund
  for each row execute function public.fund_suchgang_pruefen();

-- Abgleich: Gab es suchgang schon mit anderem Aufbau, hat CREATE TABLE IF
-- NOT EXISTS nichts veraendert. Dann hier abbrechen und alles zurueckrollen,
-- statt mit falschem Schema weiterzuarbeiten.
do $$
declare
  abweichung text;
begin
  select string_agg(format('%s.%s (%s)', e.tabelle, e.spalte, e.typ), ', ')
    into abweichung
  from (values
    ('suchgang', 'id', 'uuid'), ('suchgang', 'benutzer', 'uuid'),
    ('suchgang', 'datum', 'date'),
    ('suchgang', 'beginn', 'timestamp with time zone'),
    ('suchgang', 'ende', 'timestamp with time zone'),
    ('suchgang', 'suchdauer_min', 'integer'), ('suchgang', 'arten', 'ARRAY'),
    ('suchgang', 'ergebnisse', 'jsonb'), ('suchgang', 'route', 'uuid'),
    ('suchgang', 'lat', 'double precision'), ('suchgang', 'lon', 'double precision'),
    ('suchgang', 'genauigkeit_m', 'real'), ('suchgang', 'zelle', 'text'),
    ('suchgang', 'besuchte_zellen', 'ARRAY'),
    ('suchgang', 'raeumlich_gemischt', 'boolean'),
    ('suchgang', 'angezeigt', 'jsonb'), ('suchgang', 'datenstand', 'date'),
    ('suchgang', 'config_hash', 'text'), ('suchgang', 'modellversion', 'text'),
    ('suchgang', 'versionsstatus', 'text'),
    ('suchgang', 'auswertung_erlaubt', 'boolean'),
    ('suchgang', 'einwilligung_version', 'text'),
    ('suchgang', 'einwilligung_zeit', 'timestamp with time zone'),
    ('suchgang', 'quelle', 'text'), ('suchgang', 'notiz', 'text'),
    ('suchgang', 'angelegt', 'timestamp with time zone'),
    ('fund', 'id', 'uuid'), ('fund', 'benutzer', 'uuid'),
    ('fund', 'suchgang', 'uuid'),
    ('route', 'id', 'uuid'), ('route', 'benutzer', 'uuid')
  ) as e (tabelle, spalte, typ)
  where not exists (
    select 1 from information_schema.columns c
    where c.table_schema = 'public' and c.table_name = e.tabelle
      and c.column_name = e.spalte and c.data_type = e.typ);
  if abweichung is not null then
    raise exception 'Schema weicht ab, nichts uebernommen. Fehlend oder anders: %', abweichung;
  end if;
end $$;
