-- Rechtepruefung fuer suchgang - aendert nichts dauerhaft. NACH der
-- Migration 2026-09-23_suchgang.sql im Supabase-SQL-Editor ausfuehren.
--
-- Nimmt die beiden aeltesten Konten aus auth.users als A und B. Als A
-- entstehen ein Suchgang, eine Route und ein Fund; dann wird geprueft, was
-- B, B als Mitleser und Nichtangemeldete damit tun koennen, und ob die
-- Datenbank ungueltige Suchgaenge abweist. Die Rollen werden wie bei
-- echten Anfragen gesetzt (authenticated bzw. anon mit Kennung im Token),
-- es gelten also dieselben Zeilenrechte und Trigger wie in der App.
--
-- Am Ende wird alles zurueckgerollt - Testdaten und die voruebergehende
-- Mitleser-Markierung. Ausgegeben wird nur, ob jede Pruefung wie erwartet
-- ausging, keine Konto- oder Fundangaben.

create temp table rls_ergebnis (
  nr int, pruefung text, erwartet text, ergebnis text, ok boolean
) on commit drop;

-- Fuehrt einen Befehl als angemeldete Person (uid) oder, bei null, als
-- nicht angemeldet aus. Liefert "ok:<Zeilen>" oder "fehler:<Meldung>".
-- Bei einem Fehler rollt der Ausnahmeblock Befehl und Rollenwechsel
-- zurueck.
create function pg_temp.als(uid uuid, befehl text) returns text
language plpgsql as $$
declare
  n bigint;
begin
  if uid is null then
    execute 'set local role anon';
    perform set_config('request.jwt.claim.sub', '', true);
    perform set_config('request.jwt.claims', '{"role":"anon"}', true);
  else
    execute 'set local role authenticated';
    perform set_config('request.jwt.claim.sub', uid::text, true);
    perform set_config('request.jwt.claims',
      json_build_object('sub', uid, 'role', 'authenticated')::text, true);
  end if;
  if befehl ~* '^\s*select' then
    execute befehl into n;
  else
    execute befehl;
    get diagnostics n = row_count;
  end if;
  execute 'reset role';
  return 'ok:' || n;
exception when others then
  return 'fehler:' || sqlerrm;
end $$;

do $$
declare
  konten uuid[];
  a uuid;
  b uuid;
  sg uuid := gen_random_uuid();
  rt uuid := gen_random_uuid();
  erg jsonb := '[]';
  ort constant text := 'SRID=4326;POINT(10.7 52.4)';
