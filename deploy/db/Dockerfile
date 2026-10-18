# MySQL for the cloud VM: same version as docker-compose, with the schema/seed
# baked in (the VM has no internet and no repo checkout) and a low-memory config
# for the 1 GB e2-micro. Build context is the repo root.
FROM mysql:8.0

COPY resources/db-migrations/init.sql /docker-entrypoint-initdb.d/init.sql
COPY deploy/db/low-memory.cnf /etc/mysql/conf.d/low-memory.cnf
