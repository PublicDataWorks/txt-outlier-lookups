cd "$(dirname "$0")/.."
set -a; source .env; set +a

current_date=$(date +%d%m%Y)

psql "$DATABASE_URL" -c "DROP TABLE IF EXISTS public.mi_wayne_detroit;"

psql "$DATABASE_URL" -a  -f /tmp/mi_wayne_detroit.sql > /dev/null

psql "$DATABASE_URL" -c "
DROP TABLE IF EXISTS address_lookup.mi_wayne_detroit;
ALTER TABLE public.mi_wayne_detroit SET SCHEMA address_lookup;
"

rm /tmp/mi_wayne_detroit.sql
rm /tmp/mi_wayne_detroit.sql.zip