begin
  select array_agg(id) into konten
  from (select id from auth.users order by created_at limit 2) k;
  if coalesce(cardinality(konten), 0) < 2 then
    insert into rls_ergebnis values
      (0, 'Mindestens zwei Konten in auth.users', 'ok', 'nur '
         || coalesce(cardinality(konten), 0) || ' vorhanden', false);
    return;
  end if;
  a := konten[1];
  b := konten[2];

  begin
    -- B zunaechst ohne Mitleserrecht
    update public.profile set mitleser = false where id = b;

    -- A: eigene Daten
    erg := erg || jsonb_build_object('p', 'A legt Suchgang an', 'e', 'ok:1',
      'r', pg_temp.als(a, format($q$insert into public.suchgang
        (id, benutzer, datum, beginn, arten, ergebnisse)
        values (%L, %L, current_date, now(), '{steinpilz}', '{"steinpilz":"offen"}')$q$, sg, a)));
    erg := erg || jsonb_build_object('p', 'A legt Route an', 'e', 'ok:1',
      'r', pg_temp.als(a, format($q$insert into public.route (id, benutzer, begonnen)
        values (%L, %L, now())$q$, rt, a)));
    erg := erg || jsonb_build_object('p', 'A verknuepft eigene Route', 'e', 'ok:1',
      'r', pg_temp.als(a, format($q$update public.suchgang set route = %L where id = %L$q$, rt, sg)));
    erg := erg || jsonb_build_object('p', 'A liest eigenen Suchgang', 'e', 'ok:1',
      'r', pg_temp.als(a, format($q$select count(*) from public.suchgang where id = %L$q$, sg)));
    erg := erg || jsonb_build_object('p', 'A haengt Fund an eigenen Suchgang', 'e', 'ok:1',
      'r', pg_temp.als(a, format($q$insert into public.fund
        (benutzer, art, gefunden_am, ort, nullfund, suchgang)
        values (%L, 'steinpilz', current_date, %L, true, %L)$q$, a, ort, sg)));

    -- B ohne Mitleserrecht
    erg := erg || jsonb_build_object('p', 'B liest Suchgang von A', 'e', 'ok:0',
      'r', pg_temp.als(b, format($q$select count(*) from public.suchgang where id = %L$q$, sg)));
    erg := erg || jsonb_build_object('p', 'B aendert Suchgang von A', 'e', 'ok:0',
      'r', pg_temp.als(b, format($q$update public.suchgang set notiz = 'x' where id = %L$q$, sg)));
    erg := erg || jsonb_build_object('p', 'B loescht Suchgang von A', 'e', 'ok:0',
      'r', pg_temp.als(b, format($q$delete from public.suchgang where id = %L$q$, sg)));
    erg := erg || jsonb_build_object('p', 'B legt Suchgang im Namen von A an', 'e', 'fehler',
      'r', pg_temp.als(b, format($q$insert into public.suchgang
        (id, benutzer, datum, beginn, arten) values (%L, %L, current_date, now(), '{steinpilz}')$q$,
        gen_random_uuid(), a)));
    erg := erg || jsonb_build_object('p', 'B verknuepft Route von A', 'e', 'fehler',
      'r', pg_temp.als(b, format($q$insert into public.suchgang
        (id, benutzer, datum, beginn, arten, route)
        values (%L, %L, current_date, now(), '{steinpilz}', %L)$q$, gen_random_uuid(), b, rt)));
    erg := erg || jsonb_build_object('p', 'B haengt Fund an Suchgang von A', 'e', 'fehler',
      'r', pg_temp.als(b, format($q$insert into public.fund
        (benutzer, art, gefunden_am, ort, nullfund, suchgang)
        values (%L, 'steinpilz', current_date, %L, true, %L)$q$, b, ort, sg)));

    -- B als Mitleser (nur fuer diesen Test, wird zurueckgerollt)
    update public.profile set mitleser = true where id = b;
    if not found then
      insert into public.profile (id, mitleser) values (b, true);
    end if;
    erg := erg || jsonb_build_object('p', 'Gegenprobe: Mitleser B sieht Route von A', 'e', 'ok:1',
      'r', pg_temp.als(b, format($q$select count(*) from public.route where id = %L$q$, rt)));
    erg := erg || jsonb_build_object('p', 'Mitleser B liest Suchgang von A', 'e', 'ok:0',
      'r', pg_temp.als(b, format($q$select count(*) from public.suchgang where id = %L$q$, sg)));
    erg := erg || jsonb_build_object('p', 'Mitleser B verknuepft Route von A', 'e', 'fehler',
      'r', pg_temp.als(b, format($q$insert into public.suchgang
        (id, benutzer, datum, beginn, arten, route)
        values (%L, %L, current_date, now(), '{steinpilz}', %L)$q$, gen_random_uuid(), b, rt)));
    erg := erg || jsonb_build_object('p', 'Mitleser B haengt Fund an Suchgang von A', 'e', 'fehler',
      'r', pg_temp.als(b, format($q$insert into public.fund
        (benutzer, art, gefunden_am, ort, nullfund, suchgang)
        values (%L, 'steinpilz', current_date, %L, true, %L)$q$, b, ort, sg)));

    -- Nicht angemeldet
    erg := erg || jsonb_build_object('p', 'Nicht angemeldet liest Suchgaenge', 'e', 'fehler',
      'r', pg_temp.als(null, 'select count(*) from public.suchgang'));

    -- Ungueltige Suchgaenge von A
    erg := erg || jsonb_build_object('p', 'Unbekannte Art', 'e', 'fehler',
      'r', pg_temp.als(a, format($q$insert into public.suchgang (id, benutzer, datum, beginn, arten)
        values (%L, %L, current_date, now(), '{fliegenpilz}')$q$, gen_random_uuid(), a)));
    erg := erg || jsonb_build_object('p', 'Art doppelt', 'e', 'fehler',
      'r', pg_temp.als(a, format($q$insert into public.suchgang (id, benutzer, datum, beginn, arten)
        values (%L, %L, current_date, now(), '{steinpilz,steinpilz}')$q$, gen_random_uuid(), a)));
    erg := erg || jsonb_build_object('p', 'Ergebnis fuer nicht gesuchte Art', 'e', 'fehler',
      'r', pg_temp.als(a, format($q$insert into public.suchgang (id, benutzer, datum, beginn, arten, ergebnisse)
        values (%L, %L, current_date, now(), '{steinpilz}', '{"marone":"fund"}')$q$, gen_random_uuid(), a)));
    erg := erg || jsonb_build_object('p', 'Unzulaessiger Ergebniswert', 'e', 'fehler',
      'r', pg_temp.als(a, format($q$insert into public.suchgang (id, benutzer, datum, beginn, arten, ergebnisse)
        values (%L, %L, current_date, now(), '{steinpilz}', '{"steinpilz":"vielleicht"}')$q$, gen_random_uuid(), a)));
    erg := erg || jsonb_build_object('p', 'Nachtrag mit Kartenwerten', 'e', 'fehler',
      'r', pg_temp.als(a, format($q$insert into public.suchgang (id, benutzer, datum, arten, quelle, angezeigt)
        values (%L, %L, current_date, '{steinpilz}', 'nachtrag', '{}')$q$, gen_random_uuid(), a)));
    erg := erg || jsonb_build_object('p', 'Auswertung ohne Einwilligungsversion', 'e', 'fehler',
      'r', pg_temp.als(a, format($q$insert into public.suchgang (id, benutzer, datum, beginn, arten, auswertung_erlaubt)
        values (%L, %L, current_date, now(), '{steinpilz}', true)$q$, gen_random_uuid(), a)));
    erg := erg || jsonb_build_object('p', 'Suchdauer laenger als der Gang', 'e', 'fehler',
      'r', pg_temp.als(a, format($q$insert into public.suchgang (id, benutzer, datum, beginn, ende, arten, suchdauer_min)
        values (%L, %L, current_date, now() - interval '1 hour', now(), '{steinpilz}', 120)$q$, gen_random_uuid(), a)));
    erg := erg || jsonb_build_object('p', 'Gueltiger Nachtrag', 'e', 'ok:1',
      'r', pg_temp.als(a, format($q$insert into public.suchgang (id, benutzer, datum, arten, quelle, ergebnisse)
        values (%L, %L, current_date - 1, '{steinpilz,marone}', 'nachtrag', '{"marone":"nullfund"}')$q$, gen_random_uuid(), a)));
    erg := erg || jsonb_build_object('p', 'A schiebt Suchgang zu B', 'e', 'fehler',
      'r', pg_temp.als(a, format($q$update public.suchgang set benutzer = %L where id = %L$q$, b, sg)));
    -- Ohne Route greift der Routen-Trigger nicht; dann muss die
    -- Zeilenrichtlinie selbst den Eigentuemerwechsel verhindern
    erg := erg || jsonb_build_object('p', 'A schiebt Suchgang ohne Route zu B', 'e', 'fehler',
      'r', pg_temp.als(a, format($q$update public.suchgang set route = null, benutzer = %L where id = %L$q$, b, sg)));

    -- Alles in diesem Block zuruecknehmen
    raise exception 'rls_test_zurueck';
  exception when others then
    if sqlerrm <> 'rls_test_zurueck' then
      erg := erg || jsonb_build_object('p', 'Testablauf', 'e', 'ok', 'r', 'abgebrochen: ' || sqlerrm);
    end if;
  end;

  insert into rls_ergebnis
  select t.nr, t.v->>'p', t.v->>'e', t.v->>'r',
         case when t.v->>'e' = 'fehler' then t.v->>'r' like 'fehler:%'
              else t.v->>'r' = t.v->>'e' end
  from jsonb_array_elements(erg) with ordinality as t(v, nr);
end $$;

select nr, pruefung, erwartet, ergebnis, ok from rls_ergebnis order by nr;
