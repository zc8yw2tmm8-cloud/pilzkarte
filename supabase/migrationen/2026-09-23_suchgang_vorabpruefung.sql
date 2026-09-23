-- NUR LESEN - aendert nichts. Vor der Suchgang-Migration im Supabase-
-- SQL-Editor ausfuehren und die Ergebnistabelle vollstaendig weitergeben.
-- Zeigt, wie fund, route, profile und erlaubt heute wirklich aussehen:
-- Spalten und Typen, Zeilenrichtlinien, Trigger, Sichten und eigene
-- Funktionen. Eine Zeile je Bereich und Tabelle, damit das Ergebnis unter
-- der Zeilengrenze des Editors (100) bleibt. Funktionen aus Erweiterungen
-- wie PostGIS sind ausgeblendet.

with tabellen (name) as (
  values ('fund'), ('route'), ('profile'), ('erlaubt'), ('suchgang')
),
eintraege (reihe, bereich, tabelle, inhalt) as (
  select 1, 'spalten', c.table_name,
         string_agg(format('%s %s%s%s', c.column_name, c.data_type,
                           case when c.is_nullable = 'NO' then ' not null' else '' end,
                           coalesce(' default ' || c.column_default, '')),
                    ' ; ' order by c.ordinal_position)
  from information_schema.columns c
  where c.table_schema = 'public' and c.table_name in (select name from tabellen)
  group by c.table_name
  union all
  select 2, 'rls', c.relname,
         format('rls=%s erzwungen=%s', c.relrowsecurity, c.relforcerowsecurity)
  from pg_class c join pg_namespace s on s.oid = c.relnamespace
  where s.nspname = 'public' and c.relname in (select name from tabellen)
  union all
  select 3, 'policies', p.tablename,
         string_agg(format('%s [%s, %s] using(%s) check(%s)', p.policyname, p.cmd,
                           p.roles::text, coalesce(p.qual, '-'),
                           coalesce(p.with_check, '-')), ' ; ' order by p.policyname)
  from pg_policies p
  where p.schemaname = 'public' and p.tablename in (select name from tabellen)
  group by p.tablename
  union all
  select 4, 'trigger', t.event_object_table,
         string_agg(format('%s %s %s: %s', t.trigger_name, t.action_timing,
                           t.event_manipulation, t.action_statement),
                    ' ; ' order by t.trigger_name)
  from information_schema.triggers t
  where t.event_object_schema = 'public'
  group by t.event_object_table
  union all
  select 5, 'sichten', '-',
         string_agg(v.table_name, ' ; ' order by v.table_name)
  from information_schema.views v
  where v.table_schema = 'public'
  union all
  select 6, 'funktionen', '-',
         string_agg(format('%s(%s) definer=%s', p.proname,
                           pg_get_function_identity_arguments(p.oid), p.prosecdef),
                    ' ; ' order by p.proname)
  from pg_proc p join pg_namespace s on s.oid = p.pronamespace
  where s.nspname = 'public'
    and not exists (select 1 from pg_depend d
                    where d.objid = p.oid and d.deptype = 'e')
  union all
  select 7, 'erweiterungen', '-',
         string_agg(format('%s %s (%s)', e.extname, e.extversion, n.nspname),
                    ' ; ' order by e.extname)
  from pg_extension e join pg_namespace n on n.oid = e.extnamespace
)
select bereich, tabelle, inhalt
from eintraege
order by reihe, tabelle;
