-- Role PostgreSQL en lecture seule pour Grafana.
-- Execute par le Job grafana-role (terraform/grafana.tf) avec :
--   psql -v pw=<mot de passe> -v db=<base> -f grafana_ro.sql
-- Rejouable sans risque (idempotent).

-- CREATE ROLE IF NOT EXISTS n'existe pas : le SELECT fabrique la commande, \gexec l'execute
SELECT 'CREATE ROLE grafana_ro' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_ro') \gexec

ALTER ROLE grafana_ro WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'pw';
ALTER ROLE grafana_ro SET default_transaction_read_only = on;
ALTER ROLE grafana_ro SET statement_timeout = '15s';

GRANT CONNECT ON DATABASE :"db" TO grafana_ro;
GRANT USAGE ON SCHEMA public TO grafana_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_ro;
-- tables creees plus tard par le proprietaire de la base
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafana_ro;
